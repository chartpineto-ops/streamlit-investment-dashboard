from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from components.data_freshness_bar import render_data_freshness_bar
from utils.formatting import now_et
from utils.refresh_debug import is_refresh_stale


REFRESH_STATUS_KEY = "_pt_fragment_refresh_status"


def mark_fragment_refresh(
    name: str,
    cadence_seconds: int,
    status: str = "OK",
    message: str = "",
    *,
    last_refresh: object = None,
    data_source: str = "",
    cache_ttl: int | str = "",
    rows: int | None = None,
    is_stale: bool | None = None,
    error: str = "",
) -> None:
    actual_refresh = now_et() if last_refresh is None else last_refresh
    registry = dict(st.session_state.get(REFRESH_STATUS_KEY, {}))
    registry[name] = {
        "last_refresh": actual_refresh,
        "cadence_seconds": cadence_seconds,
        "status": status,
        "message": message,
        "data_source": data_source or message,
        "cache_ttl": cache_ttl,
        "rows": rows,
        "is_stale": is_refresh_stale(actual_refresh, cadence_seconds) if is_stale is None else bool(is_stale),
        "error": error,
    }
    st.session_state[REFRESH_STATUS_KEY] = registry


def _time_label(value: object) -> str:
    try:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            raise ValueError("missing timestamp")
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("America/New_York")
        else:
            timestamp = timestamp.tz_convert("America/New_York")
        return timestamp.strftime("%H:%M:%S")
    except Exception:
        return "Waiting"


def _status_tone(entry: dict[str, object]) -> str:
    status = str(entry.get("status") or "").casefold()
    if status in {"fallback", "partial", "demo data", "provider not configured"}:
        return "warn"
    if status and status != "ok":
        return "bad"
    if bool(entry.get("is_stale")):
        return "warn"
    timestamp = entry.get("last_refresh")
    cadence = int(entry.get("cadence_seconds") or 0)
    if not timestamp or not cadence:
        return "warn"
    try:
        age = now_et() - pd.Timestamp(timestamp).to_pydatetime()
    except Exception:
        return "warn"
    return "warn" if age > timedelta(seconds=cadence * 2) else "good"


@st.fragment(run_every="5s")
def render_freshness_status_row() -> None:
    registry = dict(st.session_state.get(REFRESH_STATUS_KEY, {}))
    labels = [
        ("Live prices", "live_prices"),
        ("Movers", "market_movers"),
        ("News", "news"),
        ("Macro", "macro"),
        ("Social", "social"),
    ]
    items: list[dict[str, object]] = []
    for label, key in labels:
        entry = registry.get(key, {})
        tone = _status_tone(entry)
        message = str(entry.get("message") or entry.get("data_source") or entry.get("status") or "Pending")
        items.append(
            {
                "label": label,
                "status": tone,
                "refreshed": _time_label(entry.get("last_refresh")),
                "source": message,
                "title": message,
            }
        )
    render_data_freshness_bar(items)
