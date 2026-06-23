from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from utils.formatting import now_et
from utils.rendering import render_html, safe_text


def log_refresh(component_name: str, data_source: str = "") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[REFRESH] {component_name} refreshed at {timestamp} source={data_source}", flush=True)


def latest_refresh_from_frame(frame: pd.DataFrame | None, columns: tuple[str, ...] = ("last_refresh", "Last Updated", "last_updated")) -> object | None:
    if frame is None or frame.empty:
        return None
    for column in columns:
        if column in frame:
            values = pd.to_datetime(frame[column], errors="coerce").dropna()
            if not values.empty:
                return values.max()
    return None


def freshness_age_seconds(value: object) -> float | None:
    if value is None:
        return None
    try:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            return None
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("America/New_York")
        else:
            timestamp = timestamp.tz_convert("America/New_York")
        return max(0.0, (now_et() - timestamp.to_pydatetime()).total_seconds())
    except Exception:
        return None


def is_refresh_stale(value: object, cadence_seconds: int, multiplier: float = 2.0) -> bool:
    age = freshness_age_seconds(value)
    if age is None:
        return True
    return age > max(1, cadence_seconds) * multiplier


def render_refresh_debug(
    component_name: str,
    *,
    last_refresh: object = None,
    data_source: str = "",
    cache_ttl: int | str = "",
    rows: int | None = None,
    is_stale: bool | None = None,
    error: str = "",
) -> None:
    if not st.session_state.get("show_refresh_debug", False):
        return

    stale_label = "Unknown" if is_stale is None else "Yes" if is_stale else "No"
    rows_label = "N/A" if rows is None else str(rows)
    refresh_label = "N/A"
    if last_refresh is not None:
        try:
            timestamp = pd.Timestamp(last_refresh)
            if timestamp.tz is None:
                timestamp = timestamp.tz_localize("America/New_York")
            else:
                timestamp = timestamp.tz_convert("America/New_York")
            refresh_label = timestamp.strftime("%H:%M:%S ET")
        except Exception:
            refresh_label = str(last_refresh)

    render_html(
        f"""
        <div class="pt-refresh-debug">
          <strong>{safe_text(component_name)}</strong>
          <span>last fetch {safe_text(refresh_label)}</span>
          <span>source {safe_text(data_source or "N/A")}</span>
          <span>cache ttl {safe_text(cache_ttl or "N/A")}</span>
          <span>rows {safe_text(rows_label)}</span>
          <span>stale {safe_text(stale_label)}</span>
          {f'<em>{safe_text(error)}</em>' if error else ''}
        </div>
        <style>
        .pt-refresh-debug {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            margin: 6px 0 10px;
            padding: 6px 8px;
            border: 1px dashed rgba(110, 130, 150, 0.45);
            border-radius: 8px;
            color: #9aa8b6;
            font-size: 11px;
            background: rgba(10, 16, 24, 0.55);
        }}
        .pt-refresh-debug strong {{ color: #f3f6f9; }}
        .pt-refresh-debug em {{ color: #ff8a8a; font-style: normal; }}
        </style>
        """
    )
