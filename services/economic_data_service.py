from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

from utils.formatting import now_et, to_float


MACRO_COLUMNS = [
    "indicator",
    "value",
    "previous_value",
    "change",
    "change_pct",
    "release_date",
    "frequency",
    "source",
    "data_source",
    "last_refresh",
]

FRED_SERIES = {
    "CPI": ("CPIAUCSL", "Consumer Price Index", "Monthly", "Index"),
    "PCE": ("PCEPI", "PCE Price Index", "Monthly", "Index"),
    "UNEMPLOYMENT": ("UNRATE", "Unemployment Rate", "Monthly", "%"),
    "NFP": ("PAYEMS", "Nonfarm Payrolls", "Monthly", "K"),
    "INITIAL_CLAIMS": ("ICSA", "Initial Jobless Claims", "Weekly", ""),
    "FED_FUNDS": ("FEDFUNDS", "Fed Funds Rate", "Monthly", "%"),
    "DGS10": ("DGS10", "10Y Treasury Yield", "Daily", "%"),
    "DGS2": ("DGS2", "2Y Treasury Yield", "Daily", "%"),
    "GDP": ("GDPC1", "Real GDP", "Quarterly", "$B"),
    "RETAIL_SALES": ("RSAFS", "Retail Sales", "Monthly", "$M"),
    "ISM_PMI": ("NAPM", "ISM Manufacturing PMI", "Monthly", "Index"),
    "CONSUMER_SENTIMENT": ("UMCSENT", "Consumer Sentiment", "Monthly", "Index"),
}

DEMO_MACRO_ROWS = [
    ("Consumer Price Index", 318.9, 317.6, "Monthly", "Index"),
    ("PCE Price Index", 125.4, 124.9, "Monthly", "Index"),
    ("Unemployment Rate", 4.3, 4.3, "Monthly", "%"),
    ("Nonfarm Payrolls", 159_200, 159_085, "Monthly", "K"),
    ("Initial Jobless Claims", 233_000, 232_000, "Weekly", ""),
    ("Fed Funds Rate", 4.63, 4.63, "Monthly", "%"),
    ("10Y Treasury Yield", 4.48, 4.42, "Daily", "%"),
    ("2Y Treasury Yield", 4.05, 3.99, "Daily", "%"),
    ("Real GDP", 23_500.0, 23_410.0, "Quarterly", "$B"),
    ("Retail Sales", 724_000.0, 722_600.0, "Monthly", "$M"),
    ("ISM Manufacturing PMI", 52.7, 50.6, "Monthly", "Index"),
    ("Consumer Sentiment", 71.8, 70.2, "Monthly", "Index"),
]


def _empty_macro() -> pd.DataFrame:
    return pd.DataFrame(columns=MACRO_COLUMNS)


def _secret_or_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        secret_value = st.secrets.get(name, "")
    except Exception:
        secret_value = ""
    return str(secret_value or "").strip()


def _row(indicator: str, value, previous, release_date, frequency: str, source: str, data_source: str) -> dict[str, object]:
    number = to_float(value)
    prior = to_float(previous)
    change = number - prior if number is not None and prior is not None else None
    change_pct = (change / prior * 100) if change is not None and prior not in (None, 0) else None
    return {
        "indicator": indicator,
        "value": number,
        "previous_value": prior,
        "change": change,
        "change_pct": change_pct,
        "release_date": release_date,
        "frequency": frequency,
        "source": source,
        "data_source": data_source,
        "last_refresh": now_et(),
    }


def _demo_macro_dashboard() -> pd.DataFrame:
    refreshed = now_et()
    rows = []
    for indicator, value, previous, frequency, source in DEMO_MACRO_ROWS:
        rows.append(_row(indicator, value, previous, refreshed.date(), frequency, source, "Demo macro data"))
    return pd.DataFrame(rows, columns=MACRO_COLUMNS)


def _fred_observations(series_id: str, limit: int = 6) -> pd.DataFrame:
    api_key = _secret_or_env("FRED_API_KEY")
    if not api_key:
        return _empty_macro()
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=8,
    )
    if response.status_code == 429:
        raise RuntimeError("FRED rate limit reached.")
    response.raise_for_status()
    observations = (response.json() or {}).get("observations") or []
    rows = []
    for item in observations:
        value = to_float(item.get("value"))
        if value is None:
            continue
        rows.append({"date": item.get("date"), "value": value})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_series(series_id: str) -> pd.DataFrame:
    """Fetch a single economic series from FRED when configured."""

    series = str(series_id or "").strip().upper()
    if not series:
        return _empty_macro()
    try:
        observations = _fred_observations(series, limit=12)
    except Exception:
        return _empty_macro()
    if observations.empty:
        return _empty_macro()
    observations = observations.sort_values("date", ascending=False).reset_index(drop=True)
    previous = observations["value"].shift(-1)
    rows = []
    for idx, item in observations.iterrows():
        rows.append(_row(series, item["value"], previous.iloc[idx], item["date"], "Series", "FRED", "FRED"))
    return pd.DataFrame(rows, columns=MACRO_COLUMNS)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_macro_dashboard() -> pd.DataFrame:
    """Fetch macro dashboard data, using FRED when configured and demo fallback otherwise."""

    if not _secret_or_env("FRED_API_KEY"):
        return _demo_macro_dashboard()

    rows = []
    for _, (series_id, label, frequency, source_unit) in FRED_SERIES.items():
        try:
            observations = _fred_observations(series_id, limit=4)
        except Exception:
            observations = pd.DataFrame()
        if observations.empty:
            continue
        observations = observations.sort_values("date", ascending=False).reset_index(drop=True)
        latest = observations.iloc[0]
        previous = observations.iloc[1] if len(observations) > 1 else {}
        rows.append(_row(label, latest.get("value"), previous.get("value"), latest.get("date"), frequency, source_unit, "FRED"))
    if not rows:
        return _demo_macro_dashboard()
    return pd.DataFrame(rows, columns=MACRO_COLUMNS)
