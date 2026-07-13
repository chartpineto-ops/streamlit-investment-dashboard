from __future__ import annotations

import re

import streamlit as st

from storage.db import init_db
from storage.watchlist import ensure_default_watchlist
from terminal_v2.integrity import provider_health
from terminal_v2.styles import inject_styles
from terminal_v2.views import (
    render_data_page,
    render_intelligence_page,
    render_market_page,
    render_portfolio_page,
    render_screener_page,
    render_security_page,
)
from utils.formatting import clean_ticker, now_et


PAGES = {
    "MARKET": ("MKT", "Market", "Regime, breadth, movers"),
    "SECURITY": ("SEC", "Security", "Underwrite a company"),
    "INTELLIGENCE": ("INTL", "Intelligence", "Catalyst transmission"),
    "SCREENER": ("SCR", "Screener", "Find dislocations"),
    "PORTFOLIO": ("PORT", "Portfolio", "Exposure and alerts"),
    "DATA": ("DATA", "Data", "Sources and integrity"),
}

COMMANDS = {
    "MKT": "MARKET",
    "MARKET": "MARKET",
    "SEC": "SECURITY",
    "SECURITY": "SECURITY",
    "COMPANY": "SECURITY",
    "INTL": "INTELLIGENCE",
    "INTEL": "INTELLIGENCE",
    "INTELLIGENCE": "INTELLIGENCE",
    "SCR": "SCREENER",
    "SCREEN": "SCREENER",
    "SCREENER": "SCREENER",
    "PORT": "PORTFOLIO",
    "PORTFOLIO": "PORTFOLIO",
    "DATA": "DATA",
}


def _initialize_state() -> None:
    init_db()
    ensure_default_watchlist()
    st.session_state.setdefault("page", "MARKET")
    st.session_state.setdefault("ticker", "SPY")
    st.session_state.setdefault("command_entry", "")


def _go(page: str, ticker: str | None = None) -> None:
    st.session_state.page = page
    if ticker:
        st.session_state.ticker = clean_ticker(ticker)
    st.query_params["page"] = page.casefold()
    st.query_params["ticker"] = st.session_state.ticker


def _parse_command(raw: str) -> tuple[str, str | None, str]:
    value = re.sub(r"\s*<GO>\s*$", "", str(raw or "").strip(), flags=re.IGNORECASE).upper()
    if not value:
        return st.session_state.page, None, ""
    parts = value.split()
    head = parts[0]
    if head in COMMANDS:
        page = COMMANDS[head]
        ticker = clean_ticker(parts[1]) if page == "SECURITY" and len(parts) > 1 else None
        return page, ticker, ""
    ticker = clean_ticker(value.replace(" US EQUITY", ""))
    if ticker and re.fullmatch(r"[A-Z0-9.^=-]{1,15}", ticker):
        return "SECURITY", ticker, ""
    return st.session_state.page, None, f"Unknown command: {value}"


def _execute_command(raw: str) -> None:
    page, ticker, error = _parse_command(raw)
    st.session_state.command_error = error
    if not error:
        _go(page, ticker)


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="pt-brand"><div class="pt-brand-name"><span class="pt-brand-mark">▲</span>PineTerminal</div>'
            '<div class="pt-brand-sub">MARKET INTELLIGENCE SYSTEM</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="pt-side-label">WORKSPACES</div>', unsafe_allow_html=True)
        for page, (code, label, _) in PAGES.items():
            button_label = f"{code}   {label}"
            if st.button(button_label, key=f"nav_{page}", use_container_width=True, type="primary" if st.session_state.page == page else "secondary"):
                _go(page)
                st.rerun()
        st.markdown('<div class="pt-side-label">SECURITY LOOKUP</div>', unsafe_allow_html=True)
        ticker_input = st.text_input("Security lookup", value=st.session_state.ticker, label_visibility="collapsed", key="sidebar_ticker", placeholder="Ticker")
        if st.button("SEC  Load Security", use_container_width=True, key="sidebar_load"):
            symbol = clean_ticker(ticker_input)
            if symbol:
                _go("SECURITY", symbol)
                st.rerun()

        health = provider_health()
        official = int(health["configured"].fillna(False).astype(bool).sum())
        st.markdown(
            f'<div class="pt-side-foot"><span class="pt-live-dot"></span>{official}/{len(health)} PRIMARY FEEDS CONFIGURED<br>'
            f'SELECTED <span class="pt-strong">{st.session_state.ticker}</span><br>'
            f'SESSION {now_et().strftime("%H:%M ET")}<br><span class="pt-muted">DATA &lt;GO&gt; for provenance</span></div>',
            unsafe_allow_html=True,
        )


def _render_command_line() -> None:
    with st.form("terminal_command_form", clear_on_submit=False, border=False):
        columns = st.columns([4.8, 0.7, 1.5])
        with columns[0]:
            command = st.text_input(
                "Terminal command",
                placeholder="Enter ticker or command: MKT, SEC NVDA, INTL, SCR, PORT, DATA",
                label_visibility="collapsed",
                key="command_entry",
            )
        with columns[1]:
            submitted = st.form_submit_button("GO", use_container_width=True)
        with columns[2]:
            st.markdown(
                f'<div class="pt-panel-tight pt-mono" style="height:38px;display:flex;align-items:center;justify-content:center;color:#f4b942">'
                f'{st.session_state.page} / {st.session_state.ticker}</div>',
                unsafe_allow_html=True,
            )
    if submitted:
        _execute_command(command)
        st.rerun()
    if st.session_state.get("command_error"):
        st.error(st.session_state.command_error)


def run() -> None:
    st.set_page_config(page_title="PineTerminal", page_icon="▲", layout="wide", initial_sidebar_state="auto")
    inject_styles()
    _initialize_state()
    query_page = str(st.query_params.get("page", "")).upper()
    query_ticker = clean_ticker(str(st.query_params.get("ticker", "")))
    if query_page in PAGES:
        st.session_state.page = query_page
    if query_ticker:
        st.session_state.ticker = query_ticker
    _render_sidebar()
    _render_command_line()

    page = st.session_state.page
    if page == "MARKET":
        render_market_page()
    elif page == "SECURITY":
        render_security_page(st.session_state.ticker)
    elif page == "INTELLIGENCE":
        render_intelligence_page()
    elif page == "SCREENER":
        render_screener_page()
    elif page == "PORTFOLIO":
        render_portfolio_page()
    else:
        render_data_page()
