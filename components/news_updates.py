from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from services.news_service import fetch_company_news, fetch_market_headlines
from utils.formatting import clean_ticker
from utils.rendering import render_html


def _news_time(value: object) -> str:
    try:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            return "N/A"
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("America/New_York")
        else:
            timestamp = timestamp.tz_convert("America/New_York")
        return timestamp.strftime("%m/%d %H:%M ET")
    except Exception:
        return "N/A"


def _sentiment_tone(value: object) -> str:
    lowered = str(value or "").casefold()
    if "bull" in lowered or "positive" in lowered:
        return "good"
    if "bear" in lowered or "negative" in lowered:
        return "bad"
    if "mixed" in lowered:
        return "warn"
    return "neutral"


def _news_markup(frame: pd.DataFrame, title: str, subtitle: str, limit: int = 6) -> str:
    if frame is None or frame.empty:
        return f"""
        <div class="pt-shell pt-live-section">
          <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div><span>Every 5min</span></div>
          <p class="pt-placeholder">No reliable headlines available.</p>
        </div>
        """
    rows = ""
    for _, row in frame.head(limit).iterrows():
        sentiment = str(row.get("sentiment") or "Neutral")
        url = str(row.get("url") or "").strip()
        source = escape(str(row.get("source") or row.get("data_source") or "News provider"))
        headline = escape(str(row.get("headline") or "Untitled headline"))
        ticker = escape(str(row.get("ticker") or "Market"))
        link = f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">Open</a>' if url else ""
        rows += f"""
        <tr>
          <td><b>{ticker}</b></td>
          <td>{headline}<small>{escape(str(row.get("summary") or ""))}</small></td>
          <td>{source}</td>
          <td>{escape(_news_time(row.get("published_at")))}</td>
          <td><span class="pt-live-badge {_sentiment_tone(sentiment)}">{escape(sentiment)}</span></td>
          <td>{link}</td>
        </tr>
        """
    return f"""
    <div class="pt-shell pt-live-section">
      <div class="pt-live-section-head"><div><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div><span>Every 5min</span></div>
      <table class="pt-table pt-live-table pt-news-live-table">
        <thead><tr><th>Ticker</th><th>Headline</th><th>Source</th><th>Time</th><th>Sentiment</th><th>URL</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


@st.fragment(run_every="5min")
def _news_fragment(ticker: str, tickers: tuple[str, ...], title: str) -> None:
    try:
        if ticker:
            frame = fetch_company_news(ticker)
            subtitle = f"Company-specific headlines for {ticker}."
        elif tickers:
            frames = [fetch_company_news(symbol) for symbol in tickers[:8]]
            frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            frame = frame.sort_values("published_at", ascending=False) if not frame.empty else frame
            subtitle = "Watchlist headlines from the configured news provider."
        else:
            frame = fetch_market_headlines()
            subtitle = "Market-wide headlines from the configured news provider."
        source = str(frame["data_source"].dropna().iloc[0]) if frame is not None and not frame.empty and "data_source" in frame else "News provider"
        mark_fragment_refresh("news", 300, "OK", source)
        render_html(_news_markup(frame, title, subtitle))
    except Exception as exc:
        mark_fragment_refresh("news", 300, "Error", str(exc)[:180])
        st.warning(f"News updates are temporarily unavailable: {exc}")


def render_news_updates(ticker: str | None = None, tickers: list[str] | None = None, title: str = "Market Headlines") -> None:
    symbol = clean_ticker(ticker) if ticker else ""
    cleaned = tuple(clean_ticker(value) for value in (tickers or []) if clean_ticker(value))
    _news_fragment(symbol, cleaned, title)
