from __future__ import annotations

from datetime import timedelta
from html import escape

import pandas as pd
import streamlit as st

from utils.formatting import now_et


REFRESH_STATUS_KEY = "_pt_fragment_refresh_status"


def mark_fragment_refresh(name: str, cadence_seconds: int, status: str = "OK", message: str = "") -> None:
    registry = dict(st.session_state.get(REFRESH_STATUS_KEY, {}))
    registry[name] = {
        "last_refresh": now_et(),
        "cadence_seconds": cadence_seconds,
        "status": status,
        "message": message,
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
    if status and status != "ok":
        return "bad"
    timestamp = entry.get("last_refresh")
    cadence = int(entry.get("cadence_seconds") or 0)
    if not timestamp or not cadence:
        return "warn"
    try:
        age = now_et() - pd.Timestamp(timestamp).to_pydatetime()
    except Exception:
        return "warn"
    return "warn" if age > timedelta(seconds=cadence * 2) else "good"


@st.fragment(run_every="60s")
def render_freshness_status_row() -> None:
    registry = dict(st.session_state.get(REFRESH_STATUS_KEY, {}))
    labels = [
        ("Live prices", "live_prices"),
        ("Movers", "market_movers"),
        ("News", "news"),
        ("Macro", "macro"),
    ]
    items = []
    for label, key in labels:
        entry = registry.get(key, {})
        tone = _status_tone(entry)
        message = escape(str(entry.get("message") or entry.get("status") or "Pending"))
        items.append(
            f"""
            <span title="{message}">
              <b>{escape(label)}</b>
              <em class="{tone}">refreshed {_time_label(entry.get("last_refresh"))}</em>
            </span>
            """
        )
    st.markdown(f'<div class="pt-refresh-status-row">{"".join(items)}</div>', unsafe_allow_html=True)
