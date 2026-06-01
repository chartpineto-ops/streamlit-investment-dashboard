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
    render_watchlist_sidebar,
    section,
    tone_for_value,
    value_row,
)
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
from utils.formatting import clean_ticker


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


st.set_page_config(page_title="PineTerminal", page_icon="P", layout="wide", initial_sidebar_state="expanded")
apply_theme()


def _init_state() -> None:
    if st.session_state.get("_pt_app_state_version") != APP_STATE_VERSION:
        for key in ("currency", "page"):
            st.session_state.pop(key, None)
        st.session_state["_pt_app_state_version"] = APP_STATE_VERSION
    st.session_state.setdefault("selected_ticker", "AMPX")
    st.session_state.setdefault("currency", "USD")
    st.session_state.setdefault("page", "Dashboard")


def _watchlist_for_sidebar() -> list[dict[str, object]]:
    rows = all_watchlist_rows()
    preferred = ["AMPX", "MRVL", "IONQ", "MP", "FBTC", "CEG", "NVDA"]
    return sorted(rows, key=lambda row: preferred.index(str(row["Ticker"])) if str(row["Ticker"]) in preferred else 99)


def render_sidebar() -> str:
    with st.sidebar:
        render_brand()
        page = st.radio("Navigation", PAGES, index=PAGES.index(st.session_state.get("page", "Dashboard")), label_visibility="collapsed")
        st.session_state["page"] = page
        render_watchlist_sidebar(_watchlist_for_sidebar())
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
    rows = all_watchlist_rows()
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
