from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from io import StringIO
from typing import Any

import pandas as pd
import requests
import streamlit as st
from curl_cffi import requests as browser_requests

from storage.db import connect
from utils.formatting import EASTERN, now_et, to_float
from utils.secrets import secret_or_env


BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_CALENDAR_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BEA_SCHEDULE_URL = "https://www.bea.gov/news/schedule/full"
FRED_API_URL = "https://api.stlouisfed.org/fred"

MACRO_COLUMNS = [
    "indicator",
    "series_id",
    "value",
    "previous_value",
    "change",
    "change_pct",
    "display_value",
    "display_change",
    "observation_date",
    "observation_period",
    "official_release_at",
    "next_release_at",
    "provider_updated_at",
    "frequency",
    "units",
    "source",
    "source_url",
    "data_source",
    "last_refresh",
    "audit_status",
    "audit_message",
]

BLS_SERIES: dict[str, dict[str, str]] = {
    "CUSR0000SA0": {
        "indicator": "Consumer Price Index",
        "frequency": "Monthly",
        "units": "Index 1982-84=100",
        "release_name": "Consumer Price Index",
        "source": "U.S. Bureau of Labor Statistics",
        "source_url": "https://www.bls.gov/cpi/",
        "display_kind": "index",
    },
    "LNS14000000": {
        "indicator": "Unemployment Rate",
        "frequency": "Monthly",
        "units": "%",
        "release_name": "Employment Situation",
        "source": "U.S. Bureau of Labor Statistics",
        "source_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
        "display_kind": "percent",
    },
    "CES0000000001": {
        "indicator": "Total Nonfarm Payrolls",
        "frequency": "Monthly",
        "units": "Thousands",
        "release_name": "Employment Situation",
        "source": "U.S. Bureau of Labor Statistics",
        "source_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
        "display_kind": "thousands",
    },
}

FRED_SERIES: dict[str, dict[str, str]] = {
    "PCEPI": {
        "indicator": "PCE Price Index",
        "frequency": "Monthly",
        "units": "Index 2017=100",
        "release_name": "Personal Income and Outlays",
        "source": "U.S. Bureau of Economic Analysis via FRED",
        "source_url": "https://www.bea.gov/data/personal-consumption-expenditures-price-index",
        "display_kind": "index",
    },
    "ICSA": {
        "indicator": "Initial Jobless Claims",
        "frequency": "Weekly",
        "units": "Claims",
        "release_name": "Unemployment Insurance Weekly Claims",
        "source": "U.S. Department of Labor via FRED",
        "source_url": "https://www.dol.gov/ui/data.pdf",
        "display_kind": "count",
    },
    "DFF": {
        "indicator": "Effective Fed Funds Rate",
        "frequency": "Daily",
        "units": "%",
        "release_name": "",
        "source": "Federal Reserve Bank of New York via FRED",
        "source_url": "https://www.newyorkfed.org/markets/reference-rates/effr",
        "display_kind": "percent",
    },
    "DGS10": {
        "indicator": "10Y Treasury Yield",
        "frequency": "Daily",
        "units": "%",
        "release_name": "",
        "source": "Federal Reserve Board H.15 via FRED",
        "source_url": "https://www.federalreserve.gov/releases/h15/",
        "display_kind": "percent",
    },
    "DGS2": {
        "indicator": "2Y Treasury Yield",
        "frequency": "Daily",
        "units": "%",
        "release_name": "",
        "source": "Federal Reserve Board H.15 via FRED",
        "source_url": "https://www.federalreserve.gov/releases/h15/",
        "display_kind": "percent",
    },
    "GDPC1": {
        "indicator": "Real GDP",
        "frequency": "Quarterly",
        "units": "$B SAAR",
        "release_name": "Gross Domestic Product",
        "source": "U.S. Bureau of Economic Analysis via FRED",
        "source_url": "https://www.bea.gov/data/gdp/gross-domestic-product",
        "display_kind": "billions",
    },
    "RSAFS": {
        "indicator": "Retail Sales",
        "frequency": "Monthly",
        "units": "$M SA",
        "release_name": "Advance Monthly Sales for Retail and Food Services",
        "source": "U.S. Census Bureau via FRED",
        "source_url": "https://www.census.gov/retail/index.html",
        "display_kind": "millions",
    },
}

TRACKED_RELEASE_TERMS = (
    "Consumer Price Index",
    "Employment Situation",
    "Producer Price Index",
    "Personal Income and Outlays",
    "Gross Domestic Product",
    "Advance Monthly Sales for Retail and Food Services",
    "Unemployment Insurance Weekly Claims",
)

RELEASE_PRIORITY = {
    "Consumer Price Index": 0,
    "Employment Situation": 1,
    "Producer Price Index": 2,
    "Personal Income and Outlays": 3,
    "Gross Domestic Product": 4,
    "Advance Monthly Sales for Retail and Food Services": 5,
    "Unemployment Insurance Weekly Claims": 6,
}


def _empty_macro() -> pd.DataFrame:
    return pd.DataFrame(columns=MACRO_COLUMNS)


def _init_snapshot_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_verified_snapshots (
                series_id TEXT PRIMARY KEY,
                snapshot_json TEXT NOT NULL,
                saved_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _save_verified_snapshots(frame: pd.DataFrame) -> None:
    verified = frame[frame["audit_status"] == "VERIFIED"] if not frame.empty else pd.DataFrame()
    if verified.empty:
        return
    try:
        _init_snapshot_table()
        with connect() as conn:
            for _, row in verified.iterrows():
                payload = json.dumps(row.to_dict(), default=str)
                conn.execute(
                    """
                    INSERT INTO macro_verified_snapshots (series_id, snapshot_json, saved_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(series_id) DO UPDATE SET
                        snapshot_json = excluded.snapshot_json,
                        saved_at = excluded.saved_at
                    """,
                    (str(row.get("series_id") or ""), payload, now_et().isoformat()),
                )
            conn.commit()
    except sqlite3.Error:
        return


def _load_verified_snapshots() -> pd.DataFrame:
    try:
        _init_snapshot_table()
        with connect() as conn:
            records = conn.execute(
                "SELECT snapshot_json, saved_at FROM macro_verified_snapshots ORDER BY series_id"
            ).fetchall()
    except sqlite3.Error:
        return _empty_macro()
    rows: list[dict[str, object]] = []
    for record in records:
        try:
            row = json.loads(record["snapshot_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        row["audit_status"] = "REVIEW"
        row["audit_message"] = (
            "Live provider refresh failed; showing the last verified official observation "
            f"saved {record['saved_at']}."
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=MACRO_COLUMNS) if rows else _empty_macro()


def _request_headers() -> dict[str, str]:
    headers = {"Accept": "application/json,text/calendar,text/html;q=0.9,*/*;q=0.8"}
    agent = secret_or_env("DATA_USER_AGENT")
    if agent:
        headers["User-Agent"] = agent
    return headers


def _as_eastern(value: object) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    return stamp.tz_localize(EASTERN) if stamp.tzinfo is None else stamp.tz_convert(EASTERN)


def _format_value(value: float | None, kind: str) -> str:
    if value is None:
        return "N/A"
    if kind == "percent":
        return f"{value:.2f}%"
    if kind == "count":
        return f"{value / 1_000:,.0f}K" if abs(value) >= 1_000 else f"{value:,.0f}"
    if kind == "thousands":
        return f"{value:,.0f}K"
    if kind == "millions":
        return f"${value / 1_000:,.1f}B"
    if kind == "billions":
        return f"${value:,.1f}B"
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def _format_change(change: float | None, change_pct: float | None, kind: str) -> str:
    if change is None:
        return "N/A"
    sign = "+" if change > 0 else ""
    if kind == "percent":
        return f"{sign}{change:.2f} pp"
    if kind == "count":
        return f"{sign}{change / 1_000:,.0f}K" if abs(change) >= 1_000 else f"{sign}{change:,.0f}"
    if kind == "thousands":
        return f"{sign}{change:,.0f}K"
    if change_pct is not None:
        return f"{sign}{change_pct:.2f}%"
    return f"{sign}{change:,.2f}"


def _unfold_ics(text: str) -> list[str]:
    lines: list[str] = []
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.strip("\r"))
    return lines


def _parse_bls_calendar(text: str) -> pd.DataFrame:
    events: list[dict[str, object]] = []
    current: dict[str, str] | None = None
    for line in _unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current:
                raw_date = current.get("DTSTART", "")
                fmt = "%Y%m%dT%H%M%S" if "T" in raw_date else "%Y%m%d"
                try:
                    released = pd.Timestamp(datetime.strptime(raw_date.rstrip("Z"), fmt), tz=EASTERN)
                    events.append(
                        {
                            "release_name": current.get("SUMMARY", "").replace("\\,", ","),
                            "release_at": released,
                            "source": "U.S. Bureau of Labor Statistics",
                            "source_url": "https://www.bls.gov/schedule/",
                        }
                    )
                except ValueError:
                    pass
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.split(";", 1)[0]
        if key in {"DTSTART", "SUMMARY"}:
            current[key] = value.strip()
    return pd.DataFrame(events, columns=["release_name", "release_at", "source", "source_url"])


def _parse_bea_schedule(html: str) -> pd.DataFrame:
    events: list[dict[str, object]] = []
    try:
        tables = pd.read_html(StringIO(html))
    except (ValueError, ImportError):
        return pd.DataFrame(columns=["release_name", "release_at", "source", "source_url"])
    for table in tables:
        if table.empty or "Release" not in table.columns:
            continue
        first_column = table.columns[0]
        year_match = re.search(r"(20\d{2})", str(first_column))
        if not year_match:
            continue
        year = int(year_match.group(1))
        for _, row in table.iterrows():
            timing = str(row.get(first_column) or "")
            match = re.match(r"([A-Za-z]+\s+\d{1,2})\s+(\d{1,2}:\d{2}\s+[AP]M)", timing)
            if not match:
                continue
            released = pd.to_datetime(f"{match.group(1)} {year} {match.group(2)}", errors="coerce")
            if pd.isna(released):
                continue
            events.append(
                {
                    "release_name": str(row.get("Release") or "").strip(),
                    "release_at": pd.Timestamp(released).tz_localize(EASTERN),
                    "source": "U.S. Bureau of Economic Analysis",
                    "source_url": BEA_SCHEDULE_URL,
                }
            )
    return pd.DataFrame(events, columns=["release_name", "release_at", "source", "source_url"])


@st.cache_data(ttl=21_600, show_spinner=False)
def fetch_release_calendar() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    try:
        response = browser_requests.get(BLS_CALENDAR_URL, headers=_request_headers(), impersonate="chrome", timeout=12)
        response.raise_for_status()
        parsed = _parse_bls_calendar(response.text)
        if not parsed.empty:
            frames.append(parsed)
    except Exception:
        pass
    try:
        response = browser_requests.get(BEA_SCHEDULE_URL, headers=_request_headers(), impersonate="chrome", timeout=12)
        response.raise_for_status()
        parsed = _parse_bea_schedule(response.text)
        if not parsed.empty:
            frames.append(parsed)
    except Exception:
        pass
    if not frames:
        return pd.DataFrame(columns=["release_name", "release_at", "source", "source_url"])
    return pd.concat(frames, ignore_index=True).sort_values("release_at").drop_duplicates(["release_name", "release_at"])


def _release_context(
    release_name: str,
    calendar: pd.DataFrame,
    current: pd.Timestamp,
    observation_date: object | None = None,
    frequency: str = "",
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if not release_name or calendar.empty:
        return None, None
    names = calendar["release_name"].astype(str)
    exact = names.str.casefold() == release_name.casefold()
    contains = names.str.contains(re.escape(release_name), case=False, na=False)
    matches = calendar[exact | contains].copy()
    if matches.empty:
        return None, None
    releases = pd.to_datetime(matches["release_at"], errors="coerce", utc=True).dropna().dt.tz_convert(EASTERN).sort_values()
    last_values = releases[releases <= current]
    next_values = releases[releases > current]
    release_at = last_values.iloc[-1] if not last_values.empty else None
    observed = pd.to_datetime(observation_date, errors="coerce")
    if frequency == "Monthly" and not pd.isna(observed):
        target_period = pd.Period(pd.Timestamp(observed), freq="M") + 1
        period_matches = releases[
            (releases.dt.year == target_period.year) & (releases.dt.month == target_period.month)
        ]
        if not period_matches.empty:
            release_at = period_matches.iloc[0]
    return (release_at, next_values.iloc[0] if not next_values.empty else None)


def _tracked_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    if calendar.empty:
        return calendar.copy()
    names = calendar["release_name"].astype(str)
    mask = pd.Series(False, index=calendar.index)
    for term in TRACKED_RELEASE_TERMS:
        mask |= names.str.contains(re.escape(term), case=False, na=False)
    return calendar[mask].copy()


def _bls_payload(series_ids: list[str]) -> dict[str, Any]:
    current_year = now_et().year
    payload: dict[str, Any] = {
        "seriesid": series_ids,
        "startyear": str(current_year - 1),
        "endyear": str(current_year),
    }
    api_key = secret_or_env("BLS_API_KEY")
    if api_key:
        payload["registrationkey"] = api_key
    return payload


def _fetch_bls_observations() -> dict[str, pd.DataFrame]:
    response = requests.post(
        BLS_API_URL,
        json=_bls_payload(list(BLS_SERIES)),
        headers=_request_headers(),
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json() or {}
    if str(payload.get("status")) != "REQUEST_SUCCEEDED":
        raise RuntimeError("BLS API request did not succeed.")
    result: dict[str, pd.DataFrame] = {}
    for series in (payload.get("Results") or {}).get("series") or []:
        series_id = str(series.get("seriesID") or "")
        rows = []
        for item in series.get("data") or []:
            period = str(item.get("period") or "")
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            year = int(item.get("year"))
            value = to_float(item.get("value"))
            if value is None:
                continue
            observation_date = pd.Timestamp(year=year, month=month, day=1)
            rows.append(
                {
                    "observation_date": observation_date,
                    "observation_period": f"{item.get('periodName')} {year}",
                    "value": value,
                    "preliminary": any(
                        str(note.get("code") or "").upper() == "P"
                        for note in (item.get("footnotes") or [])
                        if isinstance(note, dict)
                    ),
                }
            )
        result[series_id] = pd.DataFrame(rows).sort_values("observation_date", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
    return result


def _fred_observations(series_id: str, limit: int = 4) -> pd.DataFrame:
    api_key = secret_or_env("FRED_API_KEY")
    if not api_key:
        return pd.DataFrame()
    response = requests.get(
        f"{FRED_API_URL}/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        headers=_request_headers(),
        timeout=12,
    )
    if response.status_code == 429:
        raise RuntimeError("FRED rate limit reached.")
    response.raise_for_status()
    rows = []
    for item in (response.json() or {}).get("observations") or []:
        value = to_float(item.get("value"))
        observed = pd.to_datetime(item.get("date"), errors="coerce")
        if value is None or pd.isna(observed):
            continue
        rows.append({"observation_date": pd.Timestamp(observed), "value": value})
    return pd.DataFrame(rows).sort_values("observation_date", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()


def _audit_row(row: dict[str, object], current: pd.Timestamp) -> tuple[str, str]:
    value = to_float(row.get("value"))
    observed = _as_eastern(row.get("observation_date"))
    released = _as_eastern(row.get("official_release_at"))
    source_url = str(row.get("source_url") or "")
    if value is None:
        return "BLOCKED", "No official value returned; the row is suppressed."
    if observed is not None and observed > current:
        return "BLOCKED", "Observation period is future-dated."
    if released is not None and released > current:
        return "BLOCKED", "The official release is still embargoed or scheduled."
    if not source_url.startswith("https://"):
        return "REVIEW", "Official source link is missing."
    if released is None and str(row.get("frequency")) not in {"Daily", "Weekly"}:
        return "REVIEW", "Value is official, but the release-calendar match is unavailable."
    return "VERIFIED", "Official observation and release timing passed validation."


def _build_row(
    series_id: str,
    metadata: dict[str, str],
    observations: pd.DataFrame,
    calendar: pd.DataFrame,
    data_source: str,
    current: pd.Timestamp,
) -> dict[str, object] | None:
    if observations.empty:
        return None
    latest = observations.iloc[0]
    previous = observations.iloc[1] if len(observations) > 1 else {}
    value = to_float(latest.get("value"))
    prior = to_float(previous.get("value")) if hasattr(previous, "get") else None
    change = value - prior if value is not None and prior is not None else None
    change_pct = change / prior * 100 if change is not None and prior not in (None, 0) else None
    observed = pd.Timestamp(latest.get("observation_date"))
    release_name = metadata.get("release_name", "")
    frequency = metadata.get("frequency", "")
    release_at, next_release_at = _release_context(release_name, calendar, current, observed, frequency)
    period = str(latest.get("observation_period") or observed.strftime("%b %Y"))
    kind = metadata.get("display_kind", "index")
    row: dict[str, object] = {
        "indicator": metadata["indicator"],
        "series_id": series_id,
        "value": value,
        "previous_value": prior,
        "change": change,
        "change_pct": change_pct,
        "display_value": _format_value(value, kind),
        "display_change": _format_change(change, change_pct, kind),
        "observation_date": observed.date(),
        "observation_period": period,
        "official_release_at": release_at,
        "next_release_at": next_release_at,
        "provider_updated_at": release_at,
        "frequency": metadata["frequency"],
        "units": metadata["units"],
        "source": metadata["source"],
        "source_url": metadata["source_url"],
        "data_source": data_source,
        "last_refresh": current,
    }
    status, message = _audit_row(row, current)
    latest_scheduled, _ = _release_context(release_name, calendar, current)
    if (
        status == "VERIFIED"
        and frequency == "Monthly"
        and release_at is not None
        and latest_scheduled is not None
        and latest_scheduled > release_at
    ):
        status = "REVIEW"
        message = "A newer release is scheduled as published, but the provider still returns the prior observation period."
    row["audit_status"] = status
    row["audit_message"] = message
    return row


def _load_macro_dashboard() -> pd.DataFrame:
    current = pd.Timestamp(now_et())
    calendar = fetch_release_calendar()
    rows: list[dict[str, object]] = []
    try:
        bls_data = _fetch_bls_observations()
    except (requests.RequestException, RuntimeError, ValueError):
        bls_data = {}
    for series_id, metadata in BLS_SERIES.items():
        row = _build_row(series_id, metadata, bls_data.get(series_id, pd.DataFrame()), calendar, "BLS Public Data API", current)
        if row and row.get("audit_status") != "BLOCKED":
            rows.append(row)
    if secret_or_env("FRED_API_KEY"):
        for series_id, metadata in FRED_SERIES.items():
            try:
                observations = _fred_observations(series_id)
            except (requests.RequestException, RuntimeError, ValueError):
                continue
            row = _build_row(series_id, metadata, observations, calendar, "FRED official series", current)
            if row and row.get("audit_status") != "BLOCKED":
                rows.append(row)
    live = pd.DataFrame(rows, columns=MACRO_COLUMNS) if rows else _empty_macro()
    _save_verified_snapshots(live)
    snapshots = _load_verified_snapshots()
    if not snapshots.empty:
        live_ids = set(live["series_id"].astype(str)) if not live.empty else set()
        snapshots = snapshots[~snapshots["series_id"].astype(str).isin(live_ids)]
    frame = pd.concat([live, snapshots], ignore_index=True) if not snapshots.empty else live
    if frame.empty:
        return _empty_macro()
    order = ["Consumer Price Index", "PCE Price Index", "Unemployment Rate", "Total Nonfarm Payrolls", "Initial Jobless Claims", "Effective Fed Funds Rate", "10Y Treasury Yield", "2Y Treasury Yield", "Real GDP", "Retail Sales"]
    frame["_order"] = frame["indicator"].map({name: idx for idx, name in enumerate(order)}).fillna(len(order))
    return frame.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def macro_poll_interval_seconds(calendar: pd.DataFrame | None = None, current: object | None = None) -> int:
    parsed_current = _as_eastern(current)
    now = parsed_current if parsed_current is not None else pd.Timestamp(now_et())
    schedule = _tracked_calendar(fetch_release_calendar() if calendar is None else calendar)
    if schedule.empty:
        return 300 if secret_or_env("BLS_API_KEY") else 21_600
    releases = pd.to_datetime(schedule["release_at"], errors="coerce", utc=True).dropna().dt.tz_convert(EASTERN)
    deltas = [(release - now).total_seconds() for release in releases]
    near_release = any(-900 <= delta <= 300 for delta in deltas)
    if near_release:
        return 15 if secret_or_env("BLS_API_KEY") else 60
    baseline = 300 if secret_or_env("BLS_API_KEY") else 21_600
    future = [delta for delta in deltas if delta > 300]
    if not future:
        return baseline
    wake_for_release = max(15, min(future) - 300)
    return int(min(baseline, wake_for_release))


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_macro_dashboard_cached(refresh_bucket: int) -> pd.DataFrame:
    del refresh_bucket
    return _load_macro_dashboard()


def fetch_macro_dashboard() -> pd.DataFrame:
    """Return only official macro observations with release-aware caching."""

    cadence = macro_poll_interval_seconds()
    bucket = int(time.time() // max(cadence, 1))
    frame = _fetch_macro_dashboard_cached(bucket)
    verified_bls = 0
    if not frame.empty:
        verified_bls = int(
            (
                frame["series_id"].astype(str).isin(BLS_SERIES)
                & frame["audit_status"].astype(str).eq("VERIFIED")
            ).sum()
        )
    if verified_bls == len(BLS_SERIES):
        return frame
    retry_seconds = min(cadence, 300)
    retry_bucket = -(int(time.time() // max(retry_seconds, 1)) + 1)
    return _fetch_macro_dashboard_cached(retry_bucket)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_series(series_id: str) -> pd.DataFrame:
    """Fetch a single official FRED series when a FRED key is configured."""

    series = str(series_id or "").strip().upper()
    metadata = FRED_SERIES.get(series)
    if not series or not metadata or not secret_or_env("FRED_API_KEY"):
        return _empty_macro()
    try:
        observations = _fred_observations(series, limit=12)
    except (requests.RequestException, RuntimeError, ValueError):
        return _empty_macro()
    row = _build_row(series, metadata, observations, fetch_release_calendar(), "FRED official series", pd.Timestamp(now_et()))
    return pd.DataFrame([row], columns=MACRO_COLUMNS) if row else _empty_macro()


def audit_macro_dashboard(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    data = fetch_macro_dashboard() if frame is None else frame.copy()
    columns = ["indicator", "audit_status", "audit_message", "observation_period", "official_release_at", "next_release_at", "source", "source_url"]
    if data.empty:
        return pd.DataFrame(
            [
                {
                    "indicator": "Macro dashboard",
                    "audit_status": "BLOCKED",
                    "audit_message": "No official provider responded. No synthetic values are displayed.",
                    "observation_period": "N/A",
                    "official_release_at": None,
                    "next_release_at": None,
                    "source": "Official providers",
                    "source_url": "",
                }
            ],
            columns=columns,
        )
    return data[columns].copy()


def next_scheduled_macro_release(calendar: pd.DataFrame | None = None, current: object | None = None) -> dict[str, object]:
    parsed_current = _as_eastern(current)
    now = parsed_current if parsed_current is not None else pd.Timestamp(now_et())
    schedule = _tracked_calendar(fetch_release_calendar() if calendar is None else calendar.copy())
    if schedule.empty:
        return {}
    releases = pd.to_datetime(schedule["release_at"], errors="coerce", utc=True)
    schedule = schedule.assign(_release_at=releases.dt.tz_convert(EASTERN))
    schedule["_priority"] = schedule["release_name"].map(RELEASE_PRIORITY).fillna(len(RELEASE_PRIORITY))
    future = schedule[schedule["_release_at"] > now].sort_values(["_release_at", "_priority"])
    if future.empty:
        return {}
    row = future.iloc[0]
    return {
        "release_name": row.get("release_name"),
        "release_at": row.get("_release_at"),
        "source": row.get("source"),
        "source_url": row.get("source_url"),
    }
