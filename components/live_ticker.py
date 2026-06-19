from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from services.live_quotes import fetch_latest_quotes
from utils.formatting import fmt_daily_move, fmt_price, now_et, safe_format_datetime, to_float


DEFAULT_LIVE_TICKERS = ["SPY", "QQQ", "DIA", "IWM", "NVDA", "MSFT", "AAPL", "MRVL", "AMPX", "IONQ"]


def _caption_time(value: object) -> str:
    try:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            raise ValueError("missing timestamp")
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("America/New_York")
        else:
            timestamp = timestamp.tz_convert("America/New_York")
        return timestamp.strftime("%H:%M:%S ET")
    except Exception:
        return now_et().strftime("%H:%M:%S ET")


def _render_ticker_markup(quotes: pd.DataFrame) -> None:
    if quotes is None or quotes.empty:
        st.markdown(
            """
            <div class="pt-market-marquee-empty">
              Live ticker unavailable. Add tickers to the watchlist or refresh when the quote provider reconnects.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    valid = quotes[pd.to_numeric(quotes.get("price"), errors="coerce").notna()].copy()
    if valid.empty:
        error = str(quotes.get("error", pd.Series(["Quote provider unavailable."])).dropna().head(1).iloc[0])
        st.markdown(
            f"""
            <div class="pt-market-marquee-empty">
              Live ticker unavailable. {escape(error)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    items = ""
    for _, row in valid.iterrows():
        symbol = escape(str(row.get("ticker") or ""))
        price = escape(fmt_price(row.get("price")))
        change_pct = to_float(row.get("change_pct"))
        move_label = escape(fmt_daily_move(change_pct))
        tone = "good" if (change_pct or 0) > 0 else "bad" if (change_pct or 0) < 0 else "neutral"
        market_state = escape(str(row.get("market_state") or "Unknown"))
        source = escape(str(row.get("data_source") or "Quote provider"))
        updated = escape(safe_format_datetime(row.get("timestamp") or row.get("last_refresh")))
        title = f"{source} | {market_state} | Updated {updated}"
        items += f"""
        <span title="{title}">
          <b>{symbol}</b>
          <strong>{price}</strong>
          <em class="{tone}">{move_label}</em>
        </span>
        """

    last_refresh = _caption_time(valid.get("last_refresh", pd.Series(dtype=object)).dropna().max())
    sources = ", ".join(sorted({str(value) for value in valid.get("data_source", pd.Series(dtype=object)).dropna()}))
    unavailable = max(0, len(quotes) - len(valid))
    warning = f"<span>{unavailable} unavailable</span>" if unavailable else ""
    st.markdown(
        f"""
        <div class="pt-live-ticker-shell">
          <div class="pt-watch-tape pt-market-marquee" aria-label="Live market ticker">
            <div class="pt-watch-tape-inner">{items}{items}</div>
          </div>
          <div class="pt-live-ticker-caption">
            <span>Last refreshed: {escape(last_refresh)}</span>
            <span>{escape(sources or "Quote provider")}</span>
            {warning}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Browser/page auto-refresh was removed because it reran expensive dashboard
# sections. This fragment gives only the ticker strip a small, isolated pulse.
# Streamlit requires a static run_every decorator here; change "5s" below to
# adjust the default ticker interval, or replace fetch_latest_quotes with a
# WebSocket-backed provider in services/live_quotes.py later.
@st.fragment(run_every="5s")
def _live_ticker_fragment(tickers: tuple[str, ...]) -> None:
    quotes = fetch_latest_quotes(list(tickers))
    _render_ticker_markup(quotes)


def render_live_ticker(tickers: list[str], refresh_seconds: int = 5) -> None:
    """Render the moving ticker strip without refreshing the full Streamlit app."""

    del refresh_seconds
    cleaned = tuple(dict.fromkeys(tickers or DEFAULT_LIVE_TICKERS))
    _live_ticker_fragment(cleaned)
