from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from services.live_quotes import fetch_latest_quotes
from utils.formatting import fmt_daily_move, fmt_price, now_et, safe_format_datetime, to_float
from utils.refresh_debug import is_refresh_stale, latest_refresh_from_frame, log_refresh, render_refresh_debug
from utils.rendering import render_html


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
        render_html(
            """
            <div class="pt-market-marquee-empty">
              Live ticker unavailable. Add tickers to the watchlist or refresh when the quote provider reconnects.
            </div>
            """
        )
        return

    valid = quotes[pd.to_numeric(quotes.get("price"), errors="coerce").notna()].copy()
    if valid.empty:
        error = str(quotes.get("error", pd.Series(["Quote provider unavailable."])).dropna().head(1).iloc[0])
        render_html(
            f"""
            <div class="pt-market-marquee-empty">
              Live ticker unavailable. {escape(error)}
            </div>
            """
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
        bid = escape(fmt_price(row.get("bid")))
        ask = escape(fmt_price(row.get("ask")))
        title = f"{source} | {market_state} | Bid {bid} | Ask {ask} | Updated {updated}"
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
    render_html(
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
        """
    )


def render_live_ticker(tickers: list[str], refresh_seconds: int = 5) -> None:
    """Render the moving ticker strip without refreshing the full Streamlit app."""

    cleaned = tuple(dict.fromkeys(tickers or DEFAULT_LIVE_TICKERS))
    cadence_seconds = max(1, int(refresh_seconds or 5))

    # Browser/page auto-refresh was removed because it reran expensive dashboard
    # sections. This fragment gives only the ticker strip a small, isolated pulse.
    @st.fragment(run_every=f"{cadence_seconds}s")
    def _live_ticker_fragment() -> None:
        try:
            quotes = fetch_latest_quotes(list(cleaned))
            sources = quotes["data_source"].dropna() if quotes is not None and not quotes.empty and "data_source" in quotes else pd.Series(dtype=object)
            source = str(sources.iloc[0]) if not sources.empty else "Quote provider"
            last_refresh = latest_refresh_from_frame(quotes) or now_et()
            stale = is_refresh_stale(last_refresh, cadence_seconds)
            error = ""
            if quotes is not None and not quotes.empty and "error" in quotes:
                error = "; ".join(str(value) for value in quotes["error"].dropna().unique() if str(value))[:180]
            log_refresh("live_prices", source)
            mark_fragment_refresh(
                "live_prices",
                cadence_seconds,
                "OK",
                source,
                last_refresh=last_refresh,
                data_source=source,
                cache_ttl=5,
                rows=0 if quotes is None else len(quotes),
                is_stale=stale,
                error=error,
            )
            _render_ticker_markup(quotes)
            render_refresh_debug("live_prices", last_refresh=last_refresh, data_source=source, cache_ttl=5, rows=0 if quotes is None else len(quotes), is_stale=stale, error=error)
        except Exception as exc:
            error = str(exc)[:180]
            last_refresh = now_et()
            mark_fragment_refresh("live_prices", cadence_seconds, "Error", error, last_refresh=last_refresh, data_source="Quote provider", cache_ttl=5, rows=0, is_stale=True, error=error)
            render_html(
                f"""
                <div class="pt-market-marquee-empty">
                  Live ticker unavailable. {escape(error)}
                </div>
                """
            )
            render_refresh_debug("live_prices", last_refresh=last_refresh, data_source="Quote provider", cache_ttl=5, rows=0, is_stale=True, error=error)

    _live_ticker_fragment()
