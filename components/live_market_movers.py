from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from data.market_movers import get_whole_market_movers
from services.live_quotes import fetch_latest_quotes
from utils.formatting import clean_ticker, fmt_compact, fmt_daily_move, fmt_price, now_et, to_float
from utils.rendering import render_html


SECTOR_ETFS = ["XLK", "XLF", "XLV", "XLI", "XLE", "XLU", "XLY", "XLP", "XLC", "XLB", "SMH", "IGV"]


def _minute_cache_token() -> int:
    return int(now_et().timestamp() // 60)


def _row_markup(row: pd.Series, move_field: str = "Daily Move %") -> str:
    ticker = escape(str(row.get("Ticker") or row.get("ticker") or ""))
    price = fmt_price(row.get("Price", row.get("price")))
    move = to_float(row.get(move_field, row.get("change_pct"))) or 0.0
    volume = row.get("Volume", row.get("volume"))
    rel_volume = to_float(row.get("Relative Volume", row.get("relative_volume")))
    volume_label = fmt_compact(volume, 1)
    rel_label = f"{rel_volume:.1f}x" if rel_volume is not None else "N/A"
    tone = "good" if move > 0 else "bad" if move < 0 else "neutral"
    return f"""
    <tr>
      <td><b>{ticker}</b></td>
      <td>{escape(price)}</td>
      <td><span class="{tone}">{escape(fmt_daily_move(move))}</span></td>
      <td>{escape(volume_label)}</td>
      <td>{escape(rel_label)}</td>
    </tr>
    """


def _compact_table(frame: pd.DataFrame, title: str, limit: int = 5) -> str:
    if frame is None or frame.empty:
        return f'<div class="pt-live-panel"><h3>{escape(title)}</h3><p class="pt-placeholder">No movers available.</p></div>'
    rows = "".join(_row_markup(row) for _, row in frame.head(limit).iterrows())
    return f"""
    <div class="pt-live-panel">
      <h3>{escape(title)}</h3>
      <table class="pt-table pt-live-table">
        <thead><tr><th>Ticker</th><th>Price</th><th>Move</th><th>Volume</th><th>Rel Vol</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _quote_movers(tickers: list[str]) -> dict[str, pd.DataFrame]:
    quotes = fetch_latest_quotes(tickers)
    if quotes.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame(), "most_active": pd.DataFrame(), "status": pd.DataFrame()}
    frame = quotes.rename(columns={"ticker": "Ticker", "price": "Price", "change_pct": "Daily Move %"}).copy()
    frame["Volume"] = None
    frame["Relative Volume"] = None
    movers = frame[pd.to_numeric(frame["Daily Move %"], errors="coerce").notna()].copy()
    return {
        "gainers": movers[movers["Daily Move %"] > 0].sort_values("Daily Move %", ascending=False),
        "losers": movers[movers["Daily Move %"] < 0].sort_values("Daily Move %", ascending=True),
        "most_active": movers.sort_values("Ticker"),
        "status": quotes,
    }


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_market_movers_packet(cache_token: int) -> dict[str, object]:
    return get_whole_market_movers(min_price=2.0, min_volume=500_000, include_etfs=True, refresh=cache_token)


def _sector_strip() -> str:
    quotes = fetch_latest_quotes(SECTOR_ETFS)
    if quotes.empty:
        return '<p class="pt-placeholder">Sector ETF movement unavailable.</p>'
    items = []
    for _, row in quotes.head(len(SECTOR_ETFS)).iterrows():
        move = to_float(row.get("change_pct")) or 0.0
        tone = "good" if move > 0 else "bad" if move < 0 else "neutral"
        items.append(
            f'<span><b>{escape(str(row.get("ticker") or ""))}</b> {escape(fmt_price(row.get("price")))} <em class="{tone}">{escape(fmt_daily_move(move))}</em></span>'
        )
    return f'<div class="pt-sector-live-strip">{"".join(items)}</div>'


@st.fragment(run_every="60s")
def _market_movers_fragment(tickers: tuple[str, ...], title: str) -> None:
    try:
        if tickers:
            packet = _quote_movers(list(tickers))
            source = "Watchlist live quotes"
        else:
            packet = _fetch_market_movers_packet(_minute_cache_token())
            source_status = packet.get("source_status", {}) if isinstance(packet, dict) else {}
            source = str(source_status.get("source") or source_status.get("provider") or "Market movers provider")
        mark_fragment_refresh("market_movers", 60, "OK", source)
        gainers = packet.get("gainers", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
        losers = packet.get("losers", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
        active = packet.get("most_active", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
        markup = f"""
        <div class="pt-shell pt-live-section">
          <div class="pt-live-section-head">
            <div><h2>{escape(title)}</h2><p>Lightweight movers refresh. Fundamentals and AI summaries are excluded.</p></div>
            <span>Every 60s</span>
          </div>
          <div class="pt-live-mover-grid">
            {_compact_table(gainers, "Biggest Gainers")}
            {_compact_table(losers, "Biggest Losers")}
            {_compact_table(active, "Most Active")}
          </div>
          <div class="pt-live-panel pt-sector-panel"><h3>Sector ETF Movement</h3>{_sector_strip()}</div>
        </div>
        """
        render_html(markup)
    except Exception as exc:
        mark_fragment_refresh("market_movers", 60, "Error", str(exc)[:180])
        st.warning(f"Market movers are temporarily unavailable: {exc}")


def render_live_market_movers(tickers: list[str] | None = None, title: str = "Market Movers") -> None:
    cleaned = tuple(clean_ticker(ticker) for ticker in (tickers or []) if clean_ticker(ticker))
    _market_movers_fragment(cleaned, title)
