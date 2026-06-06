from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from data.market_scanner import MarketUniverseProvider, ScannerFilters, UNIVERSE_OPTIONS
from data.market_news import (
    SOURCE_TYPES,
    UPDATE_TYPES,
    NewsItem,
    filter_news_items,
    market_news_provider,
    news_summary,
)
from data.economic_calendar import enrich_economic_calendar_events
from pineterminal.components import (
    html,
    money,
    percent,
    price,
    render_brand,
    render_company_dashboard,
    render_dataframe,
    render_readthrough_table,
    render_topbar,
    section,
    tone_for_value,
    value_row,
)
from pineterminal.calculations import calculate_expected_return, calculate_fundamental_score
from pineterminal.demo_data import (
    ANALYSES,
    COMPANIES,
    ECONOMIC_CALENDAR_EVENTS,
    MARKET_INDICES,
    MARKET_MOVERS,
    MARKET_UPDATES,
    PORTFOLIO_HOLDINGS,
    THEME_EXPOSURES,
    UPCOMING_EVENTS,
    all_watchlist_rows,
    screener_rows,
)
from pineterminal.live_data import load_dashboard_analysis
from pineterminal.styles import apply_theme
from pineterminal.valuation import (
    configured_valuation_tickers,
    get_valuation_spec,
    register_valuation_spec,
)
from storage.db import connect, init_db
from storage.watchlist import add_ticker as store_add_ticker
from storage.watchlist import latest_quote_snapshot, remove_ticker as store_remove_ticker
from utils.formatting import clean_ticker, fmt_compact, fmt_currency, fmt_daily_move, fmt_multiple, now_et, safe_format_datetime, to_float


PAGES = [
    "Dashboard",
    "Markets",
    "Market Read-Through",
    "Scanner",
    "Watchlists",
    "Portfolio",
    "News Feed",
    "Alerts",
    "Economic Data",
    "Calendar",
    "Settings",
]

APP_STATE_VERSION = "pineterminal-dashboard-v3"
DEFAULT_WATCHLIST = ["AMPX", "MRVL", "VICR", "IONQ", "MP", "FBTC", "CEG", "NVDA"]
WATCHLIST_REFRESH_INTERVAL_MS = 300_000
PAGE_REFRESH_INTERVAL_MS = {
    "Scanner": 180_000,
    "News Feed": 300_000,
    "Economic Data": 900_000,
}
SCANNER_PROVIDER = MarketUniverseProvider()
SCANNER_TABLE_COLUMNS = [0.16, 0.1, 0.11, 0.1, 0.1, 0.12, 0.12, 0.17, 0.13, 0.13]


st.set_page_config(page_title="PineTerminal", page_icon="P", layout="wide", initial_sidebar_state="expanded")
apply_theme()


def _mark_pineterminal_watchlist_ticker(ticker: str) -> None:
    symbol = clean_ticker(ticker)
    if not symbol:
        return
    init_db()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at, category, notes) VALUES (?, ?, ?, ?)",
            (symbol, now_et().isoformat(), "PineTerminal", ""),
        )
        conn.execute("UPDATE watchlist SET category = ? WHERE ticker = ?", ("PineTerminal", symbol))
        conn.commit()


def _load_persistent_watchlist_tickers() -> list[str]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist WHERE category = ? ORDER BY id", ("PineTerminal",)).fetchall()
    tickers = [clean_ticker(row["ticker"]) for row in rows if clean_ticker(row["ticker"])]
    if tickers:
        return tickers
    for ticker in DEFAULT_WATCHLIST:
        _mark_pineterminal_watchlist_ticker(ticker)
    return DEFAULT_WATCHLIST.copy()


def _default_portfolio_holdings() -> list[dict[str, object]]:
    return [dict(row) for row in PORTFOLIO_HOLDINGS]


def _init_state() -> None:
    if st.session_state.get("_pt_app_state_version") != APP_STATE_VERSION:
        for key in ("currency", "page"):
            st.session_state.pop(key, None)
        st.session_state["_pt_app_state_version"] = APP_STATE_VERSION
    st.session_state.setdefault("selected_ticker", "AMPX")
    st.session_state.setdefault("currency", "USD")
    st.session_state.setdefault("page", "Dashboard")
    if st.session_state["page"] == "Thesis Tracker":
        st.session_state["page"] = "Portfolio"
    elif st.session_state["page"] == "Screener":
        st.session_state["page"] = "Scanner"
    elif st.session_state["page"] not in PAGES:
        st.session_state["page"] = "Dashboard"
    if "watchlist_tickers" not in st.session_state:
        st.session_state["watchlist_tickers"] = _load_persistent_watchlist_tickers()
    st.session_state.setdefault("watchlist_add_open", False)
    st.session_state.setdefault("watchlist_message", "")
    if "portfolio_holdings" not in st.session_state:
        st.session_state["portfolio_holdings"] = _default_portfolio_holdings()
    st.session_state.setdefault("portfolio_add_open", False)
    st.session_state.setdefault("portfolio_message", "")
    st.session_state.setdefault("valuation_assumption_specs", {})


def _apply_session_valuation_specs() -> None:
    for ticker, spec in st.session_state.get("valuation_assumption_specs", {}).items():
        register_valuation_spec(str(ticker), spec)


def _active_watchlist_tickers() -> list[str]:
    cleaned = []
    for ticker in st.session_state.get("watchlist_tickers", DEFAULT_WATCHLIST):
        symbol = clean_ticker(str(ticker))
        if symbol and symbol not in cleaned:
            cleaned.append(symbol)
    st.session_state["watchlist_tickers"] = cleaned
    return cleaned


def _analysis_watchlist_row(ticker: str) -> dict[str, object]:
    analysis = load_dashboard_analysis(ticker)
    company = analysis.company
    return {
        "Ticker": company.ticker,
        "Company": company.company_name,
        "Price": company.current_price,
        "Daily Change": company.daily_change,
        "Fundamental Score": calculate_fundamental_score(analysis.fundamental_metrics),
        "Expected Return": calculate_expected_return(analysis.expected_value, company.current_price),
        "Net Thesis Impact": analysis.thesis_summary.net_thesis_impact_score,
        "Latest Thesis Impact": analysis.thesis_updates[0].impact if analysis.thesis_updates else "Neutral",
        "Investment Signal": analysis.investment_signal.signal,
        "Risk Level": analysis.investment_signal.risk_level,
        "Theme": company.themes[0] if company.themes else "General",
        "Market Cap": company.market_cap,
        "Revenue Growth": analysis.fundamental_metrics[0].value if analysis.fundamental_metrics else "N/A",
        "Gross Margin": analysis.fundamental_metrics[1].value if len(analysis.fundamental_metrics) > 1 else "N/A",
        "Last Updated": company.last_updated,
        "Source": company.data_source,
    }


def _watchlist_rows() -> list[dict[str, object]]:
    built_in = {str(row["Ticker"]): row for row in all_watchlist_rows()}
    rows = []
    for ticker in _active_watchlist_tickers():
        try:
            rows.append(_analysis_watchlist_row(ticker))
        except Exception:
            snapshot = latest_quote_snapshot(ticker) or {}
            row = built_in.get(ticker) or {}
            rows.append(
                {
                    "Ticker": ticker,
                    "Company": snapshot.get("company") or row.get("Company") or ticker,
                    "Price": snapshot.get("price") or row.get("Price") or 0.0,
                    "Daily Change": snapshot.get("daily_move_pct") or row.get("Daily Change") or 0.0,
                    "Fundamental Score": row.get("Fundamental Score") or 0.0,
                    "Expected Return": row.get("Expected Return") or 0.0,
                    "Net Thesis Impact": row.get("Net Thesis Impact") or 0.0,
                    "Latest Thesis Impact": row.get("Latest Thesis Impact") or "N/A",
                    "Investment Signal": row.get("Investment Signal") or "No Rating",
                    "Risk Level": row.get("Risk Level") or "N/A",
                    "Theme": row.get("Theme") or "Live",
                    "Market Cap": snapshot.get("market_cap") or row.get("Market Cap") or 0.0,
                    "Revenue Growth": row.get("Revenue Growth") or "N/A",
                    "Gross Margin": row.get("Gross Margin") or "N/A",
                    "Last Updated": snapshot.get("timestamp") or row.get("Last Updated") or "N/A",
                    "Source": snapshot.get("source") or row.get("Source") or "Fallback",
                }
            )
    return rows


def _add_watchlist_ticker(symbol: str) -> None:
    ticker = clean_ticker(symbol)
    if not ticker:
        st.session_state["watchlist_message"] = "Enter a ticker first."
        return
    tickers = _active_watchlist_tickers()
    if ticker in tickers:
        st.session_state["selected_ticker"] = ticker
        st.session_state["watchlist_message"] = f"{ticker} is already in your watchlist."
        return
    if not store_add_ticker(ticker, category="PineTerminal"):
        st.session_state["watchlist_message"] = f"Could not add {ticker}. Check the symbol and try again."
        return
    _mark_pineterminal_watchlist_ticker(ticker)
    st.session_state["watchlist_tickers"] = tickers + [ticker]
    st.session_state["selected_ticker"] = ticker
    st.session_state["watchlist_add_open"] = False
    st.session_state["watchlist_message"] = f"Added {ticker}."


def _remove_watchlist_ticker(ticker: str) -> None:
    symbol = clean_ticker(ticker)
    remaining = [item for item in _active_watchlist_tickers() if item != symbol]
    st.session_state["watchlist_tickers"] = remaining
    store_remove_ticker(symbol)
    if st.session_state.get("selected_ticker") == symbol and remaining:
        st.session_state["selected_ticker"] = remaining[0]
    st.session_state["watchlist_message"] = f"Removed {symbol}."


def _portfolio_key(ticker: object) -> str:
    raw = str(ticker or "").strip()
    if raw.casefold() == "cash":
        return "CASH"
    return clean_ticker(raw)


def _portfolio_weight(value: object) -> float:
    try:
        return round(float(value or 0.0), 1)
    except (TypeError, ValueError):
        return 0.0


def _active_portfolio_holdings() -> list[dict[str, object]]:
    holdings = []
    seen = set()
    for row in st.session_state.get("portfolio_holdings", _default_portfolio_holdings()):
        key = _portfolio_key(row.get("ticker") if isinstance(row, dict) else "")
        if not key or key in seen:
            continue
        seen.add(key)
        holdings.append(
            {
                "ticker": "Cash" if key == "CASH" else key,
                "weight": _portfolio_weight(row.get("weight") if isinstance(row, dict) else 0.0),
                "signal": str(row.get("signal") or "No Rating") if isinstance(row, dict) else "No Rating",
                "risk": str(row.get("risk") or "N/A") if isinstance(row, dict) else "N/A",
                "theme": str(row.get("theme") or "General") if isinstance(row, dict) else "General",
            }
        )
    st.session_state["portfolio_holdings"] = holdings
    return holdings


def _portfolio_row_for_ticker(symbol: str, weight: float) -> dict[str, object]:
    ticker = clean_ticker(symbol)
    try:
        analysis = ANALYSES.get(ticker) or load_dashboard_analysis(ticker)
        return {
            "ticker": ticker,
            "weight": _portfolio_weight(weight),
            "signal": analysis.investment_signal.signal,
            "risk": analysis.investment_signal.risk_level,
            "theme": analysis.company.themes[0] if analysis.company.themes else "General",
        }
    except Exception:
        snapshot = latest_quote_snapshot(ticker) or {}
        return {
            "ticker": ticker,
            "weight": _portfolio_weight(weight),
            "signal": "No Rating",
            "risk": "N/A",
            "theme": str(snapshot.get("sector") or "Live"),
        }


def _portfolio_tickers(rows: list[dict[str, object]]) -> list[str]:
    return [key for row in rows if (key := _portfolio_key(row.get("ticker"))) and key != "CASH"]


def _add_portfolio_ticker(symbol: str, weight: float) -> None:
    ticker = clean_ticker(symbol)
    if not ticker:
        st.session_state["portfolio_message"] = "Enter a ticker first."
        return
    if ticker == "CASH":
        st.session_state["portfolio_message"] = "Cash is already tracked as the reserve row."
        return
    holdings = _active_portfolio_holdings()
    if ticker in _portfolio_tickers(holdings):
        st.session_state["selected_ticker"] = ticker
        st.session_state["portfolio_message"] = f"{ticker} is already in the portfolio."
        return
    insert_at = next((index for index, row in enumerate(holdings) if _portfolio_key(row.get("ticker")) == "CASH"), len(holdings))
    holdings.insert(insert_at, _portfolio_row_for_ticker(ticker, weight))
    st.session_state["portfolio_holdings"] = holdings
    st.session_state["selected_ticker"] = ticker
    st.session_state["portfolio_add_open"] = False
    st.session_state["portfolio_message"] = f"Added {ticker} to the portfolio."


def _remove_portfolio_ticker(ticker: str) -> None:
    key = _portfolio_key(ticker)
    if key == "CASH":
        st.session_state["portfolio_message"] = "Cash reserve stays in the portfolio."
        return
    holdings = [row for row in _active_portfolio_holdings() if _portfolio_key(row.get("ticker")) != key]
    st.session_state["portfolio_holdings"] = holdings
    if st.session_state.get("selected_ticker") == key:
        remaining = _portfolio_tickers(holdings)
        if remaining:
            st.session_state["selected_ticker"] = remaining[0]
    st.session_state["portfolio_message"] = f"Removed {key} from the portfolio."


def render_watchlist_sidebar(rows: list[dict[str, object]]) -> None:
    html('<div class="pt-side-title">My Watchlist</div>')
    message = st.session_state.get("watchlist_message", "")
    if message:
        st.caption(message)
    for row in rows:
        ticker = str(row["Ticker"])
        change = float(row.get("Daily Change") or 0.0)
        ticker_col, price_col, change_col, remove_col = st.columns([0.34, 0.28, 0.26, 0.12], gap="small", vertical_alignment="center")
        with ticker_col:
            if st.button(ticker, key=f"watch_select_{ticker}", use_container_width=True):
                st.session_state["selected_ticker"] = ticker
                st.rerun()
        with price_col:
            st.markdown(f'<div class="pt-watch-price">{price(float(row.get("Price") or 0.0))}</div>', unsafe_allow_html=True)
        with change_col:
            st.markdown(f'<div class="pt-watch-change {tone_for_value(change)}">{percent(change, 2)}</div>', unsafe_allow_html=True)
        with remove_col:
            if st.button("X", key=f"watch_remove_{ticker}", help=f"Remove {ticker}", use_container_width=True):
                _remove_watchlist_ticker(ticker)
                st.rerun()
        html('<div class="pt-watch-separator"></div>')
    if st.session_state.get("watchlist_add_open"):
        new_ticker = st.text_input("Add ticker", key="watchlist_new_ticker", placeholder="Ticker", label_visibility="collapsed")
        add_col, cancel_col = st.columns(2)
        with add_col:
            if st.button("Add", key="watch_add_confirm", use_container_width=True):
                _add_watchlist_ticker(new_ticker)
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="watch_add_cancel", use_container_width=True):
                st.session_state["watchlist_add_open"] = False
                st.rerun()
    elif st.button("+ Add Ticker", key="watch_add_open", use_container_width=True):
        st.session_state["watchlist_add_open"] = True
        st.rerun()


def render_sidebar(watchlist_rows: list[dict[str, object]]) -> str:
    with st.sidebar:
        render_brand()
        page = st.radio("Navigation", PAGES, index=PAGES.index(st.session_state.get("page", "Dashboard")), label_visibility="collapsed")
        st.session_state["page"] = page
        render_watchlist_sidebar(watchlist_rows)
    return page


def render_global_controls(page: str, analysis) -> None:
    search_col, topbar_col = st.columns([0.16, 0.84], vertical_alignment="center")
    with search_col:
        search_value = st.text_input("Ticker", value=st.session_state["selected_ticker"], placeholder="Search ticker")
        searched = clean_ticker(search_value)
        if searched and searched != st.session_state["selected_ticker"]:
            st.session_state["selected_ticker"] = searched
            st.rerun()
    with topbar_col:
        render_topbar(page, analysis.company.ticker, st.session_state["currency"], analysis.company.data_mode, analysis.company.last_updated)


def watchlist_tape(rows: list[dict[str, object]]) -> str:
    if not rows:
        return ""
    items = "".join(
        (
            f'<span title="Updated {escape(str(row.get("Last Updated", "N/A")))}">'
            f'<b>{escape(str(row["Ticker"]))}</b> '
            f'{price(float(row.get("Price") or 0.0))} '
            f'<b class="{tone_for_value(float(row.get("Daily Change") or 0.0))}">{percent(float(row.get("Daily Change") or 0.0), 2)}</b>'
            "</span>"
        )
        for row in rows
    )
    return (
        '<div class="pt-watch-tape" aria-label="Watchlist ticker tape">'
        f'<div class="pt-watch-tape-inner">{items}{items}</div>'
        "</div>"
    )


def render_watchlist_tape(rows: list[dict[str, object]]) -> None:
    html(watchlist_tape(rows))


def _auto_refresh_interval_ms(page: str) -> int:
    return PAGE_REFRESH_INTERVAL_MS.get(page, WATCHLIST_REFRESH_INTERVAL_MS)


def _refresh_bucket(interval_ms: int) -> int:
    seconds = max(1, int(interval_ms / 1000))
    return int(now_et().timestamp() // seconds)


def _format_refresh_interval(interval_ms: int) -> str:
    minutes = max(1, round(interval_ms / 60_000))
    return f"{minutes} min"


def render_auto_refresh_timer(page: str) -> None:
    interval_ms = _auto_refresh_interval_ms(page)
    components.html(
        f"""
        <script>
          window.setTimeout(() => window.parent.location.reload(), {interval_ms});
        </script>
        """,
        height=0,
        width=0,
    )


def render_auto_refresh_status(page: str) -> None:
    if page not in PAGE_REFRESH_INTERVAL_MS:
        return
    interval_ms = _auto_refresh_interval_ms(page)
    checked = now_et().strftime("%I:%M %p ET").lstrip("0")
    html(
        f"""
        <div class="pt-auto-refresh">
          <b>Auto-refresh</b>
          <span>Every {escape(_format_refresh_interval(interval_ms))}</span>
          <span>Last checked {escape(checked)}</span>
        </div>
        """
    )


def render_home_page() -> None:
    index_cards = "".join(
        f'<div class="pt-row-card"><span class="pt-mini-label">{row["name"]}</span><strong>{row["price"]}</strong><em class="{tone_for_value(float(row["change"]))}">{percent(float(row["change"]), 2)}</em></div>'
        for row in MARKET_INDICES
    )
    gainers = [row for row in MARKET_MOVERS if float(row["change"]) > 0]
    losers = [row for row in MARKET_MOVERS if float(row["change"]) < 0]
    mover_rows = []
    for idx, row in enumerate(gainers[:10], start=1):
        mover_rows.append({"Rank": idx, "Ticker": row["ticker"], "Company": row["company"], "Price": price(float(row["price"])), "Change": percent(float(row["change"]), 2)})
    loser_rows = []
    for idx, row in enumerate(losers[:10], start=1):
        loser_rows.append({"Rank": idx, "Ticker": row["ticker"], "Company": row["company"], "Price": price(float(row["price"])), "Change": percent(float(row["change"]), 2)})
    highlights = []
    for update in MARKET_UPDATES[:4]:
        highlights.append(
            {
                "Date": update["date"],
                "Theme": update["theme"],
                "Market Update": update["market_update"],
                "Impact": update["impact"],
                "Affected Valuation Lever": update["affected_valuation_lever"],
            }
        )
    html(
        '<div class="pt-shell">'
        + section("Market Index Strip", "", f'<div class="pt-score-breakdown">{index_cards}</div>')
        + "</div>"
    )
    col1, col2 = st.columns(2)
    with col1:
        html(section("Biggest Gainers", "", ""))
        render_dataframe(mover_rows, 260)
    with col2:
        html(section("Biggest Losers", "", ""))
        render_dataframe(loser_rows, 260)
    html(f'<div class="pt-home-grid">{section("Market Read-Through Highlights", "", render_plain_table(highlights))}{section("Upcoming Events", "", render_plain_table(UPCOMING_EVENTS))}</div>')
    render_dataframe(all_watchlist_rows(), 270)


def render_plain_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return '<p class="pt-placeholder">No rows available.</p>'
    columns = list(rows[0].keys())
    header = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>"
    return f'<table class="pt-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def render_market_readthrough_page() -> None:
    all_items = [item for analysis in ANALYSES.values() for item in analysis.market_read_through]
    themes = ["All"] + sorted({item.theme for item in all_items})
    impacts = ["All", "Positive", "Negative", "High confidence only"]
    filter_cols = st.columns(4)
    with filter_cols[0]:
        theme = st.selectbox("Theme filter", themes)
    with filter_cols[1]:
        ticker = st.selectbox("Impacted ticker", ["All"] + sorted({ticker for item in all_items for ticker in item.impacted_tickers}))
    with filter_cols[2]:
        impact = st.selectbox("Impact filter", impacts)
    with filter_cols[3]:
        search = st.text_input("Search", placeholder="drone, capex, treasury")

    filtered = []
    for item in all_items:
        if theme != "All" and item.theme != theme:
            continue
        if ticker != "All" and ticker not in item.impacted_tickers:
            continue
        if impact == "Positive" and item.impact_score <= 0:
            continue
        if impact == "Negative" and item.impact_score >= 0:
            continue
        if impact == "High confidence only" and item.confidence != "High":
            continue
        if search and search.casefold() not in (item.market_update + item.theme + item.why_it_matters).casefold():
            continue
        filtered.append(item)

    html(section("Market Read-Through", "Indirect Catalyst Radar", render_readthrough_table(filtered)))
    exposure_rows = [asdict(item) for item in THEME_EXPOSURES]
    render_dataframe(exposure_rows, 300)


def _scanner_state_defaults() -> None:
    defaults = {
        "scanner_universe": "All U.S. Stocks",
        "scanner_session": "Regular Market",
        "scanner_min_price": 2.0,
        "scanner_min_market_cap_m": 100.0,
        "scanner_min_dollar_volume_m": 10.0,
        "scanner_min_move_pct": 3.0,
        "scanner_min_relative_volume": 2.0,
        "scanner_min_unusual_pct": 100.0,
        "scanner_direction": "Both",
        "scanner_theme": "All",
        "scanner_include_etfs": False,
        "scanner_exclude_low_liquidity": True,
        "scanner_custom_tickers": "",
        "scanner_refresh_token": 0,
        "scanner_enable_fundamentals": False,
        "scanner_min_fundamental_score": 0.0,
        "scanner_min_expected_return": -250,
        "scanner_fundamental_signal": "All",
        "scanner_fundamental_risk": "All",
        "scanner_keep_unscored": True,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _reset_scanner_filters() -> None:
    for key in (
        "scanner_universe",
        "scanner_session",
        "scanner_min_price",
        "scanner_min_market_cap_m",
        "scanner_min_dollar_volume_m",
        "scanner_min_move_pct",
        "scanner_min_relative_volume",
        "scanner_min_unusual_pct",
        "scanner_direction",
        "scanner_theme",
        "scanner_include_etfs",
        "scanner_exclude_low_liquidity",
        "scanner_custom_tickers",
    ):
        st.session_state.pop(key, None)
    _scanner_state_defaults()


def _scanner_filters_from_state() -> ScannerFilters:
    custom_values = tuple(
        clean_ticker(part)
        for part in str(st.session_state.get("scanner_custom_tickers", "")).replace("\n", ",").replace(" ", ",").split(",")
        if clean_ticker(part)
    )
    manual_refresh_token = int(st.session_state.get("scanner_refresh_token", 0) or 0)
    timed_refresh_token = _refresh_bucket(_auto_refresh_interval_ms("Scanner"))
    return ScannerFilters(
        universe_type=UNIVERSE_OPTIONS.get(st.session_state.get("scanner_universe", "All U.S. Stocks"), "all_us_stocks"),
        session=str(st.session_state.get("scanner_session", "Regular Market")),
        min_price=float(st.session_state.get("scanner_min_price", 2.0) or 0),
        min_market_cap=float(st.session_state.get("scanner_min_market_cap_m", 100.0) or 0) * 1_000_000,
        min_dollar_volume=float(st.session_state.get("scanner_min_dollar_volume_m", 10.0) or 0) * 1_000_000,
        min_move_pct=float(st.session_state.get("scanner_min_move_pct", 3.0) or 0),
        min_relative_volume=float(st.session_state.get("scanner_min_relative_volume", 2.0) or 0),
        min_unusual_volume_pct=float(st.session_state.get("scanner_min_unusual_pct", 100.0) or 0),
        direction=str(st.session_state.get("scanner_direction", "Both")),
        theme=str(st.session_state.get("scanner_theme", "All")),
        include_etfs=bool(st.session_state.get("scanner_include_etfs", False)),
        exclude_low_liquidity=bool(st.session_state.get("scanner_exclude_low_liquidity", True)),
        custom_tickers=custom_values,
        refresh_token=(manual_refresh_token * 1_000_000) + timed_refresh_token,
    )


def _scanner_signal_tone(signal: str) -> str:
    value = signal.casefold()
    if "breakout" in value or "surge" in value:
        return "good"
    if "selloff" in value or "breakdown" in value or "capitulation" in value:
        return "bad"
    if "anomaly" in value or "elevated" in value:
        return "warn"
    return "neutral"


def _scanner_volume_tone(label: str) -> str:
    value = label.casefold()
    if "extreme" in value or "very" in value:
        return "warn"
    if "unusual" in value or "elevated" in value:
        return "info"
    if "normal" in value:
        return "neutral"
    return "neutral"


def _scanner_status_tone(mode: str) -> str:
    value = mode.casefold()
    if "live" in value:
        return "good"
    if "partial" in value:
        return "warn"
    if "fallback" in value or "demo" in value:
        return "bad"
    return "neutral"


def _open_scanner_ticker(row: pd.Series) -> None:
    ticker = clean_ticker(str(row.get("ticker") or ""))
    if not ticker:
        return
    if ticker in ANALYSES or ticker in COMPANIES:
        st.session_state["selected_ticker"] = ticker
        st.session_state["page"] = "Dashboard"
        st.rerun()
    st.session_state["scanner_detail_ticker"] = ticker
    st.session_state["scanner_detail_row"] = {column: row.get(column) for column in row.index}


def _scanner_summary_cards(summary: dict) -> str:
    cards = [
        ("High-Volume Gainers", summary.get("highVolumeGainers", 0), "vs filters", "+"),
        ("High-Volume Losers", summary.get("highVolumeLosers", 0), "vs filters", "-"),
        ("Unusual Volume Leaders", summary.get("unusualVolumeLeaders", 0), "ranked by rel vol", "!"),
        ("Watchlist Alerts", summary.get("watchlistAlerts", 0), "secondary only", "!"),
        ("Market Breadth", f'{summary.get("marketBreadth", 0):.0f}%', "advancers", "+"),
    ]
    body = ""
    for title, value, label, icon in cards:
        tone = "bad" if "Losers" in title else "warn" if "Unusual" in title or "Alerts" in title else "good"
        body += f"""
        <div class="pt-scanner-card">
          <div class="pt-scanner-card-icon {tone}">{escape(icon)}</div>
          <span>{escape(title)}</span>
          <strong>{escape(str(value))}</strong>
          <small>{escape(label)}</small>
        </div>
        """
    return f'<div class="pt-scanner-summary">{body}</div>'


def _scanner_header(status: dict) -> None:
    mode = str(status.get("data_mode") or "Partial")
    last_updated = safe_format_datetime(status.get("last_updated"))
    source = str(status.get("source") or status.get("provider") or "Market data feed")
    left, right = st.columns([0.58, 0.42], vertical_alignment="center")
    with left:
        html(
            f"""
            <div class="pt-scanner-titlebar">
              <div>
                <h1>Market Scanner</h1>
                <p>High-volume movers, unusual activity, and directional market signals.</p>
              </div>
            </div>
            """
        )
    with right:
        meta_col, refresh_col = st.columns([0.72, 0.28], vertical_alignment="center")
        with meta_col:
            html(
                f"""
                <div class="pt-scanner-meta">
                  <span>Last updated <b>{escape(last_updated)}</b></span>
                  <span>Session <b>{escape(str(st.session_state.get("scanner_session", "Regular Market")))}</b></span>
                  <span>Data <b class="{_scanner_status_tone(mode)}" title="{escape(source)}">{escape(mode)}</b></span>
                </div>
                """
            )
        with refresh_col:
            if st.button("Refresh", key="scanner_refresh", use_container_width=True):
                st.session_state["scanner_refresh_token"] = int(st.session_state.get("scanner_refresh_token", 0) or 0) + 1
                st.rerun()


def _render_scanner_filters(theme_options: list[str]) -> None:
    filter_cols = st.columns([0.16, 0.15, 0.13, 0.13, 0.13, 0.13, 0.12, 0.13], vertical_alignment="bottom")
    with filter_cols[0]:
        st.selectbox("Market Universe", list(UNIVERSE_OPTIONS.keys()), key="scanner_universe")
    with filter_cols[1]:
        st.selectbox("Session", ["Regular Market", "Pre-Market", "After Hours", "Full Session"], key="scanner_session")
    with filter_cols[2]:
        st.number_input("Min Price", min_value=0.0, max_value=250.0, step=0.5, key="scanner_min_price")
    with filter_cols[3]:
        st.number_input("Min Mkt Cap ($M)", min_value=0.0, max_value=1_000_000.0, step=50.0, key="scanner_min_market_cap_m")
    with filter_cols[4]:
        st.number_input("Min $ Vol ($M)", min_value=0.0, max_value=100_000.0, step=5.0, key="scanner_min_dollar_volume_m")
    with filter_cols[5]:
        st.number_input("Min % Move", min_value=0.0, max_value=50.0, step=0.5, key="scanner_min_move_pct")
    with filter_cols[6]:
        st.number_input("Min Rel Vol", min_value=0.0, max_value=50.0, step=0.5, key="scanner_min_relative_volume")
    with filter_cols[7]:
        st.selectbox("Direction", ["Both", "Gainers", "Losers"], key="scanner_direction")

    extra_cols = st.columns([0.2, 0.2, 0.16, 0.16, 0.18], vertical_alignment="bottom")
    with extra_cols[0]:
        st.number_input("Min Unusual Vol %", min_value=0.0, max_value=2_000.0, step=25.0, key="scanner_min_unusual_pct")
    with extra_cols[1]:
        current_theme = st.session_state.get("scanner_theme", "All")
        if current_theme not in theme_options:
            st.session_state["scanner_theme"] = "All"
        st.selectbox("Theme", theme_options, key="scanner_theme")
    with extra_cols[2]:
        st.checkbox("Include ETFs", key="scanner_include_etfs")
    with extra_cols[3]:
        st.checkbox("Exclude low liquidity", key="scanner_exclude_low_liquidity")
    with extra_cols[4]:
        if st.button("Reset Filters", key="scanner_reset", use_container_width=True):
            _reset_scanner_filters()
            st.rerun()

    if st.session_state.get("scanner_universe") == "Custom Universe":
        st.text_input("Custom tickers", placeholder="AAPL, MSFT, NVDA", key="scanner_custom_tickers")


def _scanner_detail_markup(row: dict) -> str:
    ticker = clean_ticker(str(row.get("ticker") or ""))
    return section(
        f"{ticker} Scanner Detail",
        "Ticker is not yet modeled in Company Analysis",
        f"""
        <div class="pt-scanner-detail-grid">
          {value_row("Company", str(row.get("companyName") or ticker))}
          {value_row("Price", price(to_float(row.get("currentPrice"))))}
          {value_row("Move", fmt_daily_move(row.get("priceChangePercent")), tone_for_value(to_float(row.get("priceChangePercent")) or 0))}
          {value_row("Relative Volume", fmt_multiple(row.get("relativeVolume")))}
          {value_row("Unusual Volume", fmt_daily_move(row.get("unusualVolumePercent")), "warn")}
          {value_row("Dollar Volume", fmt_currency(row.get("dollarVolume"), 1))}
          {value_row("Signal", str(row.get("signal") or "Normal move"), _scanner_signal_tone(str(row.get("signal") or "")))}
          {value_row("Source", str(row.get("source") or "Market data feed"))}
        </div>
        """,
    )


def _render_scanner_detail() -> None:
    row = st.session_state.get("scanner_detail_row")
    if row:
        html(_scanner_detail_markup(row))


def _scanner_row_columns(row: pd.Series, prefix: str, idx: int) -> None:
    cols = st.columns(SCANNER_TABLE_COLUMNS, vertical_alignment="center")
    ticker = clean_ticker(str(row.get("ticker") or ""))
    with cols[0]:
        if st.button(ticker, key=f"{prefix}_ticker_{ticker}_{idx}", help=f"Open {ticker}", use_container_width=True):
            _open_scanner_ticker(row)
    with cols[1]:
        st.markdown(f'<span class="pt-scanner-cell">{price(to_float(row.get("currentPrice")))}</span>', unsafe_allow_html=True)
    with cols[2]:
        move = to_float(row.get("priceChangePercent")) or 0.0
        st.markdown(f'<span class="pt-scanner-cell {tone_for_value(move)}">{fmt_daily_move(move)}</span>', unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f'<span class="pt-scanner-cell">{fmt_compact(row.get("currentVolume"), 1)}</span>', unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f'<span class="pt-scanner-cell">{fmt_multiple(row.get("relativeVolume"))}</span>', unsafe_allow_html=True)
    with cols[5]:
        st.markdown(f'<span class="pt-scanner-cell">{fmt_daily_move(row.get("unusualVolumePercent"))}</span>', unsafe_allow_html=True)
    with cols[6]:
        st.markdown(f'<span class="pt-scanner-cell">{fmt_currency(row.get("dollarVolume"), 1)}</span>', unsafe_allow_html=True)
    with cols[7]:
        st.markdown(f'<span class="pt-scanner-cell">{escape(str(row.get("theme") or "General"))}</span>', unsafe_allow_html=True)
    with cols[8]:
        anomaly = str(row.get("volumeAnomaly") or "Unknown")
        st.markdown(f'<span class="pt-scanner-chip {_scanner_volume_tone(anomaly)}">{escape(anomaly)}</span>', unsafe_allow_html=True)
    with cols[9]:
        signal = str(row.get("signal") or "Normal move")
        st.markdown(f'<span class="pt-scanner-chip {_scanner_signal_tone(signal)}">{escape(signal)}</span>', unsafe_allow_html=True)


def _render_scanner_table(title: str, subtitle: str, frame: pd.DataFrame, prefix: str, limit: int = 8, action: str = "") -> None:
    html(section(title, subtitle, "", action))
    if frame is None or frame.empty:
        html('<p class="pt-placeholder">No tickers match the current scanner filters.</p>')
        return
    header = st.columns(SCANNER_TABLE_COLUMNS)
    labels = ["Ticker", "Price", "% Change", "Volume", "Rel Vol", "Unusual", "$ Vol", "Theme", "Volume", "Signal"]
    for col, label in zip(header, labels):
        with col:
            st.markdown(f'<div class="pt-scanner-header-cell">{escape(label)}</div>', unsafe_allow_html=True)
    for idx, (_, row) in enumerate(frame.head(limit).iterrows()):
        _scanner_row_columns(row, prefix, idx)


def _apply_scanner_fundamental_filters(packet: dict) -> dict:
    if not st.session_state.get("scanner_enable_fundamentals"):
        return packet
    frame = packet.get("all_results", pd.DataFrame())
    if frame is None or frame.empty:
        return packet
    lookup = {clean_ticker(str(row["Ticker"])): row for row in screener_rows()}
    min_score = float(st.session_state.get("scanner_min_fundamental_score", 0.0) or 0.0)
    min_return = float(st.session_state.get("scanner_min_expected_return", -250) or -250)
    signal = str(st.session_state.get("scanner_fundamental_signal", "All"))
    risk = str(st.session_state.get("scanner_fundamental_risk", "All"))
    keep_unscored = bool(st.session_state.get("scanner_keep_unscored", True))

    keep_indexes = []
    for idx, row in frame.iterrows():
        fundamentals = lookup.get(clean_ticker(str(row.get("ticker") or "")))
        if not fundamentals:
            if keep_unscored:
                keep_indexes.append(idx)
            continue
        if float(fundamentals.get("Fundamental Score") or 0) < min_score:
            continue
        if float(fundamentals.get("Expected Return") or 0) < min_return:
            continue
        if signal != "All" and fundamentals.get("Investment Signal") != signal:
            continue
        if risk != "All" and fundamentals.get("Risk Level") != risk:
            continue
        keep_indexes.append(idx)
    filtered = frame.loc[keep_indexes].reset_index(drop=True)
    packet = dict(packet)
    packet["all_results"] = filtered
    packet["gainers"] = filtered[filtered["priceChangePercent"] > 0].sort_values(["priceChangePercent", "relativeVolume"], ascending=[False, False], na_position="last").reset_index(drop=True)
    packet["losers"] = filtered[filtered["priceChangePercent"] < 0].sort_values(["priceChangePercent", "relativeVolume"], ascending=[True, False], na_position="last").reset_index(drop=True)
    packet["unusual_volume"] = filtered.sort_values(["relativeVolume", "unusualVolumePercent"], ascending=[False, False], na_position="last").reset_index(drop=True)
    packet["watchlist_alerts"] = filtered[filtered["isWatchlistTicker"]].reset_index(drop=True)
    packet["summary"] = SCANNER_PROVIDER._summary(packet["all_results"], packet["gainers"], packet["losers"], packet["unusual_volume"], packet["watchlist_alerts"])
    packet["status"] = {**packet.get("status", {}), "rows": len(filtered), "fundamental_filters": "Enabled"}
    return packet


def _render_scanner_advanced_filters() -> None:
    rows = screener_rows()
    signals = ["All"] + sorted({str(row["Investment Signal"]) for row in rows})
    risks = ["All"] + sorted({str(row["Risk Level"]) for row in rows})
    with st.expander("Advanced Filters", expanded=False):
        st.checkbox("Enable fundamental filters", key="scanner_enable_fundamentals")
        cols = st.columns(5)
        with cols[0]:
            st.slider("Fundamental Score", 0.0, 10.0, key="scanner_min_fundamental_score")
        with cols[1]:
            st.slider("Expected Return", -250, 250, key="scanner_min_expected_return")
        with cols[2]:
            st.selectbox("Investment Signal", signals, key="scanner_fundamental_signal")
        with cols[3]:
            st.selectbox("Risk Level", risks, key="scanner_fundamental_risk")
        with cols[4]:
            st.checkbox("Keep unscored tickers", key="scanner_keep_unscored")
        st.caption("Fundamental filters only apply to tickers with PineTerminal model coverage unless you keep unscored tickers.")


def render_scanner_page() -> None:
    _scanner_state_defaults()
    filters = _scanner_filters_from_state()
    with st.spinner("Scanning market universe..."):
        packet = SCANNER_PROVIDER.scanMarket(filters, watchlist_tickers=_active_watchlist_tickers())
    packet = _apply_scanner_fundamental_filters(packet)
    status = packet.get("status", {})
    _scanner_header(status)
    html(_scanner_summary_cards(packet.get("summary", {})))

    current_themes = sorted(
        {
            str(value)
            for value in packet.get("all_results", pd.DataFrame()).get("theme", pd.Series(dtype=str)).dropna().unique()
            if str(value).strip() and str(value).strip() != "N/A"
        }
    )
    model_themes = sorted({str(row.get("Theme") or "General") for row in screener_rows() if row.get("Theme")})
    theme_options = ["All"] + sorted(set(current_themes + model_themes))
    _render_scanner_filters(theme_options)

    source_message = str(status.get("message") or "")
    source = str(status.get("source") or status.get("provider") or "Market data feed")
    html(
        f"""
        <div class="pt-scanner-source">
          <b>{escape(status.get("universe_label", "All U.S. Stocks"))}</b>
          <span>{escape(source_message or "Current-session leaders from the selected scanner universe.")}</span>
          <span title="{escape(source)}">Data Sources</span>
        </div>
        """
    )
    _render_scanner_detail()

    col1, col2 = st.columns(2)
    with col1:
        _render_scanner_table("Biggest Gainers on Unusual Volume", "Sorted by move, then relative volume", packet.get("gainers", pd.DataFrame()), "scanner_gainers", limit=6)
    with col2:
        _render_scanner_table("Biggest Losers on Unusual Volume", "Sorted by downside move, then relative volume", packet.get("losers", pd.DataFrame()), "scanner_losers", limit=6)

    col3, col4 = st.columns([0.62, 0.38])
    with col3:
        _render_scanner_table("Unusual Volume Leaders", "Market-wide anomaly ranking", packet.get("unusual_volume", pd.DataFrame()), "scanner_unusual", limit=10, action="View full leaderboard")
    with col4:
        _render_scanner_table("Watchlist Alerts", "Secondary alerts from your saved tickers", packet.get("watchlist_alerts", pd.DataFrame()), "scanner_watchlist", limit=6, action="View all alerts")

    _render_scanner_advanced_filters()


def render_watchlist_page() -> None:
    rows = _watchlist_rows()
    group_by = st.segmented_control("Group by", ["Theme", "Investment Signal", "Risk Level", "Market Cap"], default="Theme")
    render_dataframe(rows, 440)
    grouped: dict[str, list[str]] = {}
    for row in rows:
        key = str(row.get(group_by if group_by != "Market Cap" else "Theme", "Other"))
        grouped.setdefault(key, []).append(str(row["Ticker"]))
    cards = "".join(f'<div class="pt-row-card"><span class="pt-mini-label">{key}</span><strong>{", ".join(values)}</strong></div>' for key, values in grouped.items())
    html(section("Watchlist Groups", "", f'<div class="pt-score-breakdown">{cards}</div>'))


def _thesis_tracker_rows(tickers: list[str] | None = None) -> list[dict[str, object]]:
    rows = []
    source_tickers = list(ANALYSES.keys()) if tickers is None else tickers
    for ticker in source_tickers:
        symbol = clean_ticker(ticker)
        if not symbol:
            continue
        try:
            analysis = ANALYSES.get(symbol) or load_dashboard_analysis(symbol)
        except Exception:
            rows.append(
                {
                    "Ticker": symbol,
                    "Original Thesis": f"{symbol} needs more source data before the thesis can be scored.",
                    "Current Thesis Status": "Needs Data",
                    "Bull Case Drivers": "Pending",
                    "Bear Case Risks": "Pending",
                    "Recent Updates": "No updates available",
                    "Thesis Trend": "Unscored",
                    "Conviction Change": "+0.0",
                }
            )
            continue
        rows.append(
            {
                "Ticker": symbol,
                "Original Thesis": _original_thesis(symbol, analysis.company.themes),
                "Current Thesis Status": analysis.thesis_summary.status,
                "Bull Case Drivers": ", ".join(analysis.company.themes[:2]),
                "Bear Case Risks": analysis.risks[0].risk_name if analysis.risks else "Pending",
                "Recent Updates": analysis.thesis_updates[0].title if analysis.thesis_updates else "No updates available",
                "Thesis Trend": analysis.thesis_summary.status,
                "Conviction Change": f"{analysis.thesis_summary.net_thesis_impact_score:+.1f}",
            }
        )
    return rows


def _original_thesis(ticker: str, themes: list[str] | None = None) -> str:
    if ticker == "AMPX":
        return "High-density batteries can benefit from drone, aviation, and EV applications where weight and endurance matter."
    company = COMPANIES.get(ticker)
    selected_themes = themes or (company.themes if company else [])
    theme_text = ", ".join(selected_themes[:2]) if selected_themes else "its core end-market"
    return f"{ticker} benefits if {theme_text} demand continues strengthening."


def _portfolio_signal_tone(signal: str) -> str:
    lowered = signal.casefold()
    if "buy" in lowered:
        return "good"
    if "avoid" in lowered or "sell" in lowered:
        return "bad"
    if "hold" in lowered or "reserve" in lowered:
        return "warn"
    return "neutral"


def _portfolio_risk_tone(risk: str) -> str:
    lowered = risk.casefold()
    if lowered == "high":
        return "bad"
    if lowered == "medium":
        return "warn"
    if lowered == "low":
        return "good"
    return "neutral"


def render_portfolio_controls() -> None:
    message = st.session_state.get("portfolio_message", "")
    if message:
        st.caption(message)
    if st.session_state.get("portfolio_add_open"):
        ticker_col, weight_col = st.columns([0.72, 0.28], vertical_alignment="center")
        with ticker_col:
            new_ticker = st.text_input("Add ticker to portfolio", key="portfolio_new_ticker", placeholder="Ticker")
        with weight_col:
            new_weight = st.number_input("Starting weight (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="portfolio_new_weight")
        add_col, cancel_col = st.columns(2)
        with add_col:
            if st.button("Add to Portfolio", key="portfolio_add_confirm", use_container_width=True):
                _add_portfolio_ticker(new_ticker, new_weight)
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="portfolio_add_cancel", use_container_width=True):
                st.session_state["portfolio_add_open"] = False
                st.rerun()
    elif st.button("+ Add Ticker", key="portfolio_add_open_button"):
        st.session_state["portfolio_add_open"] = True
        st.rerun()


def render_portfolio_holdings(rows: list[dict[str, object]]) -> None:
    html('<div class="pt-side-title">Portfolio Holdings</div>')
    headers = ["Ticker", "Weight", "Signal", "Risk", "Theme", ""]
    widths = [0.16, 0.12, 0.24, 0.14, 0.28, 0.06]
    header_cols = st.columns(widths, gap="small")
    for col, label in zip(header_cols, headers):
        with col:
            st.markdown(f'<div class="pt-mini-label">{escape(label)}</div>', unsafe_allow_html=True)
    for row in rows:
        ticker = str(row.get("ticker", ""))
        key = _portfolio_key(ticker)
        is_cash = key == "CASH"
        row_cols = st.columns(widths, gap="small", vertical_alignment="center")
        with row_cols[0]:
            if is_cash:
                st.markdown(f"**{escape(ticker)}**", unsafe_allow_html=True)
            elif st.button(ticker, key=f"portfolio_select_{key}", use_container_width=True):
                st.session_state["selected_ticker"] = key
                st.rerun()
        with row_cols[1]:
            st.markdown(f'{_portfolio_weight(row.get("weight")):.1f}%')
        with row_cols[2]:
            signal = str(row.get("signal", "No Rating"))
            st.markdown(f'<span class="{_portfolio_signal_tone(signal)}">{escape(signal)}</span>', unsafe_allow_html=True)
        with row_cols[3]:
            risk = str(row.get("risk", "N/A"))
            st.markdown(f'<span class="{_portfolio_risk_tone(risk)}">{escape(risk)}</span>', unsafe_allow_html=True)
        with row_cols[4]:
            st.markdown(escape(str(row.get("theme", "General"))), unsafe_allow_html=True)
        with row_cols[5]:
            if not is_cash and st.button("X", key=f"portfolio_remove_{key}", help=f"Remove {key}", use_container_width=True):
                _remove_portfolio_ticker(key)
                st.rerun()


def render_portfolio_page() -> None:
    portfolio_rows = _active_portfolio_holdings()
    portfolio_tickers = _portfolio_tickers(portfolio_rows)
    total_risk = sum(_portfolio_weight(row.get("weight")) for row in portfolio_rows if str(row.get("risk")) == "High")
    cash_reserve = next((_portfolio_weight(row.get("weight")) for row in portfolio_rows if _portfolio_key(row.get("ticker")) == "CASH"), 0.0)
    theme_count = len({str(row.get("theme")) for row in portfolio_rows if _portfolio_key(row.get("ticker")) != "CASH"})
    cards = f"""
    <div class="pt-score-breakdown">
      <div class="pt-row-card"><span class="pt-mini-label">High-Risk Exposure</span><strong class="warn">{total_risk:.1f}%</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Theme Count</span><strong>{theme_count}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Cash Reserve</span><strong>{cash_reserve:.1f}%</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Read-Through Coverage</span><strong class="good">Active</strong></div>
    </div>
    """
    html(section("Portfolio", "Holdings, thesis, theme and risk monitor", cards))
    render_portfolio_controls()
    render_portfolio_holdings(portfolio_rows)
    html(section("Thesis / Theme Tracker", "Thesis status, drivers, risks, and recent updates", ""))
    render_dataframe(_thesis_tracker_rows(portfolio_tickers), 420)


def _news_state_defaults() -> None:
    defaults = {
        "news_feed_mode": "Market-Wide",
        "news_view_mode": "Table View",
        "news_search": "",
        "news_ticker_input": "",
        "news_ticker_filters": [],
        "news_sector": "All",
        "news_theme": "All",
        "news_impact": "All",
        "news_update_type": "All",
        "news_directness": "All",
        "news_date_filter": "Last 7 Days",
        "news_source_type": "All Sources",
        "news_custom_start": now_et().date(),
        "news_custom_end": now_et().date(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _reset_news_filters() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("news_"):
            st.session_state.pop(key, None)
    _news_state_defaults()


def _news_tone(value: str) -> str:
    lowered = str(value or "").casefold()
    if "positive" in lowered or "high" == lowered or "+" in lowered:
        return "good"
    if "negative" in lowered or "risk" in lowered or "-" in lowered:
        return "bad"
    if "mixed" in lowered or "medium" == lowered or "macro" in lowered or "sector" in lowered:
        return "warn"
    if "direct" in lowered or "theme" in lowered or "indirect" in lowered:
        return "info"
    return "neutral"


def _news_badge(label: str, tone: str | None = None) -> str:
    return f'<span class="pt-news-badge {escape(tone or _news_tone(label))}">{escape(str(label))}</span>'


def _news_primary_label(item: NewsItem) -> tuple[str, str]:
    if item.tickers:
        primary = item.tickers[0]
        extra = len(set(item.tickers + item.readThroughTickers)) - 1
        return primary, f"+{extra}" if extra > 0 else ""
    if item.themes:
        return item.themes[0], f"+{len(item.themes) - 1}" if len(item.themes) > 1 else ""
    return "Market", ""


def _news_source_link(item: NewsItem) -> str:
    label = escape(item.source)
    if item.url:
        return f'<a href="{escape(item.url)}" target="_blank" rel="noopener noreferrer">{label}</a>'
    return label


def _open_news_ticker(ticker: str, item: NewsItem) -> None:
    symbol = clean_ticker(ticker)
    if not symbol:
        return
    if symbol in ANALYSES or symbol in COMPANIES:
        st.session_state["selected_ticker"] = symbol
        st.session_state["page"] = "Dashboard"
        st.rerun()
    st.session_state["news_detail_ticker"] = symbol
    st.session_state["news_detail_item"] = item.id


def _render_news_ticker_actions(item: NewsItem, key_prefix: str) -> None:
    tickers = []
    for ticker in [*item.tickers, *item.readThroughTickers]:
        symbol = clean_ticker(ticker)
        if symbol and symbol not in tickers:
            tickers.append(symbol)
    if not tickers:
        st.caption("No direct ticker. This is a theme or macro read-through.")
        return
    cols = st.columns(min(6, len(tickers)))
    for idx, ticker in enumerate(tickers[:6]):
        with cols[idx % len(cols)]:
            if st.button(ticker, key=f"{key_prefix}_{item.id}_{ticker}", help=f"Open {ticker}", use_container_width=True):
                _open_news_ticker(ticker, item)


def _news_summary_markup(summary: dict[str, int]) -> str:
    cards = [
        ("Market Updates", summary.get("market_updates", 0), "Macro, policy, commodity, sector", "info"),
        ("Direct Company News", summary.get("company_news", 0), "Earnings, guidance, corporate actions", "good"),
        ("Indirect Read-Throughs", summary.get("indirect_readthroughs", 0), "Supply chain, policy, sector impacts", "warn"),
        ("Watchlist Impacts", summary.get("watchlist_impacts", 0), "Items affecting your watchlist", "warn"),
    ]
    body = ""
    for label, value, subtitle, tone in cards:
        body += f"""
        <div class="pt-news-summary-card">
          <span>{escape(label)}</span>
          <strong class="{tone}">{value}</strong>
          <small>{escape(subtitle)}</small>
        </div>
        """
    return f'<div class="pt-news-summary">{body}</div>'


def _render_news_header(status_label: str) -> None:
    left, right = st.columns([0.58, 0.42], vertical_alignment="center")
    with left:
        html(
            """
            <div class="pt-news-title">
              <small>Dashboard / Research / News Feed</small>
              <h1>News Feed</h1>
              <p>Market-wide updates, company news, and thesis-impact read-throughs.</p>
            </div>
            """
        )
    with right:
        controls = st.columns([0.42, 0.28, 0.3], vertical_alignment="center")
        with controls[0]:
            st.segmented_control("Feed mode", ["Market-Wide", "Watchlist", "Ticker"], key="news_feed_mode", label_visibility="collapsed")
        with controls[1]:
            st.segmented_control("View", ["Table View", "Card View"], key="news_view_mode", label_visibility="collapsed")
        with controls[2]:
            html(f'<div class="pt-news-data-mode">Data Mode <b>{escape(status_label)}</b><span>Demo feed, classified locally</span></div>')


def _render_news_filters(items: list[NewsItem]) -> None:
    all_related_tickers = sorted(
        {
            ticker
            for item in items
            for ticker in [*item.tickers, *item.readThroughTickers]
            if clean_ticker(ticker)
        }
    )
    sectors = ["All"] + sorted({sector for item in items for sector in item.sectors if sector})
    themes = ["All"] + sorted({theme for item in items for theme in [*item.themes, *item.readThroughThemes] if theme})
    impacts = ["All", "Positive", "Negative", "Neutral", "Mixed", "Unknown"]
    update_types = ["All"] + [item for item in UPDATE_TYPES if any(news.updateType == item for news in items)]
    directness = ["All", "Direct", "Indirect", "Macro", "Sector", "Theme"]
    sources = ["All Sources"] + SOURCE_TYPES

    top = st.columns([0.32, 0.18, 0.18, 0.16, 0.16], vertical_alignment="bottom")
    with top[0]:
        st.text_input("Search news", placeholder="Search headlines, themes, tickers...", key="news_search")
    with top[1]:
        st.text_input("Ticker", placeholder="Free text ticker", key="news_ticker_input")
    with top[2]:
        st.multiselect("Ticker filter", all_related_tickers, key="news_ticker_filters")
    with top[3]:
        st.selectbox("Sector", sectors, key="news_sector")
    with top[4]:
        st.selectbox("Theme", themes, key="news_theme")

    bottom = st.columns([0.16, 0.18, 0.17, 0.17, 0.18, 0.14], vertical_alignment="bottom")
    with bottom[0]:
        st.selectbox("Impact", impacts, key="news_impact")
    with bottom[1]:
        st.selectbox("Update Type", update_types, key="news_update_type")
    with bottom[2]:
        st.selectbox("Directness", directness, key="news_directness")
    with bottom[3]:
        st.selectbox("Date", ["Today", "Last 7 Days", "Last 30 Days", "Custom", "All"], key="news_date_filter")
    with bottom[4]:
        st.selectbox("Source", sources, key="news_source_type")
    with bottom[5]:
        st.button("Reset", key="reset_news_filters_button", use_container_width=True, on_click=_reset_news_filters)

    if st.session_state.get("news_date_filter") == "Custom":
        custom_cols = st.columns(2)
        with custom_cols[0]:
            st.date_input("Start date", key="news_custom_start")
        with custom_cols[1]:
            st.date_input("End date", key="news_custom_end")


def _render_news_detail_drawer(items: list[NewsItem]) -> None:
    ticker = st.session_state.get("news_detail_ticker")
    if not ticker:
        return
    item_id = st.session_state.get("news_detail_item")
    item = next((row for row in items if row.id == item_id), None)
    html(
        section(
            f"{ticker} News Detail",
            "Ticker is not yet modeled in Company Analysis",
            f"""
            <div class="pt-news-detail-grid">
              {value_row("Related item", item.headline if item else "N/A")}
              {value_row("Impact", item.impact if item else "Unknown", _news_tone(item.impact if item else ""))}
              {value_row("Why it matters", item.whyItMatters if item else "No detail available.")}
              {value_row("Valuation lever", item.affectedValuationLever if item else "Unknown")}
            </div>
            """,
        )
    )
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        if st.button(f"Add {ticker} to Watchlist", key=f"news_add_watch_{ticker}", use_container_width=True):
            _add_watchlist_ticker(str(ticker))
            st.rerun()
    with col2:
        if st.button("Close Detail", key="news_close_detail"):
            st.session_state.pop("news_detail_ticker", None)
            st.session_state.pop("news_detail_item", None)
            st.rerun()


def _render_news_item_expander(item: NewsItem, key_prefix: str) -> None:
    with st.expander(f"Details: {item.headline}", expanded=False):
        detail_cols = st.columns([0.34, 0.28, 0.2, 0.18])
        with detail_cols[0]:
            st.markdown(f"**Summary**  \n{item.summary}")
            st.markdown(f"**Why it matters**  \n{item.whyItMatters}")
        with detail_cols[1]:
            st.markdown("**Related tickers**")
            _render_news_ticker_actions(item, f"{key_prefix}_ticker")
            st.markdown("**Related themes**  \n" + ", ".join(item.readThroughThemes or item.themes or ["N/A"]))
        with detail_cols[2]:
            st.markdown(f"**Thesis lever**  \n{item.affectedThesisLever}")
            st.markdown(f"**Valuation lever**  \n{item.affectedValuationLever}")
            st.markdown(f"**Dashboard adjustment**  \n{item.dashboardAdjustment}")
        with detail_cols[3]:
            st.markdown(f"**Confidence**  \n{item.confidence}")
            st.caption(item.confidenceExplanation)
            if item.url:
                st.markdown(f"[View source]({item.url})")
            else:
                st.caption(f"Source: {item.source}")


def _render_news_table(items: list[NewsItem]) -> None:
    if not items:
        html(section("Market-Wide News", "No matching items", '<p class="pt-placeholder">Try loosening filters or switching feed mode.</p>'))
        return
    header = st.columns([0.09, 0.12, 0.26, 0.1, 0.08, 0.13, 0.13, 0.12, 0.22, 0.1])
    labels = ["Date", "Ticker / Theme", "Headline", "Type", "Impact", "Thesis Lever", "Valuation Lever", "Adjustment", "Why It Matters", "Source"]
    for col, label in zip(header, labels):
        with col:
            st.markdown(f'<div class="pt-news-header-cell">{escape(label)}</div>', unsafe_allow_html=True)
    for idx, item in enumerate(items[:20]):
        primary, extra = _news_primary_label(item)
        row = st.columns([0.09, 0.12, 0.26, 0.1, 0.08, 0.13, 0.13, 0.12, 0.22, 0.1], vertical_alignment="center")
        with row[0]:
            st.markdown(f'<span class="pt-news-cell">{escape(item.timestamp.strftime("%Y-%m-%d"))}<small>{escape(item.timestamp.strftime("%I:%M %p ET").lstrip("0"))}</small></span>', unsafe_allow_html=True)
        with row[1]:
            if primary in item.tickers:
                if st.button(primary, key=f"news_primary_{item.id}_{idx}", help=f"Open {primary}", use_container_width=True):
                    _open_news_ticker(primary, item)
            else:
                st.markdown(f'<span class="pt-news-cell"><b>{escape(primary)}</b></span>', unsafe_allow_html=True)
            if extra:
                st.caption(extra)
        with row[2]:
            st.markdown(f'<span class="pt-news-cell headline">{escape(item.headline)}</span>', unsafe_allow_html=True)
        with row[3]:
            st.markdown(_news_badge(item.updateType, "neutral"), unsafe_allow_html=True)
        with row[4]:
            st.markdown(_news_badge(item.impact), unsafe_allow_html=True)
        with row[5]:
            st.markdown(f'<span class="pt-news-cell">{escape(item.affectedThesisLever)}</span>', unsafe_allow_html=True)
        with row[6]:
            st.markdown(f'<span class="pt-news-cell">{escape(item.affectedValuationLever)}</span>', unsafe_allow_html=True)
        with row[7]:
            st.markdown(f'<span class="pt-news-cell {_news_tone(item.dashboardAdjustment)}">{escape(item.dashboardAdjustment)}</span>', unsafe_allow_html=True)
        with row[8]:
            st.markdown(f'<span class="pt-news-cell">{escape(item.whyItMatters)}</span>', unsafe_allow_html=True)
        with row[9]:
            st.markdown(f'<span class="pt-news-cell source">{_news_source_link(item)}</span>', unsafe_allow_html=True)
        _render_news_item_expander(item, f"table_{idx}")


def _render_news_cards(items: list[NewsItem]) -> None:
    if not items:
        html(section("Market-Wide News", "No matching items", '<p class="pt-placeholder">Try loosening filters or switching feed mode.</p>'))
        return
    for idx, item in enumerate(items[:16]):
        ticker_list = ", ".join(item.tickers or item.readThroughTickers[:5] or ["Theme-driven"])
        theme_list = ", ".join(item.themes[:4] or item.readThroughThemes[:4] or ["Market"])
        html(
            f"""
            <div class="pt-news-card">
              <div class="pt-news-card-head">
                <div>
                  <strong>{escape(item.headline)}</strong>
                  <small>{escape(item.source)} / {escape(item.timestamp.strftime("%Y-%m-%d %I:%M %p ET").replace(" 0", " "))}</small>
                </div>
                <div>{_news_badge(item.impact)} {_news_badge(item.updateType, "neutral")} {_news_badge(item.directness)}</div>
              </div>
              <div class="pt-news-card-meta">
                <span><b>Themes</b>{escape(theme_list)}</span>
                <span><b>Affected Tickers</b>{escape(ticker_list)}</span>
                <span><b>Valuation Lever</b>{escape(item.affectedValuationLever)}</span>
                <span><b>Dashboard Adjustment</b>{escape(item.dashboardAdjustment)}</span>
              </div>
              <p><b>Why it matters:</b> {escape(item.whyItMatters)}</p>
            </div>
            """
        )
        _render_news_item_expander(item, f"card_{idx}")


def render_news_feed_page() -> None:
    _news_state_defaults()
    provider = market_news_provider()
    all_items = provider.getMarketNews()
    _render_news_header("Demo")
    _render_news_filters(all_items)

    ticker_inputs = list(st.session_state.get("news_ticker_filters", []))
    typed_ticker = clean_ticker(st.session_state.get("news_ticker_input", ""))
    if typed_ticker:
        ticker_inputs.append(typed_ticker)
    selected_ticker = typed_ticker or st.session_state.get("selected_ticker", "")
    filtered_items = filter_news_items(
        all_items,
        mode=st.session_state.get("news_feed_mode", "Market-Wide"),
        watchlist_tickers=_active_watchlist_tickers(),
        selected_ticker=selected_ticker,
        ticker_filters=ticker_inputs,
        sector=st.session_state.get("news_sector", "All"),
        theme=st.session_state.get("news_theme", "All"),
        impact=st.session_state.get("news_impact", "All"),
        update_type=st.session_state.get("news_update_type", "All"),
        directness=st.session_state.get("news_directness", "All"),
        source_type=st.session_state.get("news_source_type", "All Sources"),
        date_filter=st.session_state.get("news_date_filter", "Last 7 Days"),
        custom_start=st.session_state.get("news_custom_start"),
        custom_end=st.session_state.get("news_custom_end"),
        search=st.session_state.get("news_search", ""),
    )
    summary = news_summary(filtered_items, _active_watchlist_tickers())
    html(_news_summary_markup(summary))
    html(
        f"""
        <div class="pt-news-feed-status">
          <b>{escape(st.session_state.get("news_feed_mode", "Market-Wide"))}</b>
          <span>{len(filtered_items)} classified items sorted by relevance, recency, and confidence.</span>
          <span title="Demo feed with local classification and market read-through mapping">Data Sources</span>
        </div>
        """
    )
    _render_news_detail_drawer(all_items)
    if st.session_state.get("news_view_mode", "Table View") == "Card View":
        _render_news_cards(filtered_items)
    else:
        _render_news_table(filtered_items)


def _economic_event_date(row: dict[str, object]):
    return datetime.strptime(str(row["date"]), "%Y-%m-%d").date()


def _first_of_month(day: date) -> date:
    return date(day.year, day.month, 1)


def _add_months(day: date, offset: int) -> date:
    month_index = day.year * 12 + day.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _coerce_calendar_month(value: object, fallback: date) -> date:
    if isinstance(value, date):
        return _first_of_month(value)
    if isinstance(value, str):
        try:
            return _first_of_month(datetime.strptime(value, "%Y-%m-%d").date())
        except ValueError:
            return fallback
    return fallback


def _economic_month_context(target_month: date, today: date) -> str:
    current_month = _first_of_month(today)
    if target_month < current_month:
        return "Previous reports released"
    if target_month > current_month:
        return "Future reports scheduled"
    return "Current month macro releases"


def _render_economic_month_nav(today: date) -> date:
    current_month = _first_of_month(today)
    target_month = _coerce_calendar_month(st.session_state.get("economic_calendar_month"), current_month)
    st.session_state["economic_calendar_month"] = target_month
    month_label = f"{calendar.month_name[target_month.month]} {target_month.year}"
    context = _economic_month_context(target_month, today)
    prev_col, label_col, next_col, current_col = st.columns([0.07, 0.73, 0.07, 0.13], vertical_alignment="center")
    with prev_col:
        if st.button("←", key="economic_calendar_prev_month", use_container_width=True, help="Previous month"):
            st.session_state["economic_calendar_month"] = _add_months(target_month, -1)
            st.rerun()
    with label_col:
        html(
            f"""
            <div class="pt-calendar-nav-label">
              <span>{escape(context)}</span>
              <strong>{escape(month_label)}</strong>
            </div>
            """
        )
    with next_col:
        if st.button("→", key="economic_calendar_next_month", use_container_width=True, help="Next month"):
            st.session_state["economic_calendar_month"] = _add_months(target_month, 1)
            st.rerun()
    with current_col:
        if st.button("Current", key="economic_calendar_current_month", use_container_width=True, disabled=target_month == current_month):
            st.session_state["economic_calendar_month"] = current_month
            st.rerun()
    return target_month


def _economic_event_tone(row: dict[str, object]) -> str:
    status = str(row.get("status", "")).casefold()
    impact = str(row.get("impact", "")).casefold()
    if status == "released":
        return "good" if impact == "high" else "info"
    if impact == "high":
        return "warn"
    return "neutral"


def _economic_event_card(row: dict[str, object]) -> str:
    tone = _economic_event_tone(row)
    source_url = escape(str(row.get("source_url", "")))
    source_label = escape(str(row.get("source_label", "Source")))
    source_link = f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_label}</a>' if source_url else ""
    data_mode = escape(str(row.get("data_mode", row.get("status", "Calendar"))))
    release_note = escape(str(row.get("release_note", "")))
    release_detail = f"<small>{release_note}</small>" if release_note else ""
    return f"""
    <div class="pt-eco-event {tone}">
      <div class="pt-eco-event-head">
        <strong>{escape(str(row["event"]))}</strong>
        <span>{escape(str(row.get("time", "")))} | {escape(str(row.get("category", "")))}</span>
      </div>
      <div class="pt-eco-values">
        <span><b>Actual</b>{escape(str(row.get("actual", "Pending")))}</span>
        <span><b>Estimate</b>{escape(str(row.get("estimate", "TBD")))}</span>
        <span><b>Previous</b>{escape(str(row.get("previous", "N/A")))}</span>
      </div>
      <p>{escape(str(row.get("why_it_matters", "")))}</p>
      {release_detail}
      <div class="pt-eco-source"><em>{escape(str(row.get("impact", "Medium")))} impact | {data_mode}</em>{source_link}</div>
    </div>
    """


def _economic_calendar_markup(year: int, month: int, today) -> str:
    enriched_events, calendar_status = enrich_economic_calendar_events(
        ECONOMIC_CALENDAR_EVENTS,
        current_date=today,
        refresh_token=_refresh_bucket(_auto_refresh_interval_ms("Economic Data")),
    )
    events = [row for row in enriched_events if (event_date := _economic_event_date(row)).year == year and event_date.month == month]
    events_by_date: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in events:
        events_by_date[_economic_event_date(row)].append(row)
    month_label = f"{calendar.month_name[month]} {year}"
    target_month = date(year, month, 1)
    subtitle = _economic_month_context(target_month, today)
    released = sum(1 for row in events if str(row.get("status", "")).casefold() == "released")
    pending = sum(1 for row in events if str(row.get("actual", "")).casefold() == "pending")
    high_impact = sum(1 for row in events if str(row.get("impact", "")).casefold() == "high")
    updated = sum(1 for row in events if row.get("actual_updated") or str(row.get("data_mode", "")).casefold().endswith("official actual"))
    summary = f"""
    <div class="pt-score-breakdown">
      <div class="pt-row-card"><span class="pt-mini-label">Month</span><strong>{escape(month_label)}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Events</span><strong>{len(events)}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Released</span><strong class="good">{released}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Updated Actuals</span><strong class="good">{updated}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Pending</span><strong class="warn">{pending}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">High Impact</span><strong class="warn">{high_impact}</strong></div>
    </div>
    """
    weekday_header = "".join(f"<div>{day}</div>" for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    cells = ""
    for week in weeks:
        for day in week:
            classes = ["pt-calendar-day"]
            if day.month != month:
                classes.append("muted")
            if day == today:
                classes.append("today")
            day_events = "".join(_economic_event_card(row) for row in events_by_date.get(day, []))
            empty = '<span class="pt-calendar-empty">No major releases</span>' if day.month == month and not day_events else ""
            cells += f'<div class="{" ".join(classes)}"><div class="pt-calendar-date">{day.day}</div>{day_events}{empty}</div>'
    checked = escape(str(calendar_status.get("last_updated", "Latest available")))
    note = f"""
    <p class="pt-calendar-note">
      Released actuals are overlaid from official source pages and refreshed with the Economic Data tab. Last official actuals refresh: {checked}.
      Estimates remain market-consensus placeholders when the official source does not publish forecasts.
    </p>
    """
    return f"""
    {section("Economic Calendar", subtitle, summary)}
    <div class="pt-calendar">
      <div class="pt-calendar-weekdays">{weekday_header}</div>
      <div class="pt-calendar-grid">{cells}</div>
    </div>
    {note}
    """


def render_economic_page() -> None:
    today = now_et().date()
    target_month = _render_economic_month_nav(today)
    html(_economic_calendar_markup(target_month.year, target_month.month, today))


def render_calendar_page() -> None:
    render_dataframe(UPCOMING_EVENTS, 360)


VALUATION_METHODS = ["Revenue Multiple", "P/E", "EBITDA Multiple", "Asset Price Scenario"]


def _valuation_editor_candidates() -> list[str]:
    tickers = {
        st.session_state.get("selected_ticker", "AMPX"),
        *_active_watchlist_tickers(),
        *_portfolio_tickers(_active_portfolio_holdings()),
        *configured_valuation_tickers(),
    }
    return sorted(clean_ticker(str(ticker)) for ticker in tickers if clean_ticker(str(ticker)))


def _default_valuation_editor_spec(ticker: str, method: str = "Revenue Multiple") -> dict[str, object]:
    if method == "P/E":
        return {
            "valuation_method": "P/E",
            "model_year": 2028,
            "net_debt": 0.0,
            "shares": None,
            "key_assumption": f"{ticker} needs validated EPS and multiple assumptions.",
            "scenarios": [
                ("Bear Case", 0.25, 18.0, None, 0.25, "Earnings power remains limited and the multiple compresses.", "Needs proof"),
                ("Base Case", 0.75, 24.0, None, 0.50, "Revenue growth converts into positive earnings power.", "Draft assumption"),
                ("Bull Case", 1.50, 30.0, None, 0.25, "Growth and margins improve enough to support premium earnings power.", "Upside case"),
            ],
        }
    if method == "EBITDA Multiple":
        return {
            "valuation_method": "EBITDA Multiple",
            "model_year": 2028,
            "net_debt": 0.0,
            "shares": None,
            "key_assumption": f"{ticker} needs validated EBITDA, dilution, and multiple assumptions.",
            "scenarios": [
                ("Bear Case", 10_000_000, 10.0, None, 0.25, "EBITDA remains small and valuation support weakens.", "Needs proof"),
                ("Base Case", 40_000_000, 14.0, None, 0.50, "Operating leverage creates a visible EBITDA base.", "Draft assumption"),
                ("Bull Case", 100_000_000, 18.0, None, 0.25, "Margins scale and the market assigns a premium EBITDA multiple.", "Upside case"),
            ],
        }
    if method == "Asset Price Scenario":
        return {
            "valuation_method": "Asset Price Scenario",
            "model_year": 2028,
            "net_debt": 0.0,
            "shares": None,
            "key_assumption": f"{ticker} value is primarily driven by asset-price scenario sensitivity.",
            "scenarios": [
                ("Bear Case", 80.0, None, None, 0.25, "Asset price declines and NAV/share contracts.", "Needs monitoring", 0.75),
                ("Base Case", 120.0, None, None, 0.50, "Asset price appreciates moderately.", "Draft assumption", 1.10),
                ("Bull Case", 180.0, None, None, 0.25, "Asset price appreciation accelerates.", "Upside case", 1.60),
            ],
        }
    return {
        "valuation_method": "Revenue Multiple",
        "model_year": 2028,
        "net_debt": 0.0,
        "shares": None,
        "key_assumption": f"{ticker} needs validated revenue, dilution, and multiple assumptions.",
        "scenarios": [
            ("Bear Case", 25_000_000, 3.0, None, 0.25, "Growth remains early and valuation multiple compresses.", "Needs proof"),
            ("Base Case", 75_000_000, 5.0, None, 0.50, "Revenue scales from a small base and the current model framework holds.", "Draft assumption"),
            ("Bull Case", 180_000_000, 8.0, None, 0.25, "Customer adoption accelerates and market support improves.", "Upside case"),
        ],
    }


def _editor_metric_value(value: object, method: str) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if method in {"P/E", "Asset Price Scenario"}:
        return round(number, 2)
    return round(number / 1_000_000, 2)


def _spec_metric_value(value: object, method: str) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if method in {"P/E", "Asset Price Scenario"}:
        return number
    return number * 1_000_000


def _editor_shares(value: object) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return round(number / 1_000_000, 2) if number else 0.0


def _spec_shares(value: object, method: str) -> float | None:
    if method in {"P/E", "Asset Price Scenario"}:
        return None
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return None
    return number * 1_000_000 if number > 0 else None


def _scenario_rows_for_editor(spec: dict[str, object], method: str) -> list[dict[str, object]]:
    rows = []
    for row in spec.get("scenarios", []):
        scenario = tuple(row)
        factor = scenario[7] if method == "Asset Price Scenario" and len(scenario) > 7 else scenario[2]
        rows.append(
            {
                "Case": str(scenario[0]),
                "Metric": _editor_metric_value(scenario[1], method),
                "Multiple / Factor": float(factor or 0.0),
                "Diluted Shares (M)": _editor_shares(scenario[3]),
                "Probability %": round(float(scenario[4] or 0.0) * 100, 1),
                "Assumption": str(scenario[5]),
                "Quality": str(scenario[6]) if len(scenario) > 6 else "Model assumptions",
            }
        )
    return rows


def _spec_from_editor(
    *,
    method: str,
    model_year: int,
    net_debt_m: float,
    shares_m: float,
    key_assumption: str,
    scenario_rows: pd.DataFrame,
) -> dict[str, object]:
    scenarios = []
    for row in scenario_rows.to_dict("records"):
        probability = max(0.0, float(row.get("Probability %") or 0.0)) / 100
        metric = _spec_metric_value(row.get("Metric"), method)
        shares = _spec_shares(row.get("Diluted Shares (M)") or shares_m, method)
        factor_or_multiple = float(row.get("Multiple / Factor") or 0.0)
        if method == "Asset Price Scenario":
            scenarios.append((row.get("Case"), metric, None, None, probability, row.get("Assumption"), row.get("Quality"), factor_or_multiple))
        else:
            scenarios.append((row.get("Case"), metric, factor_or_multiple, shares, probability, row.get("Assumption"), row.get("Quality")))
    return {
        "valuation_method": method,
        "model_year": model_year,
        "net_debt": net_debt_m * 1_000_000,
        "shares": shares_m * 1_000_000 if shares_m > 0 else None,
        "key_assumption": key_assumption,
        "scenarios": scenarios,
    }


def render_valuation_assumptions_editor() -> None:
    html(
        section(
            "Valuation Assumptions",
            "Configure ticker-specific forecast inputs",
            '<p class="pt-placeholder">Use this when a ticker shows incomplete or stale valuation inputs. Saved assumptions apply immediately for this session.</p>',
        )
    )
    candidates = _valuation_editor_candidates()
    selected_ticker = st.selectbox("Ticker", candidates, index=candidates.index(st.session_state["selected_ticker"]) if st.session_state["selected_ticker"] in candidates else 0)
    base_spec = get_valuation_spec(selected_ticker) or _default_valuation_editor_spec(selected_ticker)
    default_method = str(base_spec.get("valuation_method") or "Revenue Multiple")
    method = st.selectbox("Valuation method", VALUATION_METHODS, index=VALUATION_METHODS.index(default_method) if default_method in VALUATION_METHODS else 0)
    editor_spec = base_spec if method == default_method else _default_valuation_editor_spec(selected_ticker, method)
    metric_note = {
        "P/E": "Metric = future EPS. Multiple / Factor = P/E multiple.",
        "Asset Price Scenario": "Metric = future asset price. Multiple / Factor = NAV/share factor.",
    }.get(method, "Metric = future revenue or EBITDA in $M. Multiple / Factor = valuation multiple.")
    with st.form("valuation_assumption_form"):
        model_col, net_debt_col, shares_col = st.columns(3)
        with model_col:
            model_year = st.number_input("Model year", min_value=2026, max_value=2035, value=int(editor_spec.get("model_year") or 2028), step=1)
        with net_debt_col:
            net_debt_m = st.number_input("Net debt / (cash) $M", value=round(float(editor_spec.get("net_debt") or 0.0) / 1_000_000, 1), step=5.0)
        with shares_col:
            shares_m = st.number_input("Default diluted shares (M)", min_value=0.0, value=_editor_shares(editor_spec.get("shares")), step=1.0)
        key_assumption = st.text_area("Key assumption", value=str(editor_spec.get("key_assumption") or ""), height=70)
        st.caption(metric_note)
        edited_rows = st.data_editor(
            pd.DataFrame(_scenario_rows_for_editor(editor_spec, method)),
            hide_index=True,
            num_rows="fixed",
            use_container_width=True,
            key=f"valuation_editor_{selected_ticker}_{method}",
            column_config={
                "Case": st.column_config.TextColumn(disabled=True),
                "Metric": st.column_config.NumberColumn(format="%.2f"),
                "Multiple / Factor": st.column_config.NumberColumn(format="%.2f"),
                "Diluted Shares (M)": st.column_config.NumberColumn(format="%.2f"),
                "Probability %": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.1f"),
            },
        )
        saved = st.form_submit_button("Save Assumptions", use_container_width=True)
    if saved:
        spec = _spec_from_editor(method=method, model_year=int(model_year), net_debt_m=float(net_debt_m), shares_m=float(shares_m), key_assumption=key_assumption, scenario_rows=edited_rows)
        st.session_state["valuation_assumption_specs"][selected_ticker] = spec
        register_valuation_spec(selected_ticker, spec)
        st.session_state["selected_ticker"] = selected_ticker
        st.success(f"Saved valuation assumptions for {selected_ticker}.")
        st.rerun()


def render_settings_page() -> None:
    html(
        section(
            "Settings",
            "Demo configuration",
            """
            <p class="pt-placeholder">
              PineTerminal V2 is running on mock/demo data. The data model is structured so live market prices,
              fundamentals, SEC filings, earnings transcripts, analyst estimates, and portfolio integrations can be added later.
            </p>
            """,
        )
    )
    render_valuation_assumptions_editor()
    st.json(
        {
            "default_ticker": "AMPX",
            "currency": st.session_state["currency"],
            "calculation_mode": "transparent demo helpers",
            "theme_engine": "theme exposure map plus ticker exposure",
            "live_integrations": False,
            "configured_valuation_tickers": configured_valuation_tickers(),
        }
    )


def render_page(page: str, analysis) -> None:
    if page == "Dashboard":
        render_company_dashboard(analysis)
    elif page == "Markets":
        render_home_page()
    elif page == "Market Read-Through":
        render_market_readthrough_page()
    elif page == "Scanner":
        render_scanner_page()
    elif page == "Watchlists":
        render_watchlist_page()
    elif page == "Portfolio":
        render_portfolio_page()
    elif page == "News Feed":
        render_news_feed_page()
    elif page == "Alerts":
        html(section("Alerts", "Configured thesis and valuation monitors", '<p class="pt-placeholder">No active alerts in demo mode.</p>'))
    elif page == "Economic Data":
        render_economic_page()
    elif page == "Calendar":
        render_calendar_page()
    elif page == "Settings":
        render_settings_page()


def main() -> None:
    _init_state()
    _apply_session_valuation_specs()
    watchlist_rows = _watchlist_rows()
    page = render_sidebar(watchlist_rows)
    render_auto_refresh_timer(page)
    analysis = load_dashboard_analysis(st.session_state["selected_ticker"])
    render_global_controls(page, analysis)
    render_watchlist_tape(watchlist_rows)
    render_auto_refresh_status(page)
    render_page(page, analysis)


if __name__ == "__main__":
    main()
