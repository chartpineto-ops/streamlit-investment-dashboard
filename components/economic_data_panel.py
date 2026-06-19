from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from services.economic_data_service import fetch_macro_dashboard
from utils.formatting import fmt_number, fmt_percent, to_float


def _macro_value(row: pd.Series) -> str:
    source = str(row.get("source") or "")
    value = to_float(row.get("value"))
    if value is None:
        return "N/A"
    if source == "%":
        return f"{value:.2f}%"
    if source in {"$B", "$M"}:
        return f"{value:,.1f}{source.replace('$', '')}"
    if source == "K":
        return f"{value:,.0f}K"
    return fmt_number(value, 1)


def _macro_markup(frame: pd.DataFrame, title: str) -> str:
    if frame is None or frame.empty:
        return f"""
        <div class="pt-shell pt-live-section">
          <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>Macro indicators refresh independently from prices and news.</p></div><span>Every 30min</span></div>
          <p class="pt-placeholder">No macro data available.</p>
        </div>
        """
    rows = ""
    for _, row in frame.head(12).iterrows():
        change = to_float(row.get("change_pct"))
        tone = "good" if (change or 0) > 0 else "bad" if (change or 0) < 0 else "neutral"
        rows += f"""
        <tr>
          <td><b>{escape(str(row.get("indicator") or ""))}</b></td>
          <td>{escape(_macro_value(row))}</td>
          <td>{escape(fmt_percent(change, 2, signed=True))}</td>
          <td>{escape(str(row.get("release_date") or "N/A"))}</td>
          <td><span class="{tone}">{escape(str(row.get("data_source") or row.get("source") or "Macro provider"))}</span></td>
        </tr>
        """
    return f"""
    <div class="pt-shell pt-live-section">
      <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>CPI, rates, labor, GDP, retail sales, PMI, and sentiment.</p></div><span>Every 30min</span></div>
      <table class="pt-table pt-live-table">
        <thead><tr><th>Indicator</th><th>Latest</th><th>Change</th><th>Release</th><th>Source</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


@st.fragment(run_every="30min")
def _economic_data_fragment(title: str) -> None:
    try:
        frame = fetch_macro_dashboard()
        source = str(frame["data_source"].dropna().iloc[0]) if frame is not None and not frame.empty and "data_source" in frame else "Macro provider"
        mark_fragment_refresh("macro", 1800, "OK", source)
        st.markdown(_macro_markup(frame, title), unsafe_allow_html=True)
    except Exception as exc:
        mark_fragment_refresh("macro", 1800, "Error", str(exc)[:180])
        st.warning(f"Economic data is temporarily unavailable: {exc}")


def render_economic_data_panel(title: str = "Economic Data Snapshot") -> None:
    _economic_data_fragment(title)
