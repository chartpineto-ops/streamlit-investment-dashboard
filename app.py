from __future__ import annotations

from dataclasses import asdict
from html import escape

import streamlit as st

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
    ECONOMIC_DATA,
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
from storage.db import connect, init_db
from storage.watchlist import add_ticker as store_add_ticker
from storage.watchlist import latest_quote_snapshot, remove_ticker as store_remove_ticker
from utils.formatting import clean_ticker, now_et


PAGES = [
    "Dashboard",
    "Markets",
    "Market Read-Through",
    "Screener",
    "Watchlists",
    "Thesis Tracker",
    "Portfolio",
    "News Feed",
    "Alerts",
    "Economic Data",
    "Calendar",
    "Settings",
]

APP_STATE_VERSION = "pineterminal-dashboard-v3"
DEFAULT_WATCHLIST = ["AMPX", "MRVL", "VICR", "IONQ", "MP", "FBTC", "CEG", "NVDA"]


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


def _init_state() -> None:
    if st.session_state.get("_pt_app_state_version") != APP_STATE_VERSION:
        for key in ("currency", "page"):
            st.session_state.pop(key, None)
        st.session_state["_pt_app_state_version"] = APP_STATE_VERSION
    st.session_state.setdefault("selected_ticker", "AMPX")
    st.session_state.setdefault("currency", "USD")
    st.session_state.setdefault("page", "Dashboard")
    if "watchlist_tickers" not in st.session_state:
        st.session_state["watchlist_tickers"] = _load_persistent_watchlist_tickers()
    st.session_state.setdefault("watchlist_add_open", False)
    st.session_state.setdefault("watchlist_message", "")


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
    }


def _watchlist_rows() -> list[dict[str, object]]:
    built_in = {str(row["Ticker"]): row for row in all_watchlist_rows()}
    rows = []
    for ticker in _active_watchlist_tickers():
        row = built_in.get(ticker)
        if row is not None:
            rows.append(row)
            continue
        try:
            rows.append(_analysis_watchlist_row(ticker))
        except Exception:
            snapshot = latest_quote_snapshot(ticker) or {}
            rows.append(
                {
                    "Ticker": ticker,
                    "Company": snapshot.get("company") or ticker,
                    "Price": snapshot.get("price") or 0.0,
                    "Daily Change": snapshot.get("daily_move_pct") or 0.0,
                    "Fundamental Score": 0.0,
                    "Expected Return": 0.0,
                    "Net Thesis Impact": 0.0,
                    "Latest Thesis Impact": "N/A",
                    "Investment Signal": "No Rating",
                    "Risk Level": "N/A",
                    "Theme": "Live",
                    "Market Cap": snapshot.get("market_cap") or 0.0,
                    "Revenue Growth": "N/A",
                    "Gross Margin": "N/A",
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


def render_sidebar() -> str:
    with st.sidebar:
        render_brand()
        page = st.radio("Navigation", PAGES, index=PAGES.index(st.session_state.get("page", "Dashboard")), label_visibility="collapsed")
        st.session_state["page"] = page
        render_watchlist_sidebar(_watchlist_rows())
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


def market_tape() -> str:
    movers = MARKET_MOVERS + MARKET_MOVERS
    items = "".join(
        f'<span><b>{row["ticker"]}</b> {price(float(row["price"]))} <b class="{tone_for_value(float(row["change"]))}">{percent(float(row["change"]), 2)}</b></span>'
        for row in movers
    )
    return f'<div class="pt-tape"><div class="pt-tape-inner">{items}</div></div>'


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
        + section("Moving Market Ticker", "", market_tape())
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


def render_screener_page() -> None:
    rows = screener_rows()
    signals = ["All"] + sorted({str(row["Investment Signal"]) for row in rows})
    risks = ["All"] + sorted({str(row["Risk Level"]) for row in rows})
    filters = st.columns(4)
    with filters[0]:
        min_score = st.slider("Minimum Fundamental Score", 0.0, 10.0, 5.0, 0.5)
    with filters[1]:
        min_return = st.slider("Minimum Expected Return", -50, 150, 0, 5)
    with filters[2]:
        signal = st.selectbox("Investment Signal", signals)
    with filters[3]:
        risk = st.selectbox("Risk Level", risks)
    filtered = []
    for row in rows:
        if float(row["Fundamental Score"]) < min_score:
            continue
        if float(row["Expected Return"]) < min_return:
            continue
        if signal != "All" and row["Investment Signal"] != signal:
            continue
        if risk != "All" and row["Risk Level"] != risk:
            continue
        filtered.append(row)
    render_dataframe(filtered, 460)


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


def render_thesis_tracker_page() -> None:
    rows = []
    for ticker, analysis in ANALYSES.items():
        rows.append(
            {
                "Ticker": ticker,
                "Original Thesis": _original_thesis(ticker),
                "Current Thesis Status": analysis.thesis_summary.status,
                "Bull Case Drivers": ", ".join(analysis.company.themes[:2]),
                "Bear Case Risks": analysis.risks[0].risk_name,
                "Recent Updates": analysis.thesis_updates[0].title,
                "Thesis Trend": analysis.thesis_summary.status,
                "Conviction Change": f"{analysis.thesis_summary.net_thesis_impact_score:+.1f}",
            }
        )
    render_dataframe(rows, 520)


def _original_thesis(ticker: str) -> str:
    if ticker == "AMPX":
        return "High-density batteries can benefit from drone, aviation, and EV applications where weight and endurance matter."
    themes = ", ".join(COMPANIES[ticker].themes[:2])
    return f"{ticker} benefits if {themes} demand continues strengthening."


def render_portfolio_page() -> None:
    total_risk = sum(row["weight"] for row in PORTFOLIO_HOLDINGS if row["risk"] == "High")
    cards = f"""
    <div class="pt-score-breakdown">
      <div class="pt-row-card"><span class="pt-mini-label">High-Risk Exposure</span><strong class="warn">{total_risk:.1f}%</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Theme Count</span><strong>{len({row["theme"] for row in PORTFOLIO_HOLDINGS})}</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Cash Reserve</span><strong>65.5%</strong></div>
      <div class="pt-row-card"><span class="pt-mini-label">Read-Through Coverage</span><strong class="good">Active</strong></div>
    </div>
    """
    html(section("Portfolio", "Theme and risk monitor", cards))
    render_dataframe(PORTFOLIO_HOLDINGS, 360)


def render_news_feed_page() -> None:
    rows = []
    for ticker, analysis in ANALYSES.items():
        for update in analysis.thesis_updates:
            rows.append(
                {
                    "Date": update.date,
                    "Ticker": ticker,
                    "Title": update.title,
                    "Type": update.type,
                    "Impact": update.impact,
                    "Affected Thesis Lever": update.affected_thesis_lever,
                    "Affected Valuation Lever": update.affected_valuation_lever,
                    "Dashboard Adjustment": update.dashboard_adjustment,
                }
            )
    render_dataframe(rows, 520)


def render_economic_page() -> None:
    cards = "".join(
        f'<div class="pt-row-card"><span class="pt-mini-label">{row["metric"]}</span><strong>{row["latest"]}</strong><em>{row["trend"]}</em><p class="pt-placeholder">{row["impact"]}</p></div>'
        for row in ECONOMIC_DATA
    )
    html(section("Economic Data", "Macro inputs that affect valuation levers", f'<div class="pt-score-breakdown">{cards}</div>'))


def render_calendar_page() -> None:
    render_dataframe(UPCOMING_EVENTS, 360)


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
    st.json(
        {
            "default_ticker": "AMPX",
            "currency": st.session_state["currency"],
            "calculation_mode": "transparent demo helpers",
            "theme_engine": "theme exposure map plus ticker exposure",
            "live_integrations": False,
        }
    )


def render_page(page: str, analysis) -> None:
    if page == "Dashboard":
        render_company_dashboard(analysis)
    elif page == "Markets":
        render_home_page()
    elif page == "Market Read-Through":
        render_market_readthrough_page()
    elif page == "Screener":
        render_screener_page()
    elif page == "Watchlists":
        render_watchlist_page()
    elif page == "Thesis Tracker":
        render_thesis_tracker_page()
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
    page = render_sidebar()
    analysis = load_dashboard_analysis(st.session_state["selected_ticker"])
    render_global_controls(page, analysis)
    render_page(page, analysis)


if __name__ == "__main__":
    main()
