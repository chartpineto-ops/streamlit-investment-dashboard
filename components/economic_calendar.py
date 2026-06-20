from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape

import pandas as pd
import streamlit as st

from data.economic_calendar import enrich_economic_calendar_events
from pineterminal.demo_data import ECONOMIC_CALENDAR_EVENTS
from utils.formatting import now_et
from utils.rendering import render_html


def _event_date(row: dict[str, object]) -> date | None:
    try:
        return datetime.strptime(str(row.get("date", "")), "%Y-%m-%d").date()
    except ValueError:
        return None


def _calendar_rows() -> tuple[list[dict[str, object]], dict[str, object]]:
    return enrich_economic_calendar_events(ECONOMIC_CALENDAR_EVENTS, current_date=now_et().date())


def _calendar_markup(events: list[dict[str, object]], title: str, days_forward: int) -> str:
    today = now_et().date()
    horizon = today + timedelta(days=max(1, days_forward))
    selected = []
    for row in events:
        event_day = _event_date(row)
        if event_day and today <= event_day <= horizon:
            selected.append(row)
    selected.sort(key=lambda row: (str(row.get("date")), str(row.get("time"))))
    if not selected:
        return f"""
        <div class="pt-shell pt-live-section">
          <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>Upcoming releases, consensus, prior, actual, and market impact tags.</p></div><span>Every 30min</span></div>
          <p class="pt-placeholder">No scheduled releases in the selected window.</p>
        </div>
        """
    rows = ""
    for row in selected[:10]:
        rows += f"""
        <tr>
          <td><b>{escape(str(row.get("date") or ""))}</b><small>{escape(str(row.get("time") or ""))}</small></td>
          <td>{escape(str(row.get("event") or ""))}</td>
          <td>{escape(str(row.get("estimate") or "TBD"))}</td>
          <td>{escape(str(row.get("previous") or "N/A"))}</td>
          <td>{escape(str(row.get("actual") or "Pending"))}</td>
          <td><span class="pt-live-badge neutral">{escape(str(row.get("impact") or "Medium"))}</span></td>
        </tr>
        """
    return f"""
    <div class="pt-shell pt-live-section">
      <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>Upcoming releases, consensus, prior, actual, and market impact tags.</p></div><span>Every 30min</span></div>
      <table class="pt-table pt-live-table">
        <thead><tr><th>Release Time</th><th>Event</th><th>Consensus</th><th>Prior</th><th>Actual</th><th>Importance</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


@st.fragment(run_every="30min")
def _economic_calendar_fragment(title: str, days_forward: int) -> None:
    try:
        events, _ = _calendar_rows()
        render_html(_calendar_markup(events, title, days_forward))
    except Exception as exc:
        st.warning(f"Economic calendar is temporarily unavailable: {exc}")


def render_economic_calendar_panel(title: str = "Economic Calendar", days_forward: int = 14) -> None:
    _economic_calendar_fragment(title, days_forward)
