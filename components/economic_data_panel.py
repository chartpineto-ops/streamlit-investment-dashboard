from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from services.economic_data_service import fetch_macro_dashboard
from utils.formatting import fmt_number, fmt_percent, now_et, to_float
from utils.refresh_debug import is_refresh_stale, latest_refresh_from_frame, log_refresh, render_refresh_debug
from utils.rendering import render_html


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
    sources = frame["data_source"].dropna() if frame is not None and not frame.empty and "data_source" in frame else pd.Series(dtype=object)
    source_label = str(sources.iloc[0]) if not sources.empty else ""
    provider_notice = ""
    if "provider not configured" in source_label.casefold() or "demo" in source_label.casefold():
        provider_notice = '<p class="pt-placeholder">Provider not configured. Showing clearly labelled fallback macro data until FRED_API_KEY is configured.</p>'
    if frame is None or frame.empty:
        return f"""
        <div class="pt-shell pt-live-section">
          <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>Macro indicators refresh independently from prices and news.</p></div><span>Every 30min</span></div>
          <p class="pt-placeholder">Provider not configured or no macro data available.</p>
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
      {provider_notice}
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
        sources = frame["data_source"].dropna() if frame is not None and not frame.empty and "data_source" in frame else pd.Series(dtype=object)
        source = str(sources.iloc[0]) if not sources.empty else "Macro provider"
        last_refresh = latest_refresh_from_frame(frame) or now_et()
        stale = is_refresh_stale(last_refresh, 1800)
        status = "Fallback" if "provider not configured" in source.casefold() or "demo" in source.casefold() else "OK"
        log_refresh("macro", source)
        mark_fragment_refresh("macro", 1800, status, source, last_refresh=last_refresh, data_source=source, cache_ttl=3600, rows=0 if frame is None else len(frame), is_stale=stale)
        render_html(_macro_markup(frame, title))
        render_refresh_debug("macro", last_refresh=last_refresh, data_source=source, cache_ttl=3600, rows=0 if frame is None else len(frame), is_stale=stale)
    except Exception as exc:
        error = str(exc)[:180]
        mark_fragment_refresh("macro", 1800, "Error", error, last_refresh=now_et(), data_source="Macro provider", cache_ttl=3600, rows=0, is_stale=True, error=error)
        st.warning(f"Economic data is temporarily unavailable: {exc}")
        render_refresh_debug("macro", last_refresh=now_et(), data_source="Macro provider", cache_ttl=3600, rows=0, is_stale=True, error=error)


def render_economic_data_panel(title: str = "Economic Data Snapshot") -> None:
    _economic_data_fragment(title)
