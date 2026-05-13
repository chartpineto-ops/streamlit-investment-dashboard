from __future__ import annotations

from datetime import datetime
from math import isnan

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai.dd_generator import build_research_packet, generate_dd_memo, openai_key_from_secrets
from data.company_identity import get_company_identity
from data.filings import fetch_latest_periodic_sec_filing, fetch_latest_sec_filing, fetch_sec_filings, ticker_to_cik
from data.financials import get_latest_quarterly_release, load_latest_company_financials, view_history
from data.macro import fetch_macro_catalysts
from data.market_data import DEFAULT_TICKERS, fetch_history, fetch_market_snapshot, fetch_quote
from data.news import fetch_news
from data.options import fetch_options_summary
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
from ui.styles import apply_terminal_style
from utils.formatting import (
    clean_ticker,
    fmt_compact,
    fmt_currency,
    fmt_date,
    fmt_eps,
    fmt_multiple,
    fmt_percent,
    fmt_price,
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


st.set_page_config(page_title="Research Terminal 2.0", page_icon="RT", layout="wide")
apply_terminal_style()
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


def plotly_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#071013",
        font={"color": "#dfe8eb", "family": "Inter, Arial, sans-serif"},
        margin={"l": 42, "r": 24, "t": 38, "b": 44},
        height=height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    fig.update_xaxes(gridcolor="#1d3440", zerolinecolor="#31515f")
    fig.update_yaxes(gridcolor="#1d3440", zerolinecolor="#31515f")
    return fig


def df_display(frame: pd.DataFrame, height: int = 320) -> None:
    if frame is None or frame.empty:
        empty_state("No data available.")
        return
    config = {}
    if "Link" in frame.columns:
        config["Link"] = st.column_config.LinkColumn("Link", display_text="Open")
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
    if "Published" in display:
        display["Published"] = display["Published"].map(fmt_date)
    display["Link"] = display.get("Link", "").map(lambda value: value if isinstance(value, str) and value.startswith("http") else None)
    cols = [col for col in ["Headline", "Scope", "Tag", "Source", "Published", "Link"] if col in display]
    return display[cols]


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
    fig = go.Figure(go.Bar(x=score_frame["Category"], y=score_frame["Score"], marker_color="#7dd3fc", text=score_frame["Score"].round(1), textposition="outside", cliponaxis=False))
    fig = plotly_layout(fig, height=330)
    fig.update_yaxes(range=[0, 105], title="Score")
    st.plotly_chart(fig, use_container_width=True)
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
            <div style="position:absolute;left:0;right:0;top:30px;height:10px;border-radius:99px;background:linear-gradient(90deg,#e77878,#f4d35e,#7bd88f);border:1px solid #496b77;"></div>
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
            ("Overall Research Signal", signal.get("signal_label", "N/A"), "Full research signal based on growth, profitability, balance sheet, valuation, momentum, catalysts, and data quality.", tone_for_number(signal.get("composite_score"))),
        ],
        columns=3,
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
    if not release:
        st.info("Latest quarterly release data unavailable for this ticker.")
        return
    status = release.get("source_status", "N/A")
    tone = (
        "good"
        if status == "OK"
        else "warn"
        if status in {"Partial", "Not applicable", "Stale structured values", "Filing metadata only", "Structured values only"}
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
            ("Source Status", status, release.get("source_status_reason") or release.get("period_alignment_status") or release.get("data_quality_note", ""), tone),
        ]
    )
    render_metric_grid(cards, columns=3, small=True)
    if show_structured_period or release.get("period_alignment_status") == "Filing newer than structured values":
        st.warning(release.get("data_quality_note") or f"Latest filing detected for {reported_period}; structured financial values may still reflect {structured_period}.")
    filing_url = release.get("filing_url")
    if filing_url:
        st.link_button("Open filing", filing_url)
    missing = release.get("missing_fields") or []
    if missing:
        st.caption("Missing fields: " + ", ".join(missing))


def _reconciliation_display_value(metric: str, value) -> str:
    if metric == "eps":
        return fmt_eps(value)
    if metric == "shares_outstanding":
        return fmt_compact(value)
    return fmt_currency(value, 1)


def render_financial_reconciliation(financials: dict) -> None:
    reconciliation = financials.get("reconciliation") or {}
    if reconciliation.get("has_mismatch"):
        st.warning("Financial period mismatch detected. Review reconciliation details.")
    with st.expander("Financial Data Reconciliation"):
        rows = reconciliation.get("rows") or []
        if rows:
            display_rows = []
            for row in rows:
                display_rows.append(
                    {
                        "Metric": row.get("Metric"),
                        "Displayed Value": _reconciliation_display_value(row.get("metric"), row.get("value")),
                        "Period": row.get("Period"),
                        "Period End Date": row.get("Period End Date"),
                        "Source": row.get("Source"),
                        "Form": row.get("Form"),
                        "Filed Date": row.get("Filed Date"),
                        "Accession": row.get("Accession"),
                        "Status": row.get("Status"),
                        "Missing / Note": row.get("Missing / Note"),
                    }
                )
            df_display(pd.DataFrame(display_rows), height=360)
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
    fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close", line={"color": "#7dd3fc", "width": 2.4}))
    fig = plotly_layout(fig, height=320)
    fig.update_yaxes(title="Price")
    st.plotly_chart(fig, use_container_width=True)


def render_financial_charts(history: pd.DataFrame, view: str, chart_source: dict | None = None) -> None:
    if history.empty:
        empty_state(f"{view} financial statement data unavailable.")
        return
    chart_frame = history.tail(8).copy()
    if chart_source:
        st.caption(f"Chart source: {chart_source.get('label', 'N/A')} | Status: {chart_source.get('status', 'N/A')} | {chart_source.get('note', '')}")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=chart_frame["period"],
                y=chart_frame["revenue"],
                name="Actual Revenue",
                marker_color="#7dd3fc",
                text=[fmt_currency(v, 1) for v in chart_frame["revenue"]],
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig = plotly_layout(fig, height=340)
        fig.update_yaxes(title="Revenue")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        if "eps" in chart_frame and chart_frame["eps"].notna().any():
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=chart_frame["period"],
                    y=chart_frame["eps"],
                    name="Actual EPS",
                    marker_color="#7bd88f",
                    text=[fmt_eps(v) for v in chart_frame["eps"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig = plotly_layout(fig, height=340)
            fig.update_yaxes(title="EPS")
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state("EPS history unavailable.")
    margin_cols = ["gross_margin", "operating_margin", "net_margin", "fcf_margin"]
    if any(col in chart_frame and chart_frame[col].notna().any() for col in margin_cols):
        fig = go.Figure()
        colors = {"gross_margin": "#7dd3fc", "operating_margin": "#7bd88f", "net_margin": "#f4d35e", "fcf_margin": "#c084fc"}
        labels = {"gross_margin": "Gross Margin", "operating_margin": "Operating Margin", "net_margin": "Net Margin", "fcf_margin": "FCF Margin"}
        for col in margin_cols:
            if col in chart_frame and chart_frame[col].notna().any():
                fig.add_trace(go.Scatter(x=chart_frame["period"], y=chart_frame[col], mode="lines+markers", name=labels[col], line={"color": colors[col]}))
        fig = plotly_layout(fig, height=340)
        fig.update_yaxes(title="Margin %", ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)


def render_statement_table(latest: dict) -> None:
    rows = [
        ("Income Statement", "Revenue", fmt_currency(latest.get("revenue"), 1)),
        ("Income Statement", "Gross Profit", fmt_currency(latest.get("gross_profit"), 1)),
        ("Income Statement", "Operating Income", fmt_currency(latest.get("operating_income"), 1)),
        ("Income Statement", "Net Income", fmt_currency(latest.get("net_income"), 1)),
        ("Income Statement", "EPS", fmt_eps(latest.get("eps"))),
        ("Balance Sheet", "Cash & Equivalents", fmt_currency(latest.get("cash"), 1)),
        ("Balance Sheet", "Total Assets", fmt_currency(latest.get("total_assets"), 1)),
        ("Balance Sheet", "Total Debt", fmt_currency(latest.get("total_debt"), 1)),
        ("Balance Sheet", "Shareholders' Equity", fmt_currency(latest.get("shareholders_equity"), 1)),
        ("Cash Flow", "Operating Cash Flow", fmt_currency(latest.get("operating_cash_flow"), 1)),
        ("Cash Flow", "Capital Expenditures", fmt_currency(latest.get("capital_expenditures"), 1)),
        ("Cash Flow", "Free Cash Flow", fmt_currency(latest.get("free_cash_flow"), 1)),
        ("Cash Flow", "Financing Cash Flow", fmt_currency(latest.get("financing_cash_flow"), 1)),
    ]
    df_display(pd.DataFrame(rows, columns=["Statement", "Metric", "Latest Value"]), height=420)


def home_page(ticker: str) -> None:
    st.title("Research Terminal 2.0")
    st.markdown('<div class="terminal-subtitle">Bloomberg-style V1 personal investment research terminal.</div>', unsafe_allow_html=True)
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
        section("News & Catalysts", "Recent ticker headlines plus broad market feed.")
        news, _ = fetch_news(ticker, 10)
        if news.empty:
            empty_state("No headlines found.")
        else:
            df_display(news[["Headline", "Source", "Published", "Tag", "Link"]], height=360)
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
    quote_header(quote)
    source_line(financials.get("source_metadata", {}).get("financials", "Yahoo Finance/yfinance"), financials.get("last_updated"), financials.get("status"))
    render_metric_grid(
        [
            ("Market Cap", fmt_currency(quote.get("market_cap"), 1), "Quote metadata", "neutral"),
            ("Volume / Avg", f"{fmt_compact(quote.get('volume'))} / {fmt_compact(quote.get('average_volume'))}", "Latest daily volume", "neutral"),
            ("Sector", str(quote.get("sector") or "N/A"), str(quote.get("industry") or "N/A"), "neutral"),
            ("52W Range", f"{fmt_price(quote.get('fifty_two_week_low'))} - {fmt_price(quote.get('fifty_two_week_high'))}", "Latest provider range", "neutral"),
        ],
        columns=4,
        small=True,
    )
    section("Signal Center", "Transparent research score with factor breakdown, confidence, and missing-data warnings.")
    render_signal_summary(ticker, signal)
    section("Technical Entry Setup")
    render_entry_signal(ticker, quote, latest, options, signal)
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
    section("3-Statement Analysis", "Latest normalized statement metrics for the selected view.")
    render_statement_table(latest)
    section("Revenue, EPS, And Margins")
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
    section("News, Catalysts, And Macro Context", "Company-specific headlines are separated from broad market context where the source supports it.")
    news, news_statuses = fetch_news(ticker, 24)
    company_news = news[news.get("Scope", pd.Series(dtype=str)).eq("Company")] if not news.empty and "Scope" in news else pd.DataFrame()
    macro_news = news[news.get("Scope", pd.Series(dtype=str)).eq("Macro")] if not news.empty and "Scope" in news else pd.DataFrame()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Company Headlines")
        df_display(clean_news_table(company_news), height=300)
    with right:
        st.markdown("#### Macro / Market Headlines")
        df_display(clean_news_table(macro_news), height=300)
    macro, macro_status = fetch_macro_catalysts()
    render_metric_grid([(row["Theme"], row["Status"], row["Catalyst"], "neutral") for _, row in macro.iterrows()], columns=3, small=True)
    with st.expander("Catalyst source status"):
        st.json({"news_sources": news_statuses, "macro_source": macro_status})
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
    fig = go.Figure(go.Bar(x=score_frame["Category"], y=score_frame["Score"], marker_color="#7dd3fc", text=score_frame["Score"].round(1), textposition="outside", cliponaxis=False))
    fig = plotly_layout(fig, height=360)
    fig.update_yaxes(range=[0, 105], title="Score")
    st.plotly_chart(fig, use_container_width=True)
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
    st.markdown('<div class="terminal-subtitle">SQLite watchlist, signal-change alerts, and options/volatility monitor.</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        new_ticker = st.text_input("Add ticker", placeholder="CRWV")
        if st.button("Add"):
            if add_ticker(new_ticker):
                st.success(f"Added {clean_ticker(new_ticker)}")
                st.rerun()
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
    section("Volatility / Options Monitor", "Scans the selected ticker plus watchlist tickers. Missing options data is shown as a clean status, not a crash.")
    watch = list_watchlist()
    universe = [ticker] + [t for t in watch.get("ticker", pd.Series(dtype=str)).tolist() if t != ticker]
    max_names = st.slider("Max tickers to scan", 5, 30, min(12, len(universe) or 12), step=1, key="watchlist_options_max")
    with st.spinner("Loading options summaries..."):
        df_display(options_monitor_frame(universe[:max_names]), height=460)
    with st.expander("Options debug details"):
        debug = []
        for symbol in universe[:max_names]:
            quote = fetch_quote(symbol)
            opts = fetch_options_summary(symbol, quote.get("price"))
            debug.append({"ticker": symbol, "status": opts.get("status"), "seven_day": opts.get("seven_day"), "thirty_day": opts.get("thirty_day")})
        st.json(debug)


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
    key = openai_key_from_secrets(st.secrets)
    model = "gpt-4o-mini"
    try:
        model = st.secrets.get("OPENAI_MODEL", model)
    except Exception:
        pass
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
    try:
        openai_status = "OK" if st.secrets.get("OPENAI_API_KEY") else "Missing"
    except Exception:
        openai_status = "Missing"
    health = pd.DataFrame(
        [
            {"Source": "Yahoo Finance/yfinance quote", "Status": quote.get("status"), "Last Refresh": quote.get("last_updated"), "Cache TTL": "5 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": quote.get("error", "")},
            {"Source": "Company identity / logo", "Status": identity.get("logo_status"), "Last Refresh": identity.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": identity.get("error", "")},
            {"Source": "Yahoo Finance/yfinance financials", "Status": financials.get("status"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(financials.get("missing_fields", [])), "Error": financials.get("error", "")},
            {"Source": "Latest quarterly release", "Status": latest_release.get("source_status"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("data_quality_note", "")},
            {"Source": "Latest cards source", "Status": latest_release.get("source_status"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("reported_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("source_status_reason", "")},
            {"Source": "Yahoo Finance/yfinance options", "Status": opts.get("status"), "Last Refresh": opts.get("last_updated"), "Cache TTL": "30 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": opts.get("debug_error", "")},
            {"Source": "Yahoo Finance/RSS news", "Status": "OK" if not news.empty else "Partial", "Last Refresh": now_et(), "Cache TTL": "30 minutes", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": ""},
            {"Source": "SEC ticker-to-CIK mapping", "Status": cik_status.get("Status"), "Last Refresh": cik_status.get("Last Updated"), "Cache TTL": "24 hours", "Filing Period": "", "Structured Period": "", "Missing Fields": "", "Error": cik_status.get("Error", "")},
            {"Source": "SEC latest filing metadata", "Status": sec_latest.get("source_status"), "Last Refresh": sec_latest.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": sec_latest.get("filing_period_label", ""), "Structured Period": "", "Missing Fields": "", "Error": sec_latest.get("error", "")},
            {"Source": "SEC latest period-bearing filing", "Status": sec_periodic.get("source_status"), "Last Refresh": sec_periodic.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": sec_periodic.get("filing_period_label", ""), "Structured Period": "", "Missing Fields": "", "Error": sec_periodic.get("error", "")},
            {"Source": "SEC companyfacts", "Status": (latest_release.get("sec_companyfacts_status") or {}).get("Status", "N/A"), "Last Refresh": (latest_release.get("sec_companyfacts_status") or {}).get("Last Updated", latest_release.get("last_updated")), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": (latest_release.get("sec_companyfacts_status") or {}).get("Error", "")},
            {"Source": "SEC structured value extraction", "Status": latest_release.get("sec_value_extraction_status", "N/A"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": ", ".join(latest_release.get("missing_fields", [])), "Error": latest_release.get("data_quality_note", "")},
            {"Source": "Period alignment", "Status": latest_release.get("period_alignment_status", "N/A"), "Last Refresh": latest_release.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": latest_release.get("data_quality_note", "")},
            {"Source": "Financial chart source", "Status": financials.get("source_metadata", {}).get("chart_source_status", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": financials.get("source_metadata", {}).get("chart_source_note", "")},
            {"Source": "Missing metric periods", "Status": "Partial" if reconciliation.get("missing_chart_fields") or reconciliation.get("missing_metric_periods") else "OK", "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "; ".join((reconciliation.get("missing_chart_fields") or []) + (reconciliation.get("missing_metric_periods") or [])), "Error": ""},
            {"Source": "Margin calculation validity", "Status": financials.get("source_metadata", {}).get("margin_validity", "N/A"), "Last Refresh": financials.get("last_updated"), "Cache TTL": "24 hours", "Filing Period": latest_release.get("filing_period_label", ""), "Structured Period": latest_release.get("structured_values_period_label", ""), "Missing Fields": "", "Error": " ".join(reconciliation.get("margin_notes", []))},
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
    st.sidebar.markdown("## Research Terminal 2.0")
    st.sidebar.caption("V1 MVP")
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
