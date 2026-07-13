from __future__ import annotations

import json
import sqlite3
from typing import Any

import pandas as pd
import requests

from storage.db import connect
from utils.formatting import now_et, to_float
from utils.secrets import secret_or_env


def _init_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_release_state (
                indicator TEXT PRIMARY KEY,
                observation_period TEXT NOT NULL,
                value REAL,
                source TEXT,
                source_url TEXT,
                seen_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_release_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                official_release_at TEXT,
                observation_period TEXT NOT NULL,
                value REAL,
                previous_value REAL,
                change_value REAL,
                alert_message TEXT NOT NULL,
                source_url TEXT,
                delivery_status TEXT NOT NULL,
                delivery_error TEXT,
                dismissed INTEGER DEFAULT 0,
                UNIQUE(indicator, observation_period, value)
            )
            """
        )
        conn.commit()


def _release_changed(prior: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    if not prior:
        return False
    old_period = str(prior.get("observation_period") or "")
    new_period = str(current.get("observation_period") or "")
    old_value = to_float(prior.get("value"))
    new_value = to_float(current.get("value"))
    return old_period != new_period or old_value != new_value


def _recent_official_release(row: dict[str, Any], current: object | None = None) -> bool:
    released = pd.to_datetime(row.get("official_release_at"), errors="coerce", utc=True)
    now = pd.to_datetime(current or now_et(), errors="coerce", utc=True)
    if pd.isna(released) or pd.isna(now):
        return False
    age_seconds = (pd.Timestamp(now) - pd.Timestamp(released)).total_seconds()
    return 0 <= age_seconds <= 1_200


def _alert_message(row: dict[str, Any]) -> str:
    indicator = str(row.get("indicator") or "Macro release")
    period = str(row.get("observation_period") or "new period")
    value = str(row.get("display_value") or row.get("value") or "N/A")
    change = str(row.get("display_change") or "N/A")
    return f"{indicator} updated: {value} for {period} ({change} vs prior)."


def _deliver_webhook(message: str, row: dict[str, Any]) -> tuple[str, str]:
    webhook_url = secret_or_env("MACRO_ALERT_WEBHOOK_URL")
    if not webhook_url:
        return "In-app only", ""
    payload = {
        "text": message,
        "content": message,
        "event": {
            "type": "macro_release",
            "indicator": row.get("indicator"),
            "observation_period": row.get("observation_period"),
            "value": row.get("value"),
            "previous_value": row.get("previous_value"),
            "change": row.get("change"),
            "official_release_at": str(row.get("official_release_at") or ""),
            "source_url": row.get("source_url"),
        },
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=8)
        response.raise_for_status()
        return "Webhook delivered", ""
    except requests.RequestException as exc:
        return "Webhook failed", str(exc)[:240]


def process_macro_updates(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Persist official macro state and emit one alert for each new period or revision."""

    if frame is None or frame.empty:
        return []
    _init_tables()
    pending: list[dict[str, Any]] = []
    with connect() as conn:
        for _, series in frame.iterrows():
            row = series.to_dict()
            if str(row.get("audit_status") or "") != "VERIFIED" or to_float(row.get("value")) is None:
                continue
            indicator = str(row.get("indicator") or "").strip()
            period = str(row.get("observation_period") or "").strip()
            if not indicator or not period:
                continue
            prior_record = conn.execute(
                "SELECT indicator, observation_period, value, source, source_url, seen_at FROM macro_release_state WHERE indicator = ?",
                (indicator,),
            ).fetchone()
            prior = dict(prior_record) if prior_record else None
            changed = _release_changed(prior, row) or (prior is None and _recent_official_release(row))
            conn.execute(
                """
                INSERT INTO macro_release_state (indicator, observation_period, value, source, source_url, seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator) DO UPDATE SET
                    observation_period = excluded.observation_period,
                    value = excluded.value,
                    source = excluded.source,
                    source_url = excluded.source_url,
                    seen_at = excluded.seen_at
                """,
                (
                    indicator,
                    period,
                    to_float(row.get("value")),
                    str(row.get("source") or ""),
                    str(row.get("source_url") or ""),
                    now_et().isoformat(),
                ),
            )
            if not changed:
                continue
            message = _alert_message(row)
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO macro_release_alerts (
                        indicator, detected_at, official_release_at, observation_period, value,
                        previous_value, change_value, alert_message, source_url, delivery_status, delivery_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        indicator,
                        now_et().isoformat(),
                        str(row.get("official_release_at") or ""),
                        period,
                        to_float(row.get("value")),
                        to_float(row.get("previous_value")),
                        to_float(row.get("change")),
                        message,
                        str(row.get("source_url") or ""),
                        "Pending",
                        "",
                    ),
                )
            except sqlite3.IntegrityError:
                continue
            pending.append(
                {
                    "id": cursor.lastrowid,
                    "indicator": indicator,
                    "message": message,
                    "source_url": row.get("source_url"),
                    "row": row,
                }
            )
        conn.commit()
    emitted: list[dict[str, Any]] = []
    for alert in pending:
        delivery_status, delivery_error = _deliver_webhook(alert["message"], alert["row"])
        with connect() as conn:
            conn.execute(
                "UPDATE macro_release_alerts SET delivery_status = ?, delivery_error = ? WHERE id = ?",
                (delivery_status, delivery_error, alert["id"]),
            )
            conn.commit()
        emitted.append(
            {
                "id": alert["id"],
                "indicator": alert["indicator"],
                "message": alert["message"],
                "delivery_status": delivery_status,
                "source_url": alert["source_url"],
            }
        )
    return emitted


def list_macro_alerts(include_dismissed: bool = False, limit: int = 50) -> pd.DataFrame:
    _init_tables()
    query = "SELECT * FROM macro_release_alerts"
    if not include_dismissed:
        query += " WHERE dismissed = 0"
    query += " ORDER BY detected_at DESC, id DESC LIMIT ?"
    with connect() as conn:
        rows = conn.execute(query, (max(1, min(int(limit), 200)),)).fetchall()
    return pd.DataFrame([dict(row) for row in rows])


def dismiss_macro_alert(alert_id: int) -> None:
    _init_tables()
    with connect() as conn:
        conn.execute("UPDATE macro_release_alerts SET dismissed = 1 WHERE id = ?", (int(alert_id),))
        conn.commit()


def macro_notification_status() -> dict[str, object]:
    return {
        "in_app": True,
        "webhook_configured": bool(secret_or_env("MACRO_ALERT_WEBHOOK_URL")),
        "webhook_name": "MACRO_ALERT_WEBHOOK_URL",
        "payload_contract": json.dumps({"text": "...", "content": "...", "event": {"type": "macro_release"}}),
    }
