from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from utils.formatting import fmt_date, now_et, tone_for_number
from utils.rendering import render_html


def section(title: str, subtitle: str | None = None) -> None:
    render_html('<div class="section-rule"></div>')
    st.subheader(title)
    if subtitle:
        render_html(f'<div class="terminal-subtitle">{escape(subtitle)}</div>')


def metric_card(label: str, value: str, caption: str = "", tone: str = "neutral", small: bool = False) -> str:
    tone_class = {"good": "rt-good", "bad": "rt-bad", "warn": "rt-warn"}.get(tone, "rt-neutral")
    size_class = " small" if small else ""
    return (
        f'<div class="rt-card{size_class}">'
        f'<div class="rt-label">{escape(label)}</div>'
        f'<div class="rt-value {tone_class}">{escape(str(value))}</div>'
        f'<div class="rt-caption">{escape(str(caption))}</div>'
        "</div>"
    )


def render_metric_grid(cards: list[tuple[str, str, str, str]], columns: int = 4, small: bool = False) -> None:
    if not cards:
        return
    cols = st.columns(columns)
    for idx, (label, value, caption, tone) in enumerate(cards):
        with cols[idx % columns]:
            render_html(metric_card(label, value, caption, tone, small=small))


def badge(label: str, tone: str = "neutral") -> str:
    tone_class = tone if tone in {"good", "bad", "warn"} else ""
    return f'<span class="rt-badge {tone_class}">{escape(label)}</span>'


def source_line(source: str = "N/A", updated=None, status: str = "") -> None:
    parts = []
    if source:
        parts.append(f"Source: {source}")
    if status:
        parts.append(f"Status: {status}")
    if updated is not None:
        parts.append(f"Updated: {fmt_date(updated)}")
    if not parts:
        parts.append(f"Updated: {fmt_date(now_et())}")
    render_html(f'<div class="source-line">{" | ".join(escape(p) for p in parts)}</div>')


def quote_header(quote: dict) -> None:
    ticker = quote.get("ticker") or "N/A"
    name = quote.get("company_name") or ticker
    price = quote.get("price")
    change_pct = quote.get("daily_change_pct")
    change = quote.get("daily_change")
    tone = tone_for_number(change_pct)
    logo_url = quote.get("logo_url")
    initials = quote.get("fallback_initials") or "".join(ch for ch in ticker if ch.isalnum())[:2] or "PT"
    if logo_url:
        logo = f'<img src="{escape(str(logo_url))}" alt="{escape(ticker)} logo" onerror="this.style.display=\'none\'; this.parentNode.textContent=\'{escape(initials)}\';">'
    else:
        logo = escape(initials)
    from utils.formatting import fmt_percent, fmt_price

    change_text = fmt_percent(change_pct, decimals=2, signed=True) if change_pct is not None else "N/A"
    price_text = fmt_price(price)
    change_abs = f"{'+' if change > 0 else '-' if change < 0 else ''}{fmt_price(abs(change))}" if change is not None else ""
    render_html(
        f"""
        <div class="quote-card">
          <div class="quote-logo">{logo}</div>
          <div>
            <div class="quote-main">{escape(ticker)} <span class="{ {'good':'rt-good','bad':'rt-bad'}.get(tone, 'rt-neutral') }" style="font-size:1.05rem;">{escape(change_text)}</span></div>
            <div class="quote-sub">{escape(name)}</div>
            <div class="quote-sub">{escape(str(quote.get("sector") or "N/A"))} / {escape(str(quote.get("industry") or "N/A"))}</div>
            <div class="quote-sub" style="color:#e8f2f4;">{escape(price_text)} <span class="rt-neutral">{escape(change_abs)}</span></div>
          </div>
        </div>
        """
    )


def clean_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    return frame.replace({pd.NA: "N/A"}).fillna("N/A")


def empty_state(message: str) -> None:
    st.info(message)
