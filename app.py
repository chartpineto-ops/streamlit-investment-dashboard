from __future__ import annotations

from datetime import datetime
from html import escape
from math import isnan
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai.dd_generator import build_research_packet, generate_dd_memo
from data.company_identity import get_company_identity
from data.filings import fetch_latest_periodic_sec_filing, fetch_latest_sec_filing, fetch_sec_filings, ticker_to_cik
from data.financials import build_three_statement_visual_data, get_latest_quarterly_release, load_latest_company_financials, view_history
from data.macro import fetch_macro_catalysts
from data.market_data import DEFAULT_TICKERS, fetch_history, fetch_market_snapshot, fetch_quote
from data.market_movers import clean_mover_tickers, scan_market_movers
from data.news import fetch_news
from data.options import fetch_options_summary
from data.social import fetch_social_momentum_names
from signals.signal_engine import compute_signal
from storage.db import DB_PATH, init_db
from storage.watchlist import (
    add_ticker,
    dismiss_alert,
    latest_watchlist_table,
    list_alerts,
    list_watchlist,
    refresh_watchlist,
    remove_ticker,
)
from ui.components import clean_dataframe, empty_state, quote_header, render_metric_grid, section, source_line
from ui.styles import BRAND_COLORS, apply_brand_theme
from utils.formatting import (
    clean_ticker,
    fmt_compact,
    fmt_currency,
    fmt_date,
    fmt_eps,
    fmt_multiple,
    fmt_number,
    fmt_percent,
    fmt_price,
    get_date_normalization_status,
    now_et,
    safe_div,
    tone_for_number,
    to_float,
)


def fmt_daily_move(value) -> str:
    return fmt_percent(value, decimals=2, signed=True)


def fmt_meaningful_percent(value, decimals: int = 1, signed: bool = False, nm_threshold: float = 300) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if abs(number) > nm_threshold:
        return "NM"
    return fmt_percent(number, decimals=decimals, signed=signed)


def fmt_growth(value, base_effect: bool = False, signed: bool = True) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if base_effect or abs(number) > 500:
        return "NM / base effect"
    return fmt_percent(number, signed=signed)


PAGES = [
    "Home / Market Monitor",
    "Company Analysis",
    "Watchlist",
    "AI Due Diligence",
    "Data Health / Settings",
]

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
LOGO_PATH = Path("assets/pineterminal_logo.png")


st.set_page_config(page_title="PineTerminal", page_icon="PT", layout="wide")
apply_brand_theme()
init_db()


def reset_data_caches() -> None:
    for cached in (
        fetch_quote,
        fetch_history,
        fetch_market_snapshot,
        load_latest_company_financials,
        get_latest_quarterly_release,
        get_company_identity,
        fetch_options_summary,
        fetch_news,
        fetch_sec_filings,
        fetch_latest_sec_filing,
        fetch_latest_periodic_sec_filing,
        compute_signal,
    ):
        try:
            cached.clear()
        except Exception:
            pass


def normalize_global_ticker_input() -> None:
    normalized = clean_ticker(st.session_state.get("global_ticker_input", ""))
    if normalized:
        st.session_state["global_ticker_input"] = normalized
        st.session_state["global_ticker"] = normalized


def streamlit_secret_value(key: str, default=None):
    secret_paths = [Path.home() / ".streamlit" / "secrets.toml", Path.cwd() / ".streamlit" / "secrets.toml"]
    if not any(path.exists() for path in secret_paths):
        return default
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def logo_file() -> Path | None:
    return LOGO_PATH if LOGO_PATH.exists() else None


def brand_wordmark_html(size_rem: float = 1.35) -> str:
    return (
        f'<div class="brand-wordmark" style="font-size:{size_rem}rem;">'
        '<span class="brand-pine">Pine</span><span class="brand-terminal">Terminal</span>'
        "</div>"
    )


def render_sidebar_brand() -> None:
    logo = logo_file()
    if logo:
        st.sidebar.image(str(logo), use_container_width=True)
    st.sidebar.markdown(brand_wordmark_html(), unsafe_allow_html=True)
    st.sidebar.markdown('<div class="brand-subtitle">V1 Research Terminal</div>', unsafe_allow_html=True)


def render_home_brand_header() -> None:
    logo = logo_file()
    if logo:
        left, right = st.columns([0.14, 0.86])
        with left:
            st.image(str(logo), width=96)
        with right:
            st.markdown(brand_wordmark_html(2.15), unsafe_allow_html=True)
            st.markdown(
                '<div class="terminal-subtitle">Personal investment research terminal for market snapshots, company analysis, watchlists, signals, and AI due diligence.</div>',
                unsafe_allow_html=True,
            )
    else:
        st.title("PineTerminal")
        st.markdown(
            '<div class="terminal-subtitle">Personal investment research terminal for market snapshots, company analysis, watchlists, signals, and AI due diligence.</div>',
            unsafe_allow_html=True,
        )
    st.caption("Built for disciplined market research, not financial advice.")


def plotly_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BRAND_COLORS["background"],
        font={"color": BRAND_COLORS["text"], "family": "Inter, Arial, sans-serif", "size": 12},
        margin={"l": 44, "r": 24, "t": 34, "b": 44},
        height=height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=BRAND_COLORS["border"], zerolinecolor=BRAND_COLORS["pine_dark"], tickfont={"size": 11}, title_font={"size": 12})
    fig.update_yaxes(gridcolor=BRAND_COLORS["border"], zerolinecolor=BRAND_COLORS["pine_dark"], tickfont={"size": 11}, title_font={"size": 12})
    return fig


def render_terminal_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def df_display(frame: pd.DataFrame, height: int = 320) -> None:
    if frame is None or frame.empty:
        empty_state("No data available.")
        return
    frame = frame.copy()
    date_like_columns = ("Date", "Updated", "Refresh", "Published", "Timestamp")
    for column in frame.columns:
        if any(token in str(column) for token in date_like_columns):
            frame[column] = frame[column].map(fmt_date)
    config = {}
    if "Link" in frame.columns:
        config["Link"] = st.column_config.LinkColumn("Link", display_text="Open")
    if "Headline" in frame.columns:
        config["Headline"] = st.column_config.TextColumn("Headline", width="large")
    if "Published" in frame.columns:
        config["Published"] = st.column_config.TextColumn("Published", width="small")
    if "Source" in frame.columns:
        config["Source"] = st.column_config.TextColumn("Source", width="small")
    if "Tag" in frame.columns:
        config["Tag"] = st.column_config.TextColumn("Tag", width="small")
    if "Accession" in frame.columns:
        config["Accession"] = st.column_config.TextColumn("Accession", width="medium")
    st.dataframe(clean_dataframe(frame), use_container_width=True, hide_index=True, height=height, column_config=config)


def latest_row(financials: dict, view: str = "Quarterly") -> dict:
    history = view_history(financials, view)
    if history is None or history.empty:
        return {}
    return history.iloc[-1].to_dict()


def valuation_label(signal: dict) -> str:
    return signal.get("valuation_label") or "Not meaningful / insufficient data"


def balance_sheet_risk_label(latest: dict) -> tuple[str, str]:
    cash = to_float(latest.get("cash"))
    debt = to_float(latest.get("total_debt"))
    current_ratio = to_float(latest.get("current_ratio"))
    fcf = to_float(latest.get("free_cash_flow"))
    equity = to_float(latest.get("shareholders_equity"))
    score = 50
    if cash is None and debt is None:
        return "Insufficient data", "neutral"
    runway_years = cash / abs(fcf) if cash is not None and fcf is not None and fcf < 0 else None
    if runway_years is not None:
        if runway_years < 1:
            return "High", "bad"
        if runway_years < 2:
            return "Elevated", "warn"
        score -= 5
    if cash is not None and debt is not None:
        score += 15 if cash >= debt else -20
    if current_ratio is not None:
        score += 15 if current_ratio >= 1.5 else -15 if current_ratio < 1 else 0
    if fcf is not None and fcf < 0:
        score -= 12
    if debt is not None and equity is not None and equity > 0 and debt / equity > 2:
        score -= 20
    if score >= 72:
        return "Low", "good"
    if score >= 52:
        return "Moderate", "neutral"
    if score >= 35:
        return "Elevated", "warn"
    return "High", "bad"


def cash_runway_caption(latest: dict) -> str:
    cash = to_float(latest.get("cash"))
    fcf = to_float(latest.get("free_cash_flow"))
    if cash is not None and fcf is not None and fcf < 0:
        years = cash / abs(fcf) if fcf else None
        return f"Approx. {years:.1f} years runway" if years is not None else "Runway unavailable"
    if fcf is not None and fcf >= 0:
        return "FCF positive or breakeven"
    return "Runway unavailable"


def clean_news_table(news: pd.DataFrame) -> pd.DataFrame:
    if news is None or news.empty:
        return pd.DataFrame()
    display = news.copy()
    if "Headline" in display:
        display = display.dropna(subset=["Headline"]).drop_duplicates(subset=["Headline"])
    if "Published" in display:
        display = display.sort_values("Published", ascending=False, na_position="last")
    if "Published" in display:
        display["Published"] = display["Published"].map(fmt_date)
    if "Link" in display:
        display["Link"] = display["Link"].map(lambda value: value if isinstance(value, str) and value.startswith("http") else None)
    cols = [col for col in ["Published", "Headline", "Source", "Tag", "Link"] if col in display]
    return display[cols]


def company_headlines(news: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if news is None or news.empty:
        return pd.DataFrame()
    symbol = clean_ticker(ticker)
    scoped = news[news["Scope"].astype(str).eq("Company")] if "Scope" in news else news.copy()
    if scoped.empty:
        return scoped
    if symbol and "Ticker" in scoped:
        ticker_scoped = scoped[scoped["Ticker"].astype(str).str.upper().eq(symbol)]
        if not ticker_scoped.empty:
            return ticker_scoped
    return scoped


def macro_headlines(news: pd.DataFrame) -> pd.DataFrame:
    if news is None or news.empty:
        return pd.DataFrame()
    if "Scope" in news:
        return news[news["Scope"].astype(str).eq("Macro")]
    return news


def source_status_summary(statuses: list[dict]) -> tuple[str, str]:
    if not statuses:
        return "Free news feeds", "Unavailable"
    ok = sum(1 for status in statuses if status.get("Status") == "OK")
    source_names = [str(status.get("Source")) for status in statuses if status.get("Source")]
    state = "OK" if ok == len(statuses) else "Partial" if ok else "Unavailable"
    return ", ".join(source_names[:3]) or "Free news feeds", state


def _first_number(*values) -> float | None:
    for value in values:
        number = to_float(value)
        if number is not None:
            return number
    return None


def _range_position_pct(quote: dict) -> float | None:
    price = to_float(quote.get("price"))
    low = to_float(quote.get("fifty_two_week_low"))
    high = to_float(quote.get("fifty_two_week_high"))
    if price is None or low is None or high is None or high <= low:
        return None
    return max(0, min((price - low) / (high - low), 1)) * 100


def _stance_from_signal(label: str) -> tuple[str, str]:
    if label == "Buy":
        return "Bullish", "good"
    if label == "Speculative Buy":
        return "Bullish / Speculative", "good"
    if label == "Hold / Watchlist":
        return "Neutral", "warn"
    if label in {"Sell / Trim", "Avoid"}:
        return "Bearish", "bad"
    return "No Rating", "neutral"


def _signal_tone(label: str) -> str:
    if label in {"Buy", "Speculative Buy"}:
        return "good"
    if label in {"Sell / Trim", "Avoid"}:
        return "bad"
    if label == "Hold / Watchlist":
        return "warn"
    return "neutral"


def _hero_chip(label: str, value: str, tone: str = "neutral") -> dict:
    return {"label": label, "value": value, "tone": tone}


def _market_cap_size_label(market_cap) -> tuple[str, str]:
    cap = to_float(market_cap)
    if cap is None:
        return "Market Cap N/A", "neutral"
    if cap >= 200_000_000_000:
        size = "Mega"
    elif cap >= 10_000_000_000:
        size = "Large"
    elif cap >= 2_000_000_000:
        size = "Mid"
    elif cap >= 300_000_000:
        size = "Small"
    else:
        size = "Micro"
    return f"{fmt_currency(cap, 1)} {size}", "good" if cap >= 2_000_000_000 else "neutral"


def _entry_signal_from_inputs(quote: dict, latest: dict, signal_output: dict) -> tuple[str, str]:
    price = to_float(quote.get("price"))
    range_pct = _range_position_pct(quote)
    tech = signal_output.get("technicals", {}) or {}
    score = 0
    inputs = 0
    if range_pct is not None:
        inputs += 1
        if range_pct < 65:
            score += 2
        elif range_pct < 85:
            score += 1
        elif range_pct > 90:
            score -= 2
    rsi = to_float(tech.get("rsi"))
    if rsi is not None:
        inputs += 1
        if rsi < 30:
            score += 2
        elif rsi <= 60:
            score += 1
        elif rsi > 70:
            score -= 2
    for key in ("sma50", "sma200"):
        avg = to_float(tech.get(key))
        if price is not None and avg is not None:
            inputs += 1
            score += 1 if price > avg else -1
    growth = _first_number(latest.get("revenue_yoy_growth"), latest.get("revenue_qoq_growth"))
    if growth is not None:
        inputs += 1
        score += 1 if growth > 0 else -1
    if inputs == 0:
        return "N/A", "neutral"
    if score >= 4:
        return "STRONG ENTRY", "good"
    if score >= 2:
        return "WATCHLIST ENTRY", "good"
    if score >= -1:
        return "NEUTRAL", "warn"
    if score >= -3:
        return "EXTENDED", "warn"
    return "WEAK SETUP", "bad"


def _stage_label(latest: dict, quote_data: dict, revenue_growth, fcf, net_income) -> tuple[str, str]:
    quote_type = str(quote_data.get("quote_type") or "").upper()
    if quote_type in {"ETF", "MUTUALFUND", "FUND"}:
        return "ETF / Fund", "neutral"
    if net_income is not None and net_income > 0 and (fcf is None or fcf >= 0):
        return "Profitable", "good"
    if revenue_growth is not None and revenue_growth > 20:
        return "Growth Stage", "good"
    if fcf is not None and fcf < 0:
        return "Scaling / Burn", "warn"
    return "Developing", "neutral"


def _momentum_label(signal_output: dict) -> tuple[str, str]:
    momentum = to_float(signal_output.get("momentum_score"))
    if momentum is None:
        return "Momentum N/A", "neutral"
    if momentum >= 65:
        return "Momentum Positive", "good"
    if momentum <= 40:
        return "Momentum Weak", "bad"
    return "Momentum Stable", "warn"


def _scenario_card(title: str, label: str, points: list[str], tone: str = "neutral") -> dict:
    clean_points = [point for point in points if point][:3] or ["Insufficient scenario inputs."]
    return {"title": title, "label": label, "points": clean_points, "tone": tone}


def build_company_header_view_model(
    ticker: str,
    quote_data: dict,
    company_identity: dict,
    financial_packet: dict,
    signal_output: dict,
    valuation_output: dict,
    technical_output: dict,
) -> dict:
    symbol = clean_ticker(ticker) or clean_ticker(quote_data.get("ticker")) or "N/A"
    latest = financial_packet.get("latest_financials") or {}
    release = financial_packet.get("latest_quarterly_release") or {}
    packet = financial_packet.get("financial_data_packet") or {}
    quality = packet.get("coverage_summary") or release.get("financial_data_quality") or {}
    revenue_growth = _first_number(latest.get("revenue_yoy_growth"), latest.get("revenue_qoq_growth"), release.get("revenue_yoy_growth"))
    gross_margin = _first_number(latest.get("gross_margin"), release.get("gross_margin"))
    net_income = _first_number(release.get("net_income"), latest.get("net_income"))
    fcf = _first_number(release.get("free_cash_flow"), latest.get("free_cash_flow"))
    range_pct = _range_position_pct(quote_data)
    valuation = valuation_output.get("valuation_label") or valuation_label(signal_output)
    completeness = _first_number(packet.get("completeness_score"), release.get("data_completeness_score"), signal_output.get("data_completeness"))
    signal_label = signal_output.get("signal_label") or "No Rating / Insufficient Data"
    stance, stance_tone = _stance_from_signal(signal_label)
    entry_signal, entry_tone = _entry_signal_from_inputs(quote_data, latest, signal_output)
    market_cap_label, market_cap_tone = _market_cap_size_label(quote_data.get("market_cap"))
    stage_label, stage_tone = _stage_label(latest, quote_data, revenue_growth, fcf, net_income)
    momentum_label, momentum_tone = _momentum_label(signal_output)

    positives: list[str] = []
    cautions: list[str] = []
    if revenue_growth is not None:
        if revenue_growth > 20:
            positives.append("strong revenue growth")
        elif revenue_growth > 0:
            positives.append("positive revenue growth")
        elif revenue_growth < 0:
            cautions.append("revenue contraction")
    if gross_margin is not None and gross_margin > 40:
        positives.append("healthy gross margins")
    if to_float(signal_output.get("momentum_score")) is not None:
        if to_float(signal_output.get("momentum_score")) >= 60:
            positives.append("constructive momentum")
        elif to_float(signal_output.get("momentum_score")) <= 40:
            cautions.append("weak momentum")
    if net_income is not None and net_income < 0:
        cautions.append("profitability remains negative")
    elif net_income is not None and net_income > 0:
        positives.append("profitable latest reported net income")
    if fcf is not None and fcf < 0:
        cautions.append("cash burn remains a watch item")
    elif fcf is not None and fcf > 0:
        positives.append("free cash flow is positive")
    if valuation in {"Expensive", "Very expensive"}:
        cautions.append("valuation remains elevated")
    elif valuation in {"Cheap", "Reasonable"}:
        positives.append(f"valuation appears {valuation.lower()}")
    if range_pct is not None and range_pct >= 80:
        cautions.append("trading near the top of its 52-week range")
    elif range_pct is not None and range_pct <= 20:
        cautions.append("trading near the bottom of its 52-week range")
    if completeness is not None and completeness < 75:
        cautions.append("data quality is partial")

    positives = list(dict.fromkeys(positives))
    cautions = list(dict.fromkeys(cautions))
    if completeness is not None and completeness < 40 and not positives:
        executive_summary = f"{symbol} has limited financial coverage. The research signal is based on available market, financial, and catalyst data."
    elif positives and cautions:
        executive_summary = f"{symbol} is showing {', '.join(positives[:2])}, but {', '.join(cautions[:2])}."
    elif positives:
        executive_summary = f"{symbol} is showing {', '.join(positives[:2])}. The overall research signal is {signal_label} based on available data."
    elif cautions:
        executive_summary = f"{symbol} has {', '.join(cautions[:2])}. The overall research signal is {signal_label} based on available data."
    else:
        executive_summary = f"{symbol} has partial financial coverage. The research signal is based on available market, financial, and catalyst data."

    quick_stats = [
        _hero_chip("Revenue Growth", fmt_growth(revenue_growth, abs(revenue_growth) > 500) if revenue_growth is not None else "N/A", tone_for_number(revenue_growth)),
        _hero_chip("FCF", fmt_currency(fcf, 1), tone_for_number(fcf)),
        _hero_chip("52W Position", f"{range_pct:.1f}%" if range_pct is not None else "N/A", "warn" if range_pct is not None and range_pct >= 80 else "neutral"),
        _hero_chip("Valuation", valuation or "N/A", "warn" if valuation in {"Expensive", "Very expensive"} else "good" if valuation in {"Cheap", "Reasonable"} else "neutral"),
        _hero_chip("Completeness", _fmt_completeness(completeness), "warn" if completeness is not None and completeness < 75 else "good" if completeness is not None and completeness >= 90 else "neutral"),
    ]

    bear_risks = []
    if valuation in {"Expensive", "Very expensive"}:
        bear_risks.append("valuation remains elevated")
    if fcf is not None and fcf < 0:
        bear_risks.append("negative free cash flow")
    if net_income is not None and net_income < 0:
        bear_risks.append("profitability not yet established")
    if revenue_growth is not None and revenue_growth < 0:
        bear_risks.append("revenue contraction")
    if to_float(signal_output.get("momentum_score")) is not None and to_float(signal_output.get("momentum_score")) < 40:
        bear_risks.append("negative momentum")
    if completeness is not None and completeness < 75:
        bear_risks.append("partial data coverage")
    risk_label = "Elevated" if len(bear_risks) >= 3 else "Moderate" if bear_risks else "Low"

    bull_drivers = []
    if revenue_growth is not None and revenue_growth > 0:
        bull_drivers.append("revenue growth")
    if gross_margin is not None and gross_margin > 30:
        bull_drivers.append("margin potential")
    if fcf is not None and fcf > 0:
        bull_drivers.append("positive free cash flow")
    if to_float(signal_output.get("momentum_score")) is not None and to_float(signal_output.get("momentum_score")) >= 60:
        bull_drivers.append("strong momentum")
    for item in signal_output.get("strengths", [])[:2]:
        if item and item not in bull_drivers:
            bull_drivers.append(str(item))
    upside_label = "Strong" if len(bull_drivers) >= 3 else "Moderate" if bull_drivers else "Limited"

    score = to_float(signal_output.get("composite_score"))
    return {
        "ticker": symbol,
        "company_name": company_identity.get("company_name") or quote_data.get("company_name") or symbol,
        "sector": company_identity.get("sector") or quote_data.get("sector") or "N/A",
        "industry": company_identity.get("industry") or quote_data.get("industry") or "N/A",
        "price": quote_data.get("price"),
        "daily_move_pct": quote_data.get("daily_change_pct"),
        "daily_change_amount": quote_data.get("daily_change"),
        "market_cap_label": market_cap_label,
        "market_cap_tone": market_cap_tone,
        "stage_label": stage_label,
        "stage_tone": stage_tone,
        "momentum_label": momentum_label,
        "momentum_tone": momentum_tone,
        "entry_signal": entry_signal,
        "entry_tone": entry_tone,
        "overall_research_signal": signal_label,
        "overall_tone": _signal_tone(signal_label),
        "market_stance": stance,
        "market_stance_tone": stance_tone,
        "composite_score": score,
        "confidence": signal_output.get("confidence") or "N/A",
        "data_completeness": completeness,
        "expected_value": "N/A",
        "executive_summary": executive_summary,
        "quick_stats": quick_stats,
        "classification_chips": [
            _hero_chip(str(company_identity.get("sector") or quote_data.get("sector") or "N/A"), "", "neutral"),
            _hero_chip(market_cap_label, "", market_cap_tone),
            _hero_chip(stage_label, "", stage_tone),
            _hero_chip(momentum_label, "", momentum_tone),
        ],
        "bear_case": _scenario_card("Bear Case", f"Risk skew: {risk_label}", bear_risks, "bad" if risk_label == "Elevated" else "warn" if risk_label == "Moderate" else "neutral"),
        "base_case": _scenario_card("Base Case", f"Current view: {signal_label}", [f"Score: {score:.1f}/100" if score is not None else "Score: N/A", f"Confidence: {signal_output.get('confidence') or 'N/A'}", f"Valuation: {valuation or 'N/A'}"], stance_tone),
        "bull_case": _scenario_card("Bull Case", f"Upside drivers: {upside_label}", bull_drivers, "good" if upside_label in {"Strong", "Moderate"} else "neutral"),
        "source_status": financial_packet.get("status") or packet.get("source_status") or "N/A",
        "last_updated": financial_packet.get("last_updated") or quote_data.get("last_updated"),
    }


def _chip_html(chip: dict, css_class: str = "terminal-chip") -> str:
    value = str(chip.get("value") or "")
    value_html = f': <strong>{escape(value)}</strong>' if value else ""
    return f'<span class="{css_class} {escape(str(chip.get("tone") or "neutral"))}">{escape(str(chip.get("label") or "N/A"))}{value_html}</span>\n'


def _scenario_html(case: dict) -> str:
    points = "".join(f"<li>{escape(str(point))}</li>" for point in case.get("points", []))
    return (
        f'<div class="scenario-card {escape(str(case.get("tone") or "neutral"))}">'
        f'<div class="scenario-title">{escape(str(case.get("title") or "Scenario"))}</div>'
        f'<div class="scenario-label">{escape(str(case.get("label") or "N/A"))}</div>'
        f"<ul>{points}</ul>"
        "</div>"
    )


def _pt_tone_style(tone: str) -> dict:
    palette = {
        "good": {"color": BRAND_COLORS["pine_bright"], "border": "rgba(109,187,90,0.45)", "bg": "rgba(109,187,90,0.12)"},
        "warn": {"color": BRAND_COLORS["gold"], "border": "rgba(229,167,42,0.45)", "bg": "rgba(229,167,42,0.12)"},
        "bad": {"color": BRAND_COLORS["red"], "border": "rgba(229,115,104,0.45)", "bg": "rgba(229,115,104,0.12)"},
        "neutral": {"color": BRAND_COLORS["text_secondary"], "border": "rgba(30,52,64,0.95)", "bg": "rgba(123,199,232,0.08)"},
    }
    return palette.get(tone, palette["neutral"])


def _pt_chip(chip: dict, css_class: str = "pt-chip") -> str:
    tone = _pt_tone_style(str(chip.get("tone") or "neutral"))
    value = str(chip.get("value") or "")
    value_html = f'<span style="color:{BRAND_COLORS["text"]};margin-left:0.25rem;">{escape(value)}</span>' if value else ""
    return (
        f'<span class="{escape(css_class)}" style="display:inline-flex;align-items:center;gap:0.1rem;'
        f'border:1px solid {tone["border"]};background:{tone["bg"]};color:{tone["color"]};'
        f'border-radius:999px;padding:0.26rem 0.6rem;font-size:0.72rem;font-weight:900;'
        f'line-height:1.1;text-transform:uppercase;white-space:nowrap;">'
        f'{escape(str(chip.get("label") or "N/A"))}{value_html}</span>'
    )


def _pt_stat_card(label: str, value: str, tone: str = "neutral") -> str:
    tone_style = _pt_tone_style(tone)
    return (
        f'<div class="pt-hero-meta" style="border:1px solid {BRAND_COLORS["border"]};'
        f'border-radius:10px;background:{BRAND_COLORS["card_alt"]};padding:0.5rem 0.58rem;min-width:0;">'
        f'<div style="color:{BRAND_COLORS["muted"]};font-size:0.66rem;font-weight:850;'
        f'letter-spacing:0.04em;text-transform:uppercase;margin-bottom:0.18rem;">{escape(label)}</div>'
        f'<div style="color:{tone_style["color"]};font-size:0.92rem;font-weight:930;'
        f'line-height:1.15;overflow-wrap:anywhere;">{escape(str(value or "N/A"))}</div>'
        "</div>"
    )


def _pt_signal_badge(label: str, value: str, tone: str = "neutral") -> str:
    tone_style = _pt_tone_style(tone)
    return (
        f'<div class="pt-signal-badge" style="border:1px solid {tone_style["border"]};'
        f'background:{tone_style["bg"]};border-radius:12px;padding:0.54rem 0.65rem;margin-top:0.5rem;">'
        f'<div style="color:{BRAND_COLORS["muted"]};font-size:0.66rem;font-weight:850;'
        f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.16rem;">{escape(label)}</div>'
        f'<div style="color:{tone_style["color"]};font-size:0.98rem;font-weight:940;'
        f'line-height:1.15;overflow-wrap:anywhere;">{escape(str(value or "N/A"))}</div>'
        "</div>"
    )


def _pt_case_card(case: dict) -> str:
    tone = _pt_tone_style(str(case.get("tone") or "neutral"))
    points = "".join(f'<li style="margin-bottom:0.18rem;">{escape(str(point))}</li>' for point in case.get("points", [])[:3])
    return (
        f'<div class="pt-case-card pt-{escape(str(case.get("tone") or "base"))}" style="border:1px solid {tone["border"]};'
        f'background:{BRAND_COLORS["card_alt"]};border-radius:14px;padding:0.86rem 0.9rem;min-width:0;">'
        f'<div style="color:{BRAND_COLORS["muted"]};font-size:0.72rem;font-weight:920;'
        f'letter-spacing:0.05em;text-transform:uppercase;">{escape(str(case.get("title") or "Scenario"))}</div>'
        f'<div style="color:{tone["color"]};font-size:1rem;font-weight:950;line-height:1.18;'
        f'margin-top:0.28rem;">{escape(str(case.get("label") or "N/A"))}</div>'
        f'<ul style="color:{BRAND_COLORS["text_secondary"]};font-size:0.82rem;line-height:1.35;'
        f'margin:0.58rem 0 0 1rem;padding:0;">{points}</ul>'
        "</div>"
    )


def render_terminal_company_hero(view_model: dict) -> None:
    ticker = view_model.get("ticker") or "N/A"
    score = to_float(view_model.get("composite_score"))
    score_text = f"{score:.1f}" if score is not None else "N/A"
    score_caption = f"Composite: {score:.1f} / 100" if score is not None else "Composite: N/A"
    move = view_model.get("daily_move_pct")
    move_amount = to_float(view_model.get("daily_change_amount"))
    move_text = fmt_percent(move, decimals=2, signed=True) if move is not None else "N/A"
    move_tone = {"good": "good", "bad": "bad"}.get(tone_for_number(move), "neutral")
    change_abs = f"{'+' if move_amount > 0 else '-' if move_amount < 0 else ''}{fmt_price(abs(move_amount))}" if move_amount is not None else "N/A"
    move_style = _pt_tone_style(move_tone)
    score_tone = _pt_tone_style(str(view_model.get("overall_tone") or "neutral"))
    classification = "".join(_pt_chip(chip) for chip in view_model.get("classification_chips", []))
    quick_stats = "".join(
        _pt_stat_card(str(chip.get("label") or "N/A"), str(chip.get("value") or "N/A"), str(chip.get("tone") or "neutral"))
        for chip in view_model.get("quick_stats", [])
    )
    scenarios = "".join(_pt_case_card(view_model.get(key, {})) for key in ("bear_case", "base_case", "bull_case"))
    score_meta = "".join(
        [
            _pt_stat_card("Data Confidence", _fmt_completeness(view_model.get("data_completeness")), "warn" if to_float(view_model.get("data_completeness")) is not None and to_float(view_model.get("data_completeness")) < 75 else "good"),
            _pt_stat_card("Confidence", str(view_model.get("confidence") or "N/A"), "neutral"),
            _pt_stat_card("Expected Value", str(view_model.get("expected_value") or "N/A"), "neutral"),
            _pt_stat_card("Market Stance", str(view_model.get("market_stance") or "N/A"), str(view_model.get("market_stance_tone") or "neutral")),
        ]
    )
    st.markdown(
        f"""
        <div class="pt-hero-card" style="background:linear-gradient(135deg,{BRAND_COLORS["card"]},#0B141A);border:1px solid {BRAND_COLORS["border"]};border-radius:16px;padding:1.1rem 1.15rem;box-shadow:0 18px 34px rgba(0,0,0,0.24);">
          <div class="pt-hero-grid" style="display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,0.82fr);gap:1.25rem;align-items:stretch;">
            <div class="pt-company-left" style="min-width:0;">
              <div style="display:flex;align-items:baseline;gap:0.85rem;flex-wrap:wrap;">
                <div class="pt-ticker" style="color:{BRAND_COLORS["text"]};font-size:clamp(2.8rem,5vw,4.9rem);line-height:0.92;font-weight:980;letter-spacing:0.02em;">{escape(str(ticker))}</div>
                <span style="border:1px solid {move_style["border"]};background:{move_style["bg"]};color:{move_style["color"]};border-radius:999px;padding:0.22rem 0.6rem;font-size:0.86rem;font-weight:940;">{escape(move_text)}</span>
              </div>
              <div class="pt-company-name" style="color:{BRAND_COLORS["text"]};font-size:1.2rem;font-weight:860;margin-top:0.42rem;overflow-wrap:anywhere;">{escape(str(view_model.get("company_name") or ticker))}</div>
              <div class="pt-chip-row" style="display:flex;flex-wrap:wrap;gap:0.48rem;margin-top:0.85rem;">{classification}</div>
              <div style="color:{BRAND_COLORS["text_secondary"]};font-size:0.94rem;font-weight:780;margin-top:0.68rem;">{escape(str(view_model.get("sector") or "N/A"))} - {escape(str(view_model.get("industry") or "N/A"))}</div>
              <div style="color:{BRAND_COLORS["text"]};font-size:1.05rem;font-weight:850;margin-top:0.55rem;">{escape(fmt_price(view_model.get("price")))} <span style="color:{BRAND_COLORS["muted"]};margin-left:0.35rem;">{escape(change_abs)}</span></div>
              <div style="color:{BRAND_COLORS["text_secondary"]};font-size:0.92rem;font-weight:800;margin-top:0.65rem;">Entry Signal: {_pt_chip({"label": view_model.get("entry_signal") or "N/A", "value": "", "tone": view_model.get("entry_tone") or "neutral"}, "pt-entry-signal")}</div>
            </div>
            <div class="pt-score-right" style="border:1px solid {score_tone["border"]};background:radial-gradient(circle at top right,{score_tone["bg"]},transparent 46%),{BRAND_COLORS["card_alt"]};border-radius:15px;padding:1rem;display:flex;flex-direction:column;justify-content:center;min-width:0;">
              <div class="pt-big-score" style="color:{BRAND_COLORS["text"]};font-size:clamp(3.2rem,6vw,5.4rem);line-height:0.9;font-weight:980;letter-spacing:-0.02em;">{escape(score_text)}</div>
              <div class="pt-signal-badge" style="color:{score_tone["color"]};font-size:1.18rem;font-weight:950;margin-top:0.48rem;">{escape(str(view_model.get("overall_research_signal") or "N/A"))}</div>
              <div style="color:{BRAND_COLORS["text_secondary"]};font-size:0.84rem;font-weight:850;margin-top:0.25rem;">{escape(score_caption)}</div>
              <div class="pt-score-meta-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.48rem;margin-top:0.9rem;">
                {score_meta}
              </div>
            </div>
          </div>
          <div class="pt-quick-stat-row" style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0.58rem;margin-top:1rem;">{quick_stats}</div>
        </div>
        <div class="pt-scenario-card" style="background:linear-gradient(135deg,{BRAND_COLORS["card"]},#0B141A);border:1px solid {BRAND_COLORS["border"]};border-radius:16px;padding:1rem 1.1rem;margin-top:0.9rem;box-shadow:0 18px 34px rgba(0,0,0,0.2);">
          <div class="pt-exec-summary" style="border-bottom:1px solid {BRAND_COLORS["border"]};padding-bottom:0.82rem;margin-bottom:0.86rem;">
            <div style="color:{BRAND_COLORS["muted"]};font-size:0.72rem;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;">Executive Summary</div>
            <div style="color:{BRAND_COLORS["text"]};font-size:1.04rem;font-weight:830;line-height:1.34;margin-top:0.28rem;overflow-wrap:anywhere;">{escape(str(view_model.get("executive_summary") or "Insufficient data to generate a reliable summary."))}</div>
          </div>
          <div style="color:{BRAND_COLORS["text"]};font-size:0.96rem;font-weight:950;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:0.6rem;">Research Scenario Snapshot</div>
          <div class="pt-scenario-grid" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0.72rem;">{scenarios}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_company_hero(view_model: dict) -> None:
    render_terminal_company_hero(view_model)


def render_signal_summary(ticker: str, signal: dict) -> None:
    label = signal.get("signal_label", "N/A")
    score = signal.get("composite_score", 0)
    confidence = signal.get("confidence", "Low")
    tone = "good" if "Buy" in label else "bad" if label in {"Avoid", "Sell / Trim"} else "neutral"
    render_metric_grid(
        [
            ("Composite Score", f"{score:.1f}/100" if isinstance(score, (int, float)) else "N/A", "Transparent factor model", tone_for_number(score)),
            ("Overall Research Signal", label, "Full research signal based on growth, profitability, balance sheet, valuation, momentum, catalysts, and data quality.", tone),
            ("Confidence", confidence, f"{signal.get('data_completeness', 'N/A')}% weighted data completeness", "good" if confidence == "High" else "warn" if confidence == "Medium" else "neutral"),
            ("Missing Data Warnings", str(len(signal.get("missing_data_warnings", []))), signal.get("data_quality_note", ""), "warn" if signal.get("missing_data_warnings") else "good"),
        ],
        columns=4,
        small=True,
    )
    score_frame = pd.DataFrame(
        [
            ("Growth", signal.get("growth_score")),
            ("Profitability / Margins", signal.get("profitability_score")),
            ("Balance Sheet / Liquidity", signal.get("balance_sheet_score")),
            ("Valuation", signal.get("valuation_score")),
            ("Momentum / Technicals", signal.get("momentum_score")),
            ("Catalysts / News", signal.get("catalyst_score")),
        ],
        columns=["Category", "Score"],
    )
    fig = go.Figure(go.Bar(x=score_frame["Category"], y=score_frame["Score"], marker_color=BRAND_COLORS["pine_bright"], text=score_frame["Score"].round(1), textposition="outside", cliponaxis=False))
    fig = plotly_layout(fig, height=330)
    fig.update_yaxes(range=[0, 105], title="Score")
    render_terminal_chart(fig)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Strengths")
        for item in signal.get("strengths", []):
            st.success(item)
        st.markdown("#### Upgrade Triggers")
        for item in signal.get("upgrade_triggers", []):
            st.write(f"- {item}")
    with col2:
        st.markdown("#### Weaknesses")
        for item in signal.get("weaknesses", []):
            st.warning(item)
        st.markdown("#### Downgrade Triggers")
        for item in signal.get("downgrade_triggers", []):
            st.write(f"- {item}")


def options_monitor_frame(tickers: list[str]) -> pd.DataFrame:
    rows = []
    for symbol in tickers:
        quote = fetch_quote(symbol)
        opts = fetch_options_summary(symbol, quote.get("price"))
        seven = opts.get("seven_day", {})
        thirty = opts.get("thirty_day", {})
        rows.append(
            {
                "Ticker": symbol,
                "Last Price": fmt_price(quote.get("price")),
                "7D Implied Move": "+/-" + fmt_percent(seven.get("implied_move_pct")) if seven.get("implied_move_pct") is not None else "N/A",
                "7D IV": fmt_percent(seven.get("annual_iv")),
                "7D Expiry Used": fmt_date(seven.get("expiry")),
                "30D Implied Move": "+/-" + fmt_percent(thirty.get("implied_move_pct")) if thirty.get("implied_move_pct") is not None else "N/A",
                "30D IV": fmt_percent(thirty.get("annual_iv")),
                "30D Expiry Used": fmt_date(thirty.get("expiry")),
                "Options Status": opts.get("status", "N/A"),
            }
        )
    return pd.DataFrame(rows)


def _format_movers_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    display = frame.copy()
    if "Price" in display:
        display["Price"] = display["Price"].map(fmt_price)
    if "Daily Move %" in display:
        display["Daily Move %"] = display["Daily Move %"].map(lambda value: fmt_percent(value, decimals=2, signed=True))
    if "Volume" in display:
        display["Volume"] = display["Volume"].map(fmt_compact)
    if "Relative Volume" in display:
        display["Relative Volume"] = display["Relative Volume"].map(lambda value: fmt_multiple(value) if to_float(value) is not None else "N/A")
    if "Market Cap" in display:
        display["Market Cap"] = display["Market Cap"].map(lambda value: fmt_compact(value, prefix="$"))
    return display


def _social_display_frame(frame: pd.DataFrame, watchlist_tickers: set[str]) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    display = frame.copy()
    display["Watchlist Status"] = display["Ticker"].map(lambda value: "In Watchlist" if clean_ticker(value) in watchlist_tickers else "Candidate")
    if "Price" in display:
        display["Price"] = display["Price"].map(fmt_price)
    if "Daily Move %" in display:
        display["Daily Move %"] = display["Daily Move %"].map(lambda value: fmt_percent(value, decimals=2, signed=True))
    if "Message Volume" in display:
        display["Message Volume"] = display["Message Volume"].map(fmt_compact)
    return display


def _watchlist_symbols() -> list[str]:
    watch = list_watchlist()
    return [clean_ticker(value) for value in watch.get("ticker", pd.Series(dtype=str)).tolist() if clean_ticker(value)]


def render_52w_position(quote: dict) -> None:
    price = to_float(quote.get("price"))
    low = to_float(quote.get("fifty_two_week_low"))
    high = to_float(quote.get("fifty_two_week_high"))
    ticker = quote.get("ticker", "")
    if price is None or low is None or high is None or high <= low:
        st.info("52W range data unavailable.")
        return
    pos = max(0, min((price - low) / (high - low), 1))
    pct = pos * 100
    midpoint = (low + high) / 2
    if pct < 8:
        transform = "translateX(0)"
        label_left = "0%"
        text_align = "left"
    elif pct > 92:
        transform = "translateX(-100%)"
        label_left = "100%"
        text_align = "right"
    else:
        transform = "translateX(-50%)"
        label_left = f"{pct:.2f}%"
        text_align = "center"
    st.markdown(
        f"""
        <div class="rt-card" style="min-height:148px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem;">
            <div class="rt-label">52W Price Position</div>
            <div class="rt-label">{pct:.1f}% of Range</div>
          </div>
          <div style="position:relative;height:56px;margin:0.25rem 0 0.1rem;">
            <div style="position:absolute;left:{label_left};top:0;transform:{transform};text-align:{text_align};white-space:nowrap;">
              <span class="rt-badge good">{ticker} {fmt_price(price)}</span>
            </div>
            <div style="position:absolute;left:0;right:0;top:30px;height:10px;border-radius:99px;background:linear-gradient(90deg,{BRAND_COLORS['red']},{BRAND_COLORS['gold']},{BRAND_COLORS['pine_bright']});border:1px solid {BRAND_COLORS['border']};"></div>
            <div style="position:absolute;left:{pct:.2f}%;top:24px;transform:translateX(-50%);width:3px;height:24px;border-radius:4px;background:#e8f2f4;box-shadow:0 0 0 2px rgba(0,0,0,0.45);"></div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;margin-top:0.35rem;color:#9fb0b6;font-weight:800;font-size:0.78rem;">
            <div>52W Low<br><span style="color:#dfe8eb;">{fmt_price(low)}</span></div>
            <div style="text-align:center;">Midpoint<br><span style="color:#dfe8eb;">{fmt_price(midpoint)}</span></div>
            <div style="text-align:right;">52W High<br><span style="color:#dfe8eb;">{fmt_price(high)}</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_entry_signal(ticker: str, quote: dict, latest: dict, options: dict, signal: dict) -> None:
    price = to_float(quote.get("price"))
    low = to_float(quote.get("fifty_two_week_low"))
    high = to_float(quote.get("fifty_two_week_high"))
    range_position = safe_div(price - low, high - low, 1) if price is not None and low is not None and high not in (None, low) else None
    tech = signal.get("technicals", {})
    score = 0
    reasons = []
    if range_position is not None:
        if range_position < 0.65:
            score += 2
            reasons.append("not overly extended in the 52W range")
        elif range_position < 0.85:
            score += 1
            reasons.append("mid-to-upper part of its 52W range")
        elif range_position > 0.90:
            score -= 2
            reasons.append("near the top of its 52W range")
    rsi = to_float(tech.get("rsi"))
    if rsi is not None:
        if rsi < 30:
            score += 2
            reasons.append("RSI is oversold")
        elif rsi <= 60:
            score += 1
            reasons.append("RSI is not overbought")
        elif rsi > 70:
            score -= 2
            reasons.append("RSI is elevated")
    for label, key in (("50D average", "sma50"), ("200D average", "sma200")):
        avg = to_float(tech.get(key))
        if price is not None and avg is not None:
            score += 1 if price > avg else -1
            reasons.append(f"price is {'above' if price > avg else 'below'} the {label}")
    if to_float(latest.get("revenue_yoy_growth") or latest.get("revenue_qoq_growth")) is not None:
        score += 1 if to_float(latest.get("revenue_yoy_growth") or latest.get("revenue_qoq_growth")) > 0 else -1
    if score >= 4:
        label, tone = "Strong Entry", "good"
    elif score >= 2:
        label, tone = "Watchlist Entry", "good"
    elif score >= -1:
        label, tone = "Neutral / Mixed Setup", "neutral"
    elif score >= -3:
        label, tone = "Stretched / Wait for Pullback", "warn"
    else:
        label, tone = "Avoid / Weak Setup", "bad"
    if range_position is None and rsi is None:
        label, tone = "Insufficient Data", "neutral"
    rationale = f"{ticker} setup quality is driven by " + ", ".join(reasons[:3]) + "." if reasons else "Insufficient market and financial inputs are available."
    render_metric_grid(
        [
            ("Technical Entry Setup", label, "Technical setup signal based on momentum, moving averages, RSI, and 52-week positioning. Not a standalone buy/sell rating.", tone),
            ("Rationale", rationale, f"Signal score input: {score}", "neutral"),
        ],
        columns=2,
    )
    st.caption(
        "Technical Entry Setup reflects timing quality. Overall Research Signal reflects the broader investment profile. "
        "A stock can have a strong entry setup while still remaining Hold / Watchlist if valuation, profitability, or data quality are not supportive."
    )


def render_latest_earnings(financials: dict) -> None:
    earnings = financials.get("latest_reported_earnings", {}) or {}
    if not earnings:
        st.info("Latest quarterly earnings data unavailable for this ticker.")
        return
    eps_actual = to_float(earnings.get("eps_actual"))
    eps_estimate = to_float(earnings.get("eps_estimate"))
    eps_surprise = eps_actual - eps_estimate if eps_actual is not None and eps_estimate is not None else None
    eps_surprise_pct = safe_div(eps_surprise, abs(eps_estimate), 100) if eps_surprise is not None and eps_estimate not in (None, 0) else earnings.get("eps_surprise_pct")
    revenue_actual = earnings.get("revenue_actual")
    cards = [
        ("Announce Date", fmt_date(earnings.get("earnings_date")), earnings.get("fiscal_period") or earnings.get("period") or "Latest reported quarter", "neutral"),
        ("Revenue Actual", fmt_currency(revenue_actual, 1), "Quarterly actual, when available", "neutral"),
        ("EPS Actual", fmt_eps(eps_actual), "Reported EPS", tone_for_number(eps_actual)),
        ("EPS Estimate", fmt_eps(eps_estimate), "Consensus estimate, if available", "neutral"),
        ("EPS Surprise", f"{fmt_eps(eps_surprise, signed=True)} / {fmt_percent(eps_surprise_pct, signed=True)}", "Beat/miss from reported EPS", tone_for_number(eps_surprise)),
        ("Source", earnings.get("source", "Yahoo Finance/yfinance"), "Daily cached V1 feed", "neutral"),
    ]
    render_metric_grid(cards, columns=3, small=True)


def render_latest_quarterly_release(financials: dict) -> None:
    release = financials.get("latest_quarterly_release") or {}
    packet = financials.get("financial_data_packet") or {}
    if not release:
        st.info("Latest quarterly release data unavailable for this ticker.")
        return
    status = packet.get("source_status") or release.get("source_status", "N/A")
    tone = (
        "good"
        if status in {"OK", "Complete", "Mostly complete"}
        else "warn"
        if status in {"Partial", "Limited", "Not applicable", "Stale structured values", "Filing metadata only", "Structured values only"}
        else "neutral"
        if status in {"Insufficient data", "Missing"}
        else "bad"
    )
    reported_period = str(release.get("reported_period_label") or release.get("period_label") or "N/A")
    structured_period = release.get("structured_values_period_label")
    show_structured_period = bool(structured_period and structured_period != reported_period and structured_period != "N/A")
    structured_source = release.get("structured_values_source") or "Yahoo Finance quarterly statements"
    cards = [
        ("Reported Period", reported_period, f"Form: {release.get('form_type') or 'N/A'}", "neutral"),
        ("Period End Date", fmt_date(release.get("period_end_date")), release.get("period_alignment_status", ""), "neutral"),
        ("Release / Filing Date", fmt_date(release.get("filing_date") or release.get("filing_or_release_date")), release.get("source", "N/A"), "neutral"),
    ]
    if show_structured_period:
        cards.append(("Structured Values Period", str(structured_period), structured_source, "warn"))
    value_period_caption = structured_source if not show_structured_period else f"{structured_source}; period: {structured_period}"
    cards.extend(
        [
            ("Revenue", fmt_currency(release.get("revenue"), 1), value_period_caption, "neutral"),
            ("EPS", fmt_eps(release.get("eps")), "N/A if unavailable", tone_for_number(release.get("eps"))),
            ("Net Income", fmt_currency(release.get("net_income"), 1), value_period_caption, tone_for_number(release.get("net_income"))),
            ("Free Cash Flow", fmt_currency(release.get("free_cash_flow"), 1), "OCF less normalized capex", tone_for_number(release.get("free_cash_flow"))),
            ("Cash", fmt_currency(release.get("cash"), 1), "Nearest matching balance sheet", "neutral"),
            ("Total Debt", fmt_currency(release.get("total_debt"), 1), "Nearest matching balance sheet", "neutral"),
            ("Source Status", status, packet.get("data_quality_note") or release.get("compact_source_status_note") or release.get("period_alignment_status") or "Review reconciliation.", tone),
            ("Data Completeness", _fmt_completeness(packet.get("completeness_score", release.get("data_completeness_score"))), packet.get("data_quality_note") or release.get("compact_source_status_note") or "Latest-period core fields", tone),
        ]
    )
    render_metric_grid(cards, columns=3, small=True)
    if show_structured_period or release.get("period_alignment_status") == "Filing newer than structured values":
        st.warning(release.get("data_quality_note") or f"Latest filing detected for {reported_period}; structured financial values may still reflect {structured_period}.")
    filing_url = release.get("filing_url")
    if filing_url:
        st.link_button("Open filing", filing_url)


def _reconciliation_display_value(metric: str, value) -> str:
    if metric == "eps":
        return fmt_eps(value)
    if metric == "shares_outstanding":
        return fmt_compact(value)
    return fmt_currency(value, 1)


def render_financial_reconciliation(financials: dict) -> None:
    reconciliation = financials.get("reconciliation") or {}
    packet = financials.get("financial_data_packet") or {}
    if reconciliation.get("has_mismatch"):
        st.warning("Financial period mismatch detected. Review reconciliation details.")
    with st.expander("Financial Data Reconciliation"):
        quality = packet.get("coverage_summary") or reconciliation.get("data_quality") or (financials.get("latest_quarterly_release") or {}).get("financial_data_quality") or {}
        if quality:
            render_metric_grid(
                [
                    ("Source Status", packet.get("source_status") or quality.get("source_status", "N/A"), packet.get("data_quality_note") or "Canonical financial packet", _status_tone(packet.get("source_status") or quality.get("source_status", ""))),
                    ("Data Completeness", _fmt_completeness(quality.get("completeness_score")), f"{quality.get('available_count', 0)} of {quality.get('required_count', 0)} core fields available", "good" if (quality.get("completeness_score") or 0) >= 75 else "warn" if (quality.get("completeness_score") or 0) >= 25 else "bad"),
                    ("Found Directly", str(quality.get("direct_count", 0)), ", ".join(quality.get("found_direct", []) or ["N/A"]), "good"),
                    ("Fallback", str(quality.get("fallback_count", 0)), ", ".join(quality.get("fallback", []) or ["N/A"]), "warn" if quality.get("fallback_count", 0) else "neutral"),
                    ("Calculated", str(quality.get("calculated_count", 0)), ", ".join(quality.get("calculated", []) or ["N/A"]), "neutral"),
                    ("Estimated / Partial", str(quality.get("estimated_count", 0)), ", ".join(quality.get("estimated", []) or ["N/A"]), "warn" if quality.get("estimated_count", 0) else "neutral"),
                    ("Missing", str(quality.get("missing_count", 0)), ", ".join(quality.get("missing", []) or ["N/A"]), "bad" if quality.get("missing_count", 0) else "good"),
                ],
                columns=3,
                small=True,
            )
            coverage_rows = [
                {"Category": "Direct", "Fields": ", ".join(quality.get("found_direct", []) or ["N/A"])},
                {"Category": "Fallback", "Fields": ", ".join(quality.get("fallback", []) or ["N/A"])},
                {"Category": "Calculated", "Fields": ", ".join(quality.get("calculated", []) or ["N/A"])},
                {"Category": "Estimated / Partial", "Fields": ", ".join(quality.get("estimated", []) or ["N/A"])},
                {"Category": "Missing", "Fields": ", ".join(quality.get("missing", []) or ["N/A"])},
                {"Category": "Not applicable", "Fields": ", ".join(quality.get("not_applicable", []) or ["N/A"])},
            ]
            st.markdown("#### Field Coverage Summary")
            df_display(pd.DataFrame(coverage_rows), height=250)
        rows = reconciliation.get("rows") or []
        if rows:
            display_rows = []
            for row in rows:
                display_rows.append(
                    {
                        "Metric": row.get("Metric"),
                        "Displayed Value": _reconciliation_display_value(row.get("metric"), row.get("value")),
                        "Status": row.get("Status"),
                        "Provider": row.get("Provider"),
                        "Source": row.get("Source"),
                        "SEC Concept Used": row.get("SEC Concept Used"),
                        "Component Concepts Used": row.get("Component Concepts Used"),
                        "Calculation Formula": row.get("Calculation Formula"),
                        "Period": row.get("Period"),
                        "Period End Date": row.get("Period End Date"),
                        "Fallback Used": row.get("Fallback Used"),
                        "Fallback Source": row.get("Fallback Source"),
                        "SEC Concepts Attempted": row.get("Concepts Attempted"),
                        "Form": row.get("Form"),
                        "Filed Date": row.get("Filed Date"),
                        "Accession": row.get("Accession"),
                        "Note": row.get("Note") or row.get("Missing / Note"),
                    }
                )
            df_display(pd.DataFrame(display_rows), height=420)
        else:
            empty_state("No financial reconciliation rows available.")
        checks = reconciliation.get("checks") or []
        if checks:
            st.markdown("#### Consistency Checks")
            df_display(pd.DataFrame(checks), height=220)
        missing_chart = reconciliation.get("missing_chart_fields") or []
        if missing_chart:
            st.info("Some chart periods have missing values: " + "; ".join(missing_chart))
        margin_notes = reconciliation.get("margin_notes") or []
        if margin_notes:
            st.caption("Margin validation: " + " ".join(margin_notes))


def render_price_chart(ticker: str) -> None:
    history = fetch_history(ticker, "1y", "1d")
    if history.empty or "Close" not in history:
        empty_state("Price history unavailable.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close", line={"color": BRAND_COLORS["pine_bright"], "width": 2.4}))
    fig = plotly_layout(fig, height=320)
    fig.update_yaxes(title="Price")
    render_terminal_chart(fig)


def render_financial_charts(history: pd.DataFrame, view: str, chart_source: dict | None = None) -> None:
    if history.empty:
        empty_state(f"{view} financial statement data unavailable.")
        return
    chart_frame = history.tail(8).copy()
    if chart_source:
        st.caption(f"Chart source: {chart_source.get('label', 'N/A')} | Status: {chart_source.get('status', 'N/A')} | {chart_source.get('note', '')}")
    col1, col2 = st.columns(2)
    with col1:
        if "revenue" in chart_frame and chart_frame["revenue"].notna().any():
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=chart_frame["period"],
                    y=chart_frame["revenue"],
                    name="Actual Revenue",
                    marker_color=BRAND_COLORS["pine_bright"],
                    text=[fmt_currency(v, 1) for v in chart_frame["revenue"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig = plotly_layout(fig, height=340)
            fig.update_yaxes(title="Revenue")
            render_terminal_chart(fig)
        else:
            empty_state("Revenue history unavailable.")
    with col2:
        if "eps" in chart_frame and chart_frame["eps"].notna().any():
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=chart_frame["period"],
                    y=chart_frame["eps"],
                    name="Actual EPS",
                    marker_color=[BRAND_COLORS["pine_bright"] if to_float(v) is not None and to_float(v) >= 0 else BRAND_COLORS["red"] for v in chart_frame["eps"]],
                    text=[fmt_eps(v) for v in chart_frame["eps"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig = plotly_layout(fig, height=340)
            fig.update_yaxes(title="EPS")
            render_terminal_chart(fig)
        else:
            empty_state("EPS history unavailable.")
    margin_cols = ["gross_margin", "operating_margin", "net_margin", "fcf_margin"]
    if any(col in chart_frame and chart_frame[col].notna().any() for col in margin_cols):
        fig = go.Figure()
        colors = {"gross_margin": BRAND_COLORS["pine_bright"], "operating_margin": BRAND_COLORS["gold"], "net_margin": BRAND_COLORS["pine"], "fcf_margin": BRAND_COLORS["warning"]}
        labels = {"gross_margin": "Gross Margin", "operating_margin": "Operating Margin", "net_margin": "Net Margin", "fcf_margin": "FCF Margin"}
        for col in margin_cols:
            if col in chart_frame and chart_frame[col].notna().any():
                fig.add_trace(go.Scatter(x=chart_frame["period"], y=chart_frame[col], mode="lines+markers", name=labels[col], line={"color": colors[col]}))
        fig = plotly_layout(fig, height=340)
        fig.update_yaxes(title="Margin %", ticksuffix="%")
        render_terminal_chart(fig)


def _statement_display_value(metric: str, value) -> str:
    if metric == "eps":
        return fmt_eps(value)
    if metric == "cash_runway":
        number = to_float(value)
        return f"{number:.1f} quarters" if number is not None else "N/A"
    return fmt_currency(value, 1)


def render_statement_table(visual: dict) -> None:
    rows = []
    for row in visual.get("detailed_rows") or []:
        rows.append(
            {
                "Statement": row.get("statement"),
                "Metric": row.get("label"),
                "Latest Value": _statement_display_value(row.get("metric"), row.get("value")),
                "Period": row.get("period") or "N/A",
                "Source": row.get("source") or "N/A",
                "Status / Note": row.get("note") or row.get("status") or "OK",
            }
        )
    if not rows:
        empty_state("Detailed 3-statement rows unavailable.")
        return
    df_display(pd.DataFrame(rows), height=420)


def _statement_tone(value) -> str:
    number = to_float(value)
    if number is None:
        return "neutral"
    if number < 0:
        return "bad"
    if number > 0:
        return "good"
    return "neutral"


def _status_tone(status: str) -> str:
    if status in {"Complete", "Mostly complete", "Profitable", "Operating profitable", "Cash-rich", "FCF positive", "OK", "Strong liquidity"}:
        return "good"
    if status in {"Partial data", "Partial", "Limited", "Unprofitable", "Burning cash", "Elevated burn", "Net debt", "Moderate liquidity", "Tight liquidity", "Stale"}:
        return "warn"
    if status in {"Insufficient data", "Insufficient", "Debt data unavailable", "Source error", "Error", "High liquidity risk", "N/A"}:
        return "bad"
    return "neutral"


def _fmt_completeness(value) -> str:
    number = to_float(value)
    return "N/A" if number is None else f"{number:.0f}%"


def _compact_bar_chart(title: str, labels: list[str], values: list[float | None], *, currency: bool = True, height: int = 220, orientation: str = "h") -> None:
    rows = [(label, to_float(value)) for label, value in zip(labels, values) if to_float(value) is not None]
    if not rows:
        empty_state(f"{title} unavailable.")
        return
    labels_clean = [row[0] for row in rows]
    values_clean = [row[1] for row in rows]
    colors = [BRAND_COLORS["pine_bright"] if value >= 0 else BRAND_COLORS["red"] for value in values_clean]
    text = [fmt_currency(value, 1) if currency else fmt_number(value, 1) for value in values_clean]
    if orientation == "v":
        bar = go.Bar(
            x=labels_clean,
            y=values_clean,
            marker_color=colors,
            text=text,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{text}<extra></extra>",
        )
    else:
        bar = go.Bar(
            x=values_clean,
            y=labels_clean,
            orientation="h",
            marker_color=colors,
            text=text,
            textposition="auto",
            cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    fig = go.Figure(
        bar
    )
    fig = plotly_layout(fig, height=height)
    fig.update_layout(showlegend=False, margin={"l": 86 if orientation == "h" else 22, "r": 20, "t": 18, "b": 46 if orientation == "v" else 28})
    fig.update_xaxes(zeroline=True, zerolinecolor=BRAND_COLORS["muted"])
    if orientation == "h":
        fig.update_yaxes(autorange="reversed")
    render_terminal_chart(fig)


def _statement_header_strip(visual: dict) -> None:
    status = str(visual.get("source_status") or "N/A")
    tone = _status_tone(status)
    tone_class = {"good": "rt-good", "bad": "rt-bad", "warn": "rt-warn"}.get(tone, "rt-neutral")
    parts = [
        escape(str(visual.get("ticker") or "N/A")),
        escape(str(visual.get("reported_period") or "N/A")),
        f"Period ended {escape(fmt_date(visual.get('period_end_date')))}",
        f"Source: {escape(str(visual.get('source') or 'N/A'))}",
        f'<span class="{tone_class}">Status: {escape(status)}</span>',
    ]
    st.markdown(
        f'<div class="rt-card small" style="display:flex;flex-wrap:wrap;gap:0.6rem;align-items:center;">{" | ".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def _analyst_takeaway_box(text: str) -> None:
    st.markdown(
        f"""
        <div class="rt-card small" style="border-color:rgba(125,211,252,0.32);">
          <div class="rt-label">Analyst Takeaway</div>
          <div class="rt-caption" style="font-size:0.9rem;color:#d8e5e8;">{escape(text or "Latest 3-statement takeaway unavailable.")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _margin_text(entry: dict) -> str:
    value = to_float((entry or {}).get("value"))
    if value is None:
        status = str((entry or {}).get("status") or "N/A")
        return "NM" if status.startswith("NM") or "mismatch" in status.casefold() else "N/A"
    return fmt_meaningful_percent(value)


def _runway_text(cash_flow: dict) -> str:
    fcf = to_float(cash_flow.get("free_cash_flow"))
    runway = cash_flow.get("cash_runway")
    if fcf is not None and fcf >= 0:
        return "FCF positive"
    return f"Approx. {runway:.1f} quarters" if runway is not None else "N/A"


def render_three_statement_visual(ticker: str, financials: dict) -> None:
    visual = build_three_statement_visual_data(ticker, financials)
    income = visual.get("income_statement", {})
    balance = visual.get("balance_sheet", {})
    cash_flow = visual.get("cash_flow", {})
    margins = visual.get("margins", {})
    health = visual.get("health_summary", {})
    _statement_header_strip(visual)
    if visual.get("missing_fields") or str(visual.get("source_status")) in {"Partial", "Stale structured values"}:
        note = visual.get("data_quality_note") or "Some values are unavailable or sourced from a fallback provider. Review detailed table."
        st.warning(note)
    _analyst_takeaway_box(visual.get("analyst_takeaway", ""))
    if visual.get("reconciliation", {}).get("has_mismatch"):
        st.warning("Financial statement values are partially sourced or period-mismatched. Review detailed table before relying on this view.")
    col_income, col_balance, col_cash = st.columns(3)
    with col_income:
        st.markdown("#### Income Statement")
        render_metric_grid(
            [
                ("Revenue", fmt_currency(income.get("revenue"), 1), "Top line", "neutral"),
                ("Gross Profit", fmt_currency(income.get("gross_profit"), 1), "After cost of revenue", _statement_tone(income.get("gross_profit"))),
                ("Operating Income / Loss", fmt_currency(income.get("operating_income"), 1), "Operating result", _statement_tone(income.get("operating_income"))),
                ("Net Income / Loss", fmt_currency(income.get("net_income"), 1), "Bottom line", _statement_tone(income.get("net_income"))),
                ("EPS", fmt_eps(income.get("eps")), "Per diluted share where available", _statement_tone(income.get("eps"))),
            ],
            columns=1,
            small=True,
        )
        _compact_bar_chart(
            "Revenue To Net Income",
            ["Revenue", "Gross Profit", "Operating Income", "Net Income"],
            [income.get("revenue"), income.get("gross_profit"), income.get("operating_income"), income.get("net_income")],
            orientation="v",
            height=250,
        )
        render_metric_grid(
            [
                ("Gross Margin", _margin_text(margins.get("gross_margin", {})), (margins.get("gross_margin", {}) or {}).get("status", ""), "neutral"),
                ("Operating Margin", _margin_text(margins.get("operating_margin", {})), (margins.get("operating_margin", {}) or {}).get("status", ""), "neutral"),
                ("Net Margin", _margin_text(margins.get("net_margin", {})), (margins.get("net_margin", {}) or {}).get("status", ""), "neutral"),
            ],
            columns=3,
            small=True,
        )
    with col_balance:
        st.markdown("#### Balance Sheet")
        net_cash = balance.get("net_cash_or_debt")
        render_metric_grid(
            [
                ("Cash & Equivalents", fmt_currency(balance.get("cash"), 1), "Latest matching balance sheet", "neutral"),
                ("Total Debt", fmt_currency(balance.get("total_debt"), 1), "Debt data unavailable if N/A", "warn" if balance.get("total_debt") is None else "neutral"),
                ("Net Cash / Debt", fmt_currency(net_cash, 1), "Cash less debt", _statement_tone(net_cash)),
                ("Total Assets", fmt_currency(balance.get("total_assets"), 1), "Latest matching balance sheet", "neutral"),
                ("Shareholders' Equity", fmt_currency(balance.get("shareholders_equity"), 1), "Book equity", _statement_tone(balance.get("shareholders_equity"))),
            ],
            columns=1,
            small=True,
        )
        render_metric_grid(
            [
                ("Liquidity Label", health.get("liquidity_status", "N/A"), _runway_text(cash_flow), _status_tone(health.get("liquidity_status", ""))),
            ],
            columns=1,
            small=True,
        )
        if balance.get("cash") is not None and balance.get("total_debt") is not None:
            _compact_bar_chart("Cash vs Debt", ["Cash", "Total Debt"], [balance.get("cash"), balance.get("total_debt")], height=190)
        elif balance.get("cash") is not None:
            st.caption("Debt data unavailable. Cash is shown, but net cash/debt is not calculated.")
        else:
            empty_state("Insufficient balance sheet data.")
    with col_cash:
        st.markdown("#### Cash Flow")
        render_metric_grid(
            [
                ("Operating Cash Flow", fmt_currency(cash_flow.get("operating_cash_flow"), 1), "Cash from operations", _statement_tone(cash_flow.get("operating_cash_flow"))),
                ("Capital Expenditures", fmt_currency(cash_flow.get("capex"), 1), "Normalized as cash outflow", _statement_tone(cash_flow.get("capex"))),
                ("Free Cash Flow", fmt_currency(cash_flow.get("free_cash_flow"), 1), "OCF less capex outflow", _statement_tone(cash_flow.get("free_cash_flow"))),
                ("Cash Runway", _runway_text(cash_flow), "Approximation from latest quarterly FCF", _status_tone(health.get("liquidity_status", ""))),
            ],
            columns=1,
            small=True,
        )
        _compact_bar_chart("OCF To FCF Bridge", ["Operating CF", "Capex Outflow", "Free CF"], [cash_flow.get("operating_cash_flow"), cash_flow.get("capex"), cash_flow.get("free_cash_flow")], height=210)
        st.caption("FCF calculated as operating cash flow less capex.")
    st.markdown("#### 3-Statement Health Summary")
    render_metric_grid(
        [
            ("Profitability", health.get("profitability_status", "N/A"), "Net income based", _status_tone(health.get("profitability_status", ""))),
            ("Liquidity", health.get("liquidity_status", "N/A"), "Cash runway and debt availability", _status_tone(health.get("liquidity_status", ""))),
            ("Cash Burn", health.get("cash_burn_status", "N/A"), "Free cash flow based", _status_tone(health.get("cash_burn_status", ""))),
            ("Data Completeness", health.get("data_completeness_status", "N/A"), visual.get("data_quality_note") or "Latest-quarter fields", _status_tone(health.get("data_completeness_status", ""))),
        ],
        columns=4,
        small=True,
    )
    notes = visual.get("reconciliation_notes") or []
    if notes:
        with st.expander("3-Statement Reconciliation Notes"):
            for note in notes:
                st.write(f"- {note}")
    with st.expander("Detailed 3-Statement Table"):
        render_statement_table(visual)


def home_page(ticker: str) -> None:
    render_home_brand_header()
    snapshot, statuses = fetch_market_snapshot()
    cards = []
    for _, row in snapshot.iterrows():
        value = fmt_percent(row["Last"], decimals=2) if row["Ticker"] == "^TNX" else fmt_price(row["Last"])
        caption = f"{row['Name']} | {fmt_daily_move(row['Daily Move %'])}"
        cards.append((row["Ticker"], value, caption, tone_for_number(row["Daily Move %"])))
    render_metric_grid(cards[:7], columns=7, small=True)
    source_line("Yahoo Finance/yfinance market snapshot", now_et(), "Delayed / cached")
    col1, col2 = st.columns([1.15, 1])
    with col1:
        section("Company Snapshot", "Global ticker drives research pages.")
        quote = fetch_quote(ticker)
        quote_header(quote)
        source_line(quote.get("source"), quote.get("last_updated"), quote.get("status"))
        render_price_chart(ticker)
    with col2:
        section("Macro / Market News Headlines", "Broad market headlines and catalysts from current free sources.")
        macro_news_raw, macro_statuses = fetch_news("", 24)
        macro_news = macro_headlines(macro_news_raw)
        source_name, news_state = source_status_summary(macro_statuses)
        source_line(source_name, now_et(), news_state)
        if macro_news.empty:
            empty_state("Macro headlines unavailable from current free sources.")
        else:
            df_display(clean_news_table(macro_news), height=360)
    section("Market Snapshot Table")
    display = snapshot.copy()
    display["Last"] = display.apply(lambda r: fmt_percent(r["Last"], decimals=2) if r["Ticker"] == "^TNX" else fmt_price(r["Last"]), axis=1)
    display["Daily Move %"] = display["Daily Move %"].map(fmt_daily_move)
    df_display(display, height=300)


def company_page(ticker: str) -> None:
    st.title("Company Analysis")
    st.markdown('<div class="terminal-subtitle">Latest quote, financials, valuation, balance sheet risk, filings, options, and 3-statement snapshot.</div>', unsafe_allow_html=True)
    if st.button("Refresh Financial Data", type="primary"):
        reset_data_caches()
        st.rerun()
    financials = load_latest_company_financials(ticker)
    quote = financials.get("latest_quote") or fetch_quote(ticker)
    latest = latest_row(financials, "Quarterly")
    signal = compute_signal(ticker)
    options = fetch_options_summary(ticker, quote.get("price"))
    identity = get_company_identity(ticker)
    header_view_model = build_company_header_view_model(ticker, quote, identity, financials, signal, {"valuation_label": valuation_label(signal)}, signal.get("technicals", {}))
    render_company_hero(header_view_model)
    source_line(financials.get("source_metadata", {}).get("financials", "Yahoo Finance/yfinance"), financials.get("last_updated"), financials.get("status"))
    section("Signal Center", "Transparent research score with factor breakdown, confidence, and missing-data warnings.")
    render_signal_summary(ticker, signal)
    section("Technical Entry Setup")
    render_entry_signal(ticker, quote, latest, options, signal)
    with st.expander("Market Setup Details", expanded=False):
        section("7D Options Metrics", "Nearest-expiry options are used when available; values are annualized IV converted to the expiry window.")
        seven = options.get("seven_day", {})
        render_metric_grid(
            [
                ("7D IV", fmt_percent(seven.get("annual_iv")), seven.get("status", "Unavailable"), "neutral"),
                ("7D Implied Move", "+/-" + fmt_percent(seven.get("implied_move_pct")), "Options-implied range", "warn" if seven.get("implied_move_pct") and seven.get("implied_move_pct") > 10 else "neutral"),
                ("Options Expiry Used", fmt_date(seven.get("expiry")), f"{seven.get('days', 'N/A')} day(s)", "neutral"),
                ("ATM Strike", fmt_price(seven.get("atm_strike")), "Closest available strike", "neutral"),
            ],
            columns=4,
            small=True,
        )
        section("52W Price Position")
        render_52w_position(quote)
    section("Latest Quarterly Release", "Newest available quarterly statement values plus latest SEC filing metadata where available.")
    render_latest_quarterly_release(financials)
    render_financial_reconciliation(financials)
    section("Financial Summary")
    view = st.radio("Financial statement view", ["Quarterly", "Annual"], index=0, horizontal=True, key="company_financial_view")
    history = view_history(financials, view)
    latest = latest_row(financials, view)
    period = latest.get("period", view)
    risk_label, risk_tone = balance_sheet_risk_label(latest)
    render_metric_grid(
        [
            ("Revenue", fmt_currency(latest.get("revenue"), 1), period, "neutral"),
            ("Revenue Growth", fmt_growth(latest.get("revenue_yoy_growth") if view == "Quarterly" else latest.get("revenue_qoq_growth"), bool(latest.get("revenue_yoy_base_effect"))), "YoY where available; NM flags base effects", tone_for_number(latest.get("revenue_yoy_growth"))),
            ("Gross Margin", fmt_meaningful_percent(latest.get("gross_margin")), period, tone_for_number(latest.get("gross_margin"))),
            ("Operating Margin", fmt_meaningful_percent(latest.get("operating_margin")), period, tone_for_number(latest.get("operating_margin"))),
            ("Net Margin", fmt_meaningful_percent(latest.get("net_margin")), period, tone_for_number(latest.get("net_margin"))),
            ("Free Cash Flow", fmt_currency(latest.get("free_cash_flow"), 1), period, tone_for_number(latest.get("free_cash_flow"))),
            ("Cash", fmt_currency(latest.get("cash"), 1), period, "neutral"),
            ("Balance Sheet Risk", risk_label, cash_runway_caption(latest), risk_tone),
        ],
        columns=4,
    )
    section("3-Statement Analysis", "Visual latest-quarter view tying income statement, balance sheet, and cash flow together.")
    render_three_statement_visual(ticker, financials)
    section("Revenue, EPS, and Margins")
    render_financial_charts(
        history,
        view,
        {
            "label": financials.get("source_metadata", {}).get("chart_source"),
            "status": financials.get("source_metadata", {}).get("chart_source_status"),
            "note": financials.get("source_metadata", {}).get("chart_source_note"),
        },
    )
    section("Valuation")
    render_metric_grid(
        [
            ("Market Cap", fmt_currency(quote.get("market_cap"), 1), "Quote metadata", "neutral"),
            ("Enterprise Value", fmt_currency(quote.get("enterprise_value"), 1), "Quote metadata", "neutral"),
            ("Price / Sales", fmt_multiple(quote.get("price_to_sales")), valuation_label(signal), "neutral"),
            ("P/E", fmt_multiple(quote.get("trailing_pe")), "Not emphasized for unprofitable names", "neutral"),
            ("Forward P/E", fmt_multiple(quote.get("forward_pe")), "Forward estimate, if available", "neutral"),
            ("Price / Book", fmt_multiple(quote.get("price_to_book")), "Balance sheet multiple", "neutral"),
            ("EV / EBITDA", fmt_multiple(quote.get("ev_to_ebitda")), "Cash earnings multiple", "neutral"),
            ("Valuation View", valuation_label(signal), "Signal-engine heuristic", "warn" if valuation_label(signal) in {"Expensive", "Very expensive"} else "neutral"),
        ],
        columns=4,
    )
    section("SEC Filings")
    filings, status = fetch_sec_filings(ticker)
    source_line(status.get("Source"), status.get("Last Updated"), status.get("Status"))
    df_display(filings, height=180)
    section("Company Headlines", "Ticker-specific headlines and catalysts for the selected company.")
    news, news_statuses = fetch_news(ticker, 24)
    company_news = company_headlines(news, ticker)
    source_name, news_state = source_status_summary(news_statuses)
    source_line(source_name, now_et(), news_state)
    if company_news.empty:
        empty_state("No company-specific headlines found for this ticker.")
    else:
        df_display(clean_news_table(company_news), height=420)
    with st.expander("Catalyst Source Status"):
        st.json({"news_sources": news_statuses})
    with st.expander("Company Financials Data Validation"):
        st.json(
            {
                "selected_ticker": ticker,
                "financial_view_selected": view,
                "latest_reported_quarter": financials.get("latest_reported_earnings", {}),
                "income_statement_period": latest.get("period"),
                "statement_sources": financials.get("source_metadata", {}),
                "last_updated": str(financials.get("last_updated")),
                "status": financials.get("status"),
                "validation_warnings": financials.get("validation_warnings", []),
                "missing_fields": financials.get("missing_fields", []),
            }
        )


def signal_page(ticker: str) -> None:
    st.title("Signal Center")
    st.markdown('<div class="terminal-subtitle">Transparent V1 scoring engine. Research signal only, not investment advice.</div>', unsafe_allow_html=True)
    signal = compute_signal(ticker)
    render_metric_grid(
        [
            ("Composite Score", f"{signal.get('composite_score', 0):.1f}/100", signal.get("source", ""), tone_for_number(signal.get("composite_score"))),
            ("Signal", signal.get("signal_label", "N/A"), "Buy/Hold/Sell research signal", "good" if "Buy" in signal.get("signal_label", "") else "bad" if signal.get("signal_label") in {"Avoid", "Sell / Trim"} else "neutral"),
            ("Confidence", signal.get("confidence", "N/A"), "Missing-data adjusted", "good" if signal.get("confidence") == "High" else "warn" if signal.get("confidence") == "Medium" else "neutral"),
        ],
        columns=3,
    )
    score_frame = pd.DataFrame(
        [
            ("Growth", signal.get("growth_score")),
            ("Profitability", signal.get("profitability_score")),
            ("Balance Sheet", signal.get("balance_sheet_score")),
            ("Valuation", signal.get("valuation_score")),
            ("Momentum", signal.get("momentum_score")),
            ("Catalysts", signal.get("catalyst_score")),
        ],
        columns=["Category", "Score"],
    )
    fig = go.Figure(go.Bar(x=score_frame["Category"], y=score_frame["Score"], marker_color=BRAND_COLORS["pine_bright"], text=score_frame["Score"].round(1), textposition="outside", cliponaxis=False))
    fig = plotly_layout(fig, height=360)
    fig.update_yaxes(range=[0, 105], title="Score")
    render_terminal_chart(fig)
    col1, col2 = st.columns(2)
    with col1:
        section("Strengths")
        for item in signal.get("strengths", []):
            st.success(item)
        section("Upgrade Triggers")
        for item in signal.get("upgrade_triggers", []):
            st.write(f"- {item}")
    with col2:
        section("Weaknesses")
        for item in signal.get("weaknesses", []):
            st.warning(item)
        section("Downgrade Triggers")
        for item in signal.get("downgrade_triggers", []):
            st.write(f"- {item}")
    with st.expander("Signal Methodology"):
        st.write("Weights: Growth 20%, Profitability 15%, Balance Sheet 15%, Valuation 20%, Momentum 15%, Catalysts 15%.")
        st.json(signal)


def watchlist_page(ticker: str) -> None:
    st.title("Watchlist")
    st.markdown('<div class="terminal-subtitle">Track saved tickers, signal changes, market movers, options-implied moves, and social momentum.</div>', unsafe_allow_html=True)

    section("Watchlist Controls")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        new_ticker = st.text_input("Add ticker", placeholder="CRWV")
        if st.button("Add"):
            if add_ticker(new_ticker):
                st.success(f"Added {clean_ticker(new_ticker)}")
                st.session_state["watchlist_table"] = latest_watchlist_table()
                st.rerun()
            else:
                st.error("Invalid or unsupported ticker.")
    with col2:
        watch = list_watchlist()
        remove = st.selectbox("Remove ticker", [""] + watch.get("ticker", pd.Series(dtype=str)).tolist())
        if st.button("Remove", disabled=not remove):
            remove_ticker(remove)
            st.warning(f"Removed {remove}")
            st.rerun()
    with col3:
        if st.button("Refresh Watchlist", type="primary"):
            with st.spinner("Refreshing watchlist signals and alert history..."):
                st.session_state["watchlist_table"] = refresh_watchlist()
                st.success("Watchlist refreshed.")
    section("Watchlist Table")
    table = st.session_state.get("watchlist_table")
    if table is None:
        table = latest_watchlist_table()
    df_display(table, height=480)

    section("Alert Center", "In-app alerts generated from day-over-day signal changes.")
    alerts = list_alerts(False)
    if alerts.empty:
        empty_state("No active alerts.")
    else:
        df_display(alerts[["id", "ticker", "timestamp", "alert_type", "alert_message"]], height=240)
        dismiss_id = st.number_input("Dismiss alert ID", min_value=0, step=1)
        if st.button("Dismiss Alert", disabled=dismiss_id <= 0):
            dismiss_alert(int(dismiss_id))
            st.rerun()

    section("Market Volatility Scanner", "Cached broader-universe scan for tickers moving at least +/-5% by default.")
    scan_col1, scan_col2, scan_col3, scan_col4 = st.columns(4)
    with scan_col1:
        min_move = st.slider("Minimum daily move %", 1.0, 20.0, 5.0, 0.5, key="market_mover_threshold")
    with scan_col2:
        max_results = st.slider("Max results", 10, 100, 50, 5, key="market_mover_max")
    with scan_col3:
        include_etfs = st.toggle("Include ETFs", value=True, key="market_mover_include_etfs")
    with scan_col4:
        include_watch = st.toggle("Include watchlist tickers", value=True, key="market_mover_include_watchlist")
    if st.button("Refresh scanner"):
        try:
            scan_market_movers.clear()
        except Exception:
            pass
    extra = tuple(_watchlist_symbols()) if include_watch else ()
    with st.spinner("Scanning cached market universe..."):
        movers, mover_status = scan_market_movers(min_move, max_results, include_etfs, clean_mover_tickers(extra))
    st.session_state["market_movers_frame"] = movers
    source_line(mover_status.get("Source"), mover_status.get("Last Updated"), mover_status.get("Status"))
    if movers.empty:
        empty_state(f"No tickers in the V1 scan universe moved at least +/-{min_move:.1f}% today.")
    else:
        df_display(_format_movers_frame(movers), height=420)
    with st.expander("Market scanner source status"):
        st.json(mover_status)

    section("Options / Implied Move Monitor", "Options-implied move scanner with clean source statuses.")
    watch_symbols = _watchlist_symbols()
    scan_mode = st.selectbox("Scan universe", ["Selected ticker + Watchlist", "Watchlist only", "Top Market Movers", "Custom tickers"], index=0)
    custom_tickers = ""
    if scan_mode == "Custom tickers":
        custom_tickers = st.text_input("Custom tickers", placeholder="NVDA, IONQ, AMPX")
    if scan_mode == "Watchlist only":
        universe = watch_symbols
    elif scan_mode == "Top Market Movers":
        source_movers = st.session_state.get("market_movers_frame", pd.DataFrame())
        universe = source_movers.get("Ticker", pd.Series(dtype=str)).head(20).tolist()
    elif scan_mode == "Custom tickers":
        universe = [clean_ticker(value) for value in custom_tickers.replace(";", ",").split(",") if clean_ticker(value)]
    else:
        universe = [ticker] + [symbol for symbol in watch_symbols if symbol != ticker]
    universe = list(dict.fromkeys([symbol for symbol in universe if symbol]))
    max_names = st.slider("Max tickers to scan", 5, 50, min(12, len(universe) or 12), step=1, key="watchlist_options_max")
    with st.spinner("Loading options summaries..."):
        df_display(options_monitor_frame(universe[:max_names]), height=460)
    with st.expander("Options debug details"):
        debug = []
        for symbol in universe[:max_names]:
            quote = fetch_quote(symbol)
            opts = fetch_options_summary(symbol, quote.get("price"))
            debug.append({"ticker": symbol, "status": opts.get("status"), "seven_day": opts.get("seven_day"), "thirty_day": opts.get("thirty_day")})
        st.json(debug)

    section("Popular Stocktwits / Social Momentum Names", "Fallback social momentum universe with quote/daily move context.")
    if st.button("Refresh social names"):
        try:
            fetch_social_momentum_names.clear()
        except Exception:
            pass
    social, social_status = fetch_social_momentum_names()
    source_line(social_status.get("Source"), social_status.get("Last Updated"), social_status.get("Status"))
    if social_status.get("Status") == "Fallback":
        st.info("Stocktwits trending data unavailable from current free sources. Showing fallback social momentum universe.")
    watch_set = set(_watchlist_symbols())
    df_display(_social_display_frame(social, watch_set), height=380)
    social_candidates = [symbol for symbol in social.get("Ticker", pd.Series(dtype=str)).tolist() if clean_ticker(symbol) not in watch_set]
    add_social = st.selectbox("Add social ticker to Watchlist", [""] + social_candidates)
    if st.button("Add Social Ticker", disabled=not add_social):
        if add_ticker(add_social):
            st.success(f"Added {add_social}")
            st.rerun()
        else:
            st.error("Invalid or unsupported ticker.")
    with st.expander("Social source status"):
        st.json(social_status)


def volatility_page(ticker: str) -> None:
    st.title("Volatility Radar")
    st.markdown('<div class="terminal-subtitle">Nearest 7D and 30D options-implied move monitor for the selected ticker and watchlist.</div>', unsafe_allow_html=True)
    watch = list_watchlist()
    universe = [ticker] + [t for t in watch.get("ticker", pd.Series(dtype=str)).tolist() if t != ticker]
    max_names = st.slider("Max tickers to scan", 5, 30, min(12, len(universe) or 12), step=1)
    rows = []
    for symbol in universe[:max_names]:
        quote = fetch_quote(symbol)
        opts = fetch_options_summary(symbol, quote.get("price"))
        seven = opts.get("seven_day", {})
        thirty = opts.get("thirty_day", {})
        rows.append(
            {
                "Ticker": symbol,
                "Last Price": fmt_price(quote.get("price")),
                "7D Implied Move": "+/-" + fmt_percent(seven.get("implied_move_pct")),
                "7D IV": fmt_percent(seven.get("annual_iv")),
                "7D Expiry": fmt_date(seven.get("expiry")),
                "30D Implied Move": "+/-" + fmt_percent(thirty.get("implied_move_pct")),
                "Options Status": opts.get("status"),
            }
        )
    df_display(pd.DataFrame(rows), height=520)
    with st.expander("Data validation"):
        st.json(
            {
                "selected_expiry_window": "7D primary, 30D secondary",
                "implied_move_formula_used": "annualized_IV * sqrt(days_to_expiry / 365)",
                "number_of_tickers_loaded": len(universe[:max_names]),
                "source": "Yahoo Finance/yfinance options",
            }
        )


def macro_page(ticker: str) -> None:
    st.title("Macro & Catalysts")
    st.markdown('<div class="terminal-subtitle">Macro checklist plus recent company and market headlines.</div>', unsafe_allow_html=True)
    macro, status = fetch_macro_catalysts()
    render_metric_grid([(row["Theme"], row["Status"], row["Catalyst"], "neutral") for _, row in macro.iterrows()], columns=3, small=True)
    source_line(status.get("Source"), status.get("Last Updated"), status.get("Status"))
    section("Headlines")
    news, statuses = fetch_news(ticker, 24)
    if news.empty:
        empty_state("No headlines found.")
    else:
        df_display(news[["Headline", "Source", "Published", "Ticker", "Tag", "Link"]], height=560)
    with st.expander("News source status"):
        st.json(statuses)


def ai_due_diligence_page(ticker: str) -> None:
    st.title("AI Due Diligence")
    st.markdown('<div class="terminal-subtitle">Generates a starter DD memo from the terminal research packet. Disabled unless OPENAI_API_KEY exists in Streamlit secrets.</div>', unsafe_allow_html=True)
    packet = build_research_packet(ticker)
    with st.expander("Research packet", expanded=False):
        st.json(packet)
    key = streamlit_secret_value("OPENAI_API_KEY")
    model = "gpt-4o-mini"
    model = streamlit_secret_value("OPENAI_MODEL", model)
    if not key:
        st.info("AI DD is disabled until OPENAI_API_KEY is added to Streamlit secrets.")
        return
    if st.button("Generate DD Memo", type="primary"):
        with st.spinner("Generating memo from structured terminal data..."):
            memo, error = generate_dd_memo(packet, key, model=model)
        if error:
            st.error(error)
        else:
            st.markdown(memo)


def data_health_page(ticker: str) -> None:
    st.title("Data Health / Settings")
    st.markdown('<div class="terminal-subtitle">Source status, cache notes, database location, and V1 limitations.</div>', unsafe_allow_html=True)
    quote = fetch_quote(ticker)
    financials = load_latest_company_financials(ticker)
    identity = get_company_identity(ticker)
    latest_release = financials.get("latest_quarterly_release") or get_latest_quarterly_release(ticker)
    opts = fetch_options_summary(ticker, quote.get("price"))
    news, news_statuses = fetch_news(ticker, 8)
    filings, filing_status = fetch_sec_filings(ticker)
    sec_latest = fetch_latest_sec_filing(ticker)
    sec_periodic = fetch_latest_periodic_sec_filing(ticker)
    _, cik_status = ticker_to_cik(ticker)
    reconciliation = financials.get("reconciliation") or {}
    source_meta = financials.get("source_metadata", {})
    packet = financials.get("financial_data_packet") or {}
    quality = packet.get("coverage_summary") or latest_release.get("financial_data_quality") or reconciliation.get("data_quality") or {}
    watch_symbols = _watchlist_symbols()
    try:
        _, mover_status = scan_market_movers(5.0, 50, True, clean_mover_tickers(tuple(watch_symbols)))
    except Exception as exc:
        mover_status = {"Source": "Market volatility scanner", "Status": "Source error", "Last Updated": now_et(), "Error": str(exc)}
    try:
        _, social_status = fetch_social_momentum_names()
    except Exception as exc:
        social_status = {"Source": "Social momentum", "Status": "Source error", "Last Updated": now_et(), "Error": str(exc)}
    openai_status = "OK" if streamlit_secret_value("OPENAI_API_KEY") else "Missing"
    date_status = get_date_normalization_status()
    health = pd.DataFrame(
        [
            {"Source": "Yahoo Finance/yfinance quote", "Status": quote.get("status"), "Last Refresh": quote.get("last_updated"), "Cache TTL": "5 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": quote.get("error", "")},
            {"Source": "Company identity / logo", "Status": identity.get("logo_status"), "Last Refresh": identity.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": identity.get("error", "")},
            {"Source": "Yahoo Finance/yfinance financials", "Status": financials.get("status"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(financials.get("missing_fields", [])), "Error": financials.get("error", "")},
            {"Source": "Latest quarterly release", "Status": latest_release.get("source_status"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("data_quality_note", "")},
            {"Source": "Latest cards source", "Status": latest_release.get("source_status"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("compact_source_status_note", "")},
            {"Source": "Financial packet status", "Status": packet.get("source_status", "N/A"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": packet.get("reported_period_label", latest_release.get("reported_period_label", "")), "Structured Period": packet.get("structured_values_period_label", latest_release.get("structured_values_period_label", "")), "Missing Fields": ", ".join(packet.get("missing", [])), "Error": packet.get("data_quality_note", "")},
            {"Source": "Financial data completeness", "Status": _fmt_completeness(quality.get("completeness_score", latest_release.get("data_completeness_score"))), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(quality.get("missing", [])), "Error": packet.get("data_quality_note", latest_release.get("compact_source_status_note", ""))},
            {"Source": "Found financial fields", "Status": "OK" if quality.get("found_direct") else "N/A", "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": ", ".join(quality.get("found_direct", []))},
            {"Source": "Calculated financial fields", "Status": "OK" if quality.get("calculated") else "N/A", "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": ", ".join(quality.get("calculated", []))},
            {"Source": "Estimated financial fields", "Status": "Partial" if quality.get("estimated") else "N/A", "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": ", ".join(quality.get("estimated", []))},
            {"Source": "Yahoo Finance/yfinance options", "Status": opts.get("status"), "Last Refresh": opts.get("last_updated"), "Cache TTL": "30 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": opts.get("debug_error", "")},
            {"Source": "Watchlist quote population", "Status": "OK" if not latest_watchlist_table().empty else "Partial", "Last Refresh": now_et(), "Cache TTL": "SQLite snapshot + 5 min quote cache", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": ""},
            {"Source": "Watchlist signal refresh", "Status": "OK", "Last Refresh": now_et(), "Cache TTL": "On refresh", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": "Signals are saved when Refresh Watchlist is clicked."},
            {"Source": "Alert generation", "Status": "OK", "Last Refresh": now_et(), "Cache TTL": "SQLite persistent alerts", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": "Alerts are generated on watchlist refresh."},
            {"Source": "Market volatility scanner", "Status": mover_status.get("Status"), "Last Refresh": mover_status.get("Last Updated"), "Cache TTL": "10 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": mover_status.get("Error", "")},
            {"Source": "Stocktwits/social source", "Status": social_status.get("Status"), "Last Refresh": social_status.get("Last Updated"), "Cache TTL": "15 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": social_status.get("Error", "")},
            {"Source": "Yahoo Finance/RSS news", "Status": "OK" if not news.empty else "Partial", "Last Refresh": now_et(), "Cache TTL": "30 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": ""},
            {"Source": "SEC ticker-to-CIK mapping", "Status": cik_status.get("Status"), "Last Refresh": cik_status.get("Last Updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": cik_status.get("Error", "")},
            {"Source": "SEC latest filing metadata", "Status": sec_latest.get("source_status"), "Last Refresh": sec_latest.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": sec_latest.get("filing_period_label", ""), "Structured Period": "", "Missing Fields": "", "Error": sec_latest.get("error", "")},
            {"Source": "SEC latest period-bearing filing", "Status": sec_periodic.get("source_status"), "Last Refresh": sec_periodic.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": sec_periodic.get("filing_period_label", ""), "Structured Period": "", "Missing Fields": "", "Error": sec_periodic.get("error", "")},
            {"Source": "SEC companyfacts", "Status": (latest_release.get("sec_companyfacts_status") or {}).get("Status", "N/A"), "Last Refresh": (latest_release.get("sec_companyfacts_status") or {}).get("Last Updated", latest_release.get("last_updated")), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": (latest_release.get("sec_companyfacts_status") or {}).get("Error", "")},
            {"Source": "SEC structured value extraction", "Status": latest_release.get("sec_value_extraction_status", "N/A"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("data_quality_note", "")},
            {"Source": "SEC concept coverage", "Status": source_meta.get("sec_concept_coverage", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(source_meta.get("missing_financial_concepts", [])), "Error": ""},
            {"Source": "yfinance fallback coverage", "Status": "Partial" if source_meta.get("yfinance_fallback_metrics") else "N/A", "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": ", ".join(source_meta.get("yfinance_fallback_metrics", []))},
            {"Source": "Missing financial concepts", "Status": "Partial" if source_meta.get("missing_financial_concepts") else "OK", "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(source_meta.get("missing_financial_concepts", [])), "Error": "Mapped SEC concepts and period-aligned fallback did not produce these latest-period metrics." if source_meta.get("missing_financial_concepts") else ""},
            {"Source": "Debt calculation quality", "Status": source_meta.get("debt_calculation_quality", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": (", ".join(source_meta.get("debt_components_used", [])) + ". " if source_meta.get("debt_components_used") else "") + source_meta.get("debt_calculation_note", "")},
            {"Source": "FCF calculation status", "Status": source_meta.get("fcf_calculation_status", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": source_meta.get("fcf_calculation_note", "")},
            {"Source": "Period alignment", "Status": latest_release.get("period_alignment_status", "N/A"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": latest_release.get("data_quality_note", "")},
            {"Source": "Financial chart source", "Status": financials.get("source_metadata", {}).get("chart_source_status", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": financials.get("source_metadata", {}).get("chart_source_note", "")},
            {"Source": "Missing metric periods", "Status": "Partial" if reconciliation.get("missing_chart_fields") or reconciliation.get("missing_metric_periods") else "OK", "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "; ".join((reconciliation.get("missing_chart_fields") or []) + (reconciliation.get("missing_metric_periods") or [])), "Error": ""},
            {"Source": "Margin calculation validity", "Status": financials.get("source_metadata", {}).get("margin_validity", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": " ".join(reconciliation.get("margin_notes", []))},
            {"Source": "Date/time normalization", "Status": date_status.get("Status"), "Last Refresh": date_status.get("Last Updated"), "Cache TTL": "Runtime", "Filing Period": "", "Structured Period": "", "Missing Fields": date_status.get("Affected Field", ""), "Error": date_status.get("Error", "")},
            {"Source": filing_status.get("Source"), "Status": filing_status.get("Status"), "Last Refresh": filing_status.get("Last Updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": filing_status.get("Error", "")},
            {"Source": "SQLite watchlist", "Status": "OK", "Last Refresh": now_et(), "Cache TTL": "Persistent local DB", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": ""},
            {"Source": "OpenAI API", "Status": openai_status, "Last Refresh": now_et(), "Cache TTL": "On demand", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": "OPENAI_API_KEY not configured" if openai_status == "Missing" else ""},
        ]
    )
    df_display(health, height=260)
    render_metric_grid(
        [
            ("Database", str(DB_PATH), "SQLite persistence", "neutral"),
            ("Default Watchlist", str(len(DEFAULT_TICKERS)), ", ".join(DEFAULT_TICKERS[:6]) + "...", "neutral"),
            ("Selected Ticker", ticker, quote.get("company_name", ""), "neutral"),
        ],
        columns=3,
        small=True,
    )
    section("V1 Limitations")
    st.write(
        """
        - yfinance is MVP-grade and may be incomplete or delayed.
        - Some tickers may lack options, analyst, or financial statement data.
        - In-app alerts are generated when the app refreshes or the watchlist refresh button is clicked.
        - Research signals are transparent indicators, not automatic trade instructions or investment advice.
        """
    )
    with st.expander("Debug source diagnostics"):
        st.json(
            {
                "selected_ticker": ticker,
                "company_identity": identity,
                "quote_error": quote.get("error"),
                "latest_quarterly_release": latest_release,
                "latest_filing_period": latest_release.get("filing_period_label"),
                "structured_values_period": latest_release.get("structured_values_period_label"),
                "period_alignment_status": latest_release.get("period_alignment_status"),
                "latest_quarter_source_status": latest_release.get("source_status"),
                "latest_quarter_missing_fields": latest_release.get("missing_fields", []),
                "latest_quarter_last_error_summary": latest_release.get("data_quality_note"),
                "financial_missing_fields": financials.get("missing_fields", []),
                "financial_warnings": financials.get("validation_warnings", []),
                "options_debug": opts,
                "news_sources": news_statuses,
                "filings_status": filing_status,
            }
        )


def render_page(page: str, ticker: str) -> None:
    try:
        if page == "Home / Market Monitor":
            home_page(ticker)
        elif page == "Company Analysis":
            company_page(ticker)
        elif page == "Watchlist":
            watchlist_page(ticker)
        elif page == "AI Due Diligence":
            ai_due_diligence_page(ticker)
        elif page == "Data Health / Settings":
            data_health_page(ticker)
    except Exception as exc:
        st.error(f"This page could not be rendered cleanly. {exc}")
        st.info("Open Data Health / Settings for source status, then refresh data. Raw tracebacks are hidden in the V1 UI.")


def main() -> None:
    render_sidebar_brand()
    if "global_ticker_input" not in st.session_state:
        st.session_state["global_ticker_input"] = clean_ticker(st.session_state.get("global_ticker", "IONQ")) or "IONQ"
    ticker_input = st.sidebar.text_input("Global ticker", placeholder="IONQ", key="global_ticker_input", on_change=normalize_global_ticker_input)
    ticker = clean_ticker(ticker_input) or "IONQ"
    st.session_state["global_ticker"] = ticker
    if st.sidebar.button("Refresh Data"):
        reset_data_caches()
        st.rerun()
    page = st.sidebar.radio("Tabs", PAGES, index=PAGES.index(st.session_state.get("page", PAGES[0])) if st.session_state.get("page") in PAGES else 0)
    st.session_state["page"] = page
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Selected: {ticker}")
    st.sidebar.caption(f"Session refreshed: {fmt_date(now_et())}")
    render_page(page, ticker)


if __name__ == "__main__":
    main()
