from __future__ import annotations

from datetime import date
from html import escape
from math import log10

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.financials import load_latest_company_financials
from pineterminal.components import money, percent, price, tone_for_value
from services.competitive_intelligence_service import fetch_competitive_intelligence
from utils.formatting import fmt_date, to_float
from utils.rendering import render_html


def _format_margin(value: float | None) -> str:
    return percent(value, 1, signed=False) if value is not None else "N/A"


def _financial_history(financials: dict) -> tuple[pd.DataFrame, bool]:
    quarterly = financials.get("quarterly_history")
    if isinstance(quarterly, pd.DataFrame) and not quarterly.empty:
        return quarterly.tail(8).copy(), True
    annual = financials.get("annual_history")
    if isinstance(annual, pd.DataFrame) and not annual.empty:
        return annual.tail(8).copy(), False
    return pd.DataFrame(), False


def _numeric_series(frame: pd.DataFrame, key: str) -> pd.Series:
    if frame.empty or key not in frame:
        return pd.Series(float("nan"), index=frame.index, dtype=float)
    return pd.to_numeric(frame[key], errors="coerce")


def _money_scale(*series: pd.Series) -> tuple[float, str]:
    values = pd.concat([value.dropna().abs() for value in series if isinstance(value, pd.Series)], ignore_index=True)
    maximum = float(values.max()) if not values.empty else 0.0
    if maximum >= 1_000_000_000:
        return 1_000_000_000, "$B"
    if maximum >= 1_000_000:
        return 1_000_000, "$M"
    if maximum >= 1_000:
        return 1_000, "$K"
    return 1.0, "$"


def _chart_periods(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return []
    if "period" in frame:
        return [str(value) for value in frame["period"]]
    return [f"P{index + 1}" for index in range(len(frame))]


def _apply_terminal_chart_layout(figure: go.Figure, height: int = 300) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=48, r=46, t=42, b=42),
        paper_bgcolor="#070c0f",
        plot_bgcolor="#070c0f",
        font=dict(family="IBM Plex Mono, Consolas, monospace", color="#aeb8be", size=10),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#111a20", bordercolor="#3a4650", font_color="#edf2f5"),
        legend=dict(orientation="h", x=0, y=1.14, bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        bargap=0.28,
        barmode="group",
    )
    figure.update_xaxes(showgrid=False, linecolor="#354049", tickfont=dict(color="#85929a"), fixedrange=True)
    figure.update_yaxes(gridcolor="#202a31", zerolinecolor="#53616a", tickfont=dict(color="#85929a"), fixedrange=True)
    return figure


def _latest_value(frame: pd.DataFrame, key: str) -> float | None:
    values = _numeric_series(frame, key).dropna()
    return to_float(values.iloc[-1]) if not values.empty else None


def _period_change(frame: pd.DataFrame, key: str, quarterly: bool) -> float | None:
    values = _numeric_series(frame, key).dropna()
    if len(values) < 2:
        return None
    prior_index = -5 if quarterly and len(values) >= 5 else 0
    return to_float(values.iloc[-1] - values.iloc[prior_index])


def _period_growth(frame: pd.DataFrame, key: str, quarterly: bool) -> float | None:
    values = _numeric_series(frame, key).dropna()
    if len(values) < 2:
        return None
    prior_index = -5 if quarterly and len(values) >= 5 else 0
    prior = to_float(values.iloc[prior_index])
    latest = to_float(values.iloc[-1])
    return (latest / prior - 1) * 100 if latest is not None and prior not in (None, 0) else None


def _figure_tile(label: str, value: str, context: str, tone: str = "neutral") -> str:
    return f'<div class="pt-decision-figure"><span>{escape(label)}</span><strong class="{escape(tone)}">{escape(value)}</strong><small>{escape(context)}</small></div>'


def _estimate_value(frame: object, period: str, column: str) -> float | None:
    if not isinstance(frame, pd.DataFrame) or frame.empty or column not in frame or period not in frame.index:
        return None
    value = frame.loc[period, column]
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    return to_float(value)


def _multiple(value: float | None, label: str = "x") -> str:
    return f"{value:.1f}{label}" if value is not None and value > 0 else "N/M"


def _signed_money(value: float | None) -> str:
    if value is None:
        return "N/A"
    prefix = "-" if value < 0 else ""
    return prefix + money(abs(value))


def _terminal_rows(rows: list[tuple[str, str, str, str]]) -> str:
    return "".join(
        f'<div class="pt-analyst-row"><span>{escape(label)}</span><strong class="{escape(tone)}">{escape(value)}</strong><small>{escape(context)}</small></div>'
        for label, value, context, tone in rows
    )


def _analyst_monitor_panels(analysis, financials: dict, frame: pd.DataFrame, quarterly: bool) -> str:
    latest = financials.get("latest_financials") or {}
    quote = financials.get("latest_quote") or {}
    earnings = financials.get("latest_reported_earnings") or {}
    eps_estimates = financials.get("analyst_estimates")
    revenue_estimates = financials.get("consensus_revenue")

    revenue = to_float(latest.get("revenue"))
    revenue_yoy = to_float(latest.get("revenue_yoy_growth"))
    revenue_qoq = to_float(latest.get("revenue_qoq_growth"))
    gross_margin = to_float(latest.get("gross_margin"))
    gross_margin_change = _period_change(frame, "gross_margin", quarterly)
    eps_actual = to_float(earnings.get("eps_actual"))
    eps_estimate = to_float(earnings.get("eps_estimate"))
    eps_surprise = to_float(earnings.get("eps_surprise_pct"))
    fcf = to_float(latest.get("free_cash_flow"))

    next_q_revenue = _estimate_value(revenue_estimates, "0q", "avg")
    next_q_low = _estimate_value(revenue_estimates, "0q", "low")
    next_q_high = _estimate_value(revenue_estimates, "0q", "high")
    next_q_growth = _estimate_value(revenue_estimates, "0q", "growth")
    next_q_analysts = _estimate_value(revenue_estimates, "0q", "numberOfAnalysts")
    fy0_revenue = _estimate_value(revenue_estimates, "0y", "avg")
    fy0_growth = _estimate_value(revenue_estimates, "0y", "growth")
    fy1_revenue = _estimate_value(revenue_estimates, "+1y", "avg")
    fy1_growth = _estimate_value(revenue_estimates, "+1y", "growth")
    fy0_eps = _estimate_value(eps_estimates, "0y", "avg")
    fy1_eps = _estimate_value(eps_estimates, "+1y", "avg")
    fy1_eps_analysts = _estimate_value(eps_estimates, "+1y", "numberOfAnalysts")

    market_cap = to_float(quote.get("market_cap")) or to_float(analysis.company.market_cap)
    enterprise_value = to_float(quote.get("enterprise_value")) or to_float(analysis.company.enterprise_value)
    quarterly_revenue = _numeric_series(frame.tail(4), "revenue").dropna()
    ttm_revenue = to_float(quarterly_revenue.sum()) if len(quarterly_revenue) == 4 else None
    ev_sales = enterprise_value / ttm_revenue if enterprise_value is not None and ttm_revenue not in (None, 0) else to_float(quote.get("price_to_sales"))
    free_cash_flow = to_float(quote.get("free_cash_flow"))
    fcf_yield = free_cash_flow / market_cap * 100 if free_cash_flow is not None and market_cap not in (None, 0) else None
    cash = to_float(latest.get("cash")) or to_float(quote.get("total_cash"))
    debt = to_float(latest.get("total_debt")) or to_float(quote.get("total_debt"))
    net_cash = cash - debt if cash is not None and debt is not None else None
    target = to_float(quote.get("target_mean_price"))
    current_price = to_float(quote.get("price")) or to_float(analysis.company.current_price)
    target_upside = ((target / current_price) - 1) * 100 if target is not None and current_price not in (None, 0) else None
    street_rating = str(quote.get("recommendation") or "Unavailable").replace("_", " ").title()
    next_earnings = quote.get("next_earnings_date")
    next_earnings_valid = next_earnings if isinstance(next_earnings, date) and next_earnings >= date.today() else None
    completeness = to_float((financials.get("source_metadata") or {}).get("financial_data_completeness"))

    results_rows = [
        ("Revenue", money(revenue) if revenue is not None else "N/A", f"{percent(revenue_yoy, 1)} YoY | {percent(revenue_qoq, 1)} QoQ", tone_for_value(revenue_yoy)),
        ("EPS vs Consensus", f"{eps_actual:.2f}" if eps_actual is not None else "N/A", f"Street {eps_estimate:.2f} | surprise {percent(eps_surprise, 1)}" if eps_estimate is not None else "Consensus unavailable", tone_for_value(eps_surprise)),
        ("Gross Margin", _format_margin(gross_margin), f"{gross_margin_change:+.1f} pts YoY" if gross_margin_change is not None else "Comparable period unavailable", tone_for_value(gross_margin_change)),
        ("Free Cash Flow", _signed_money(fcf), f"{_format_margin(to_float(latest.get('fcf_margin')))} of revenue", tone_for_value(fcf)),
    ]
    estimate_rows = [
        ("Next-Q Revenue", money(next_q_revenue) if next_q_revenue is not None else "N/A", f"Range {money(next_q_low)}-{money(next_q_high)} | {int(next_q_analysts)} analysts" if next_q_low is not None and next_q_high is not None and next_q_analysts is not None else "Consensus range unavailable", tone_for_value(next_q_growth)),
        ("FY0 Revenue", money(fy0_revenue) if fy0_revenue is not None else "N/A", f"{percent((fy0_growth or 0) * 100, 1)} expected growth" if fy0_growth is not None else "Growth estimate unavailable", tone_for_value(fy0_growth)),
        ("FY1 Revenue", money(fy1_revenue) if fy1_revenue is not None else "N/A", f"{percent((fy1_growth or 0) * 100, 1)} expected growth" if fy1_growth is not None else "Growth estimate unavailable", tone_for_value(fy1_growth)),
        ("FY1 EPS", f"{fy1_eps:.2f}" if fy1_eps is not None else "N/A", f"FY0 {fy0_eps:.2f} | {int(fy1_eps_analysts)} analysts" if fy0_eps is not None and fy1_eps_analysts is not None else "Consensus breadth unavailable", "good" if fy1_eps is not None and fy1_eps > 0 else "warn"),
    ]
    valuation_rows = [
        ("EV / TTM Sales", _multiple(ev_sales), f"EV {money(enterprise_value)} | TTM revenue {money(ttm_revenue)}", "warn" if ev_sales is not None and ev_sales > 10 else "neutral"),
        ("Forward P/E", _multiple(to_float(quote.get("forward_pe"))), "Meaningful only if forward EPS is positive", "warn"),
        ("FCF Yield", percent(fcf_yield, 1), "Negative yield signals external funding risk", tone_for_value(fcf_yield)),
        ("Net Cash / Debt", money(net_cash) if net_cash is not None else "N/A", f"{percent(net_cash / enterprise_value * 100, 1)} of EV" if net_cash is not None and enterprise_value not in (None, 0) else "Balance-sheet share of EV unavailable", tone_for_value(net_cash)),
    ]
    catalyst_rows = [
        ("Latest Results", fmt_date(earnings.get("earnings_date")), str(earnings.get("fiscal_period") or "Reported period"), "neutral"),
        ("Next Earnings", fmt_date(next_earnings_valid) if next_earnings_valid else "N/A", "Provider date is historical" if next_earnings and not next_earnings_valid else "Scheduled event", "warn" if not next_earnings_valid else "good"),
        ("Street Target", price(target) if target is not None else "N/A", f"{percent(target_upside, 1)} implied upside | {street_rating}", tone_for_value(target_upside)),
        ("Data Coverage", f"{completeness:.0f}%" if completeness is not None else "N/A", str(financials.get("status") or "Unknown"), "good" if completeness is not None and completeness >= 95 else "warn"),
    ]
    return (
        '<div class="pt-terminal-command-strip"><b>FA</b> Fundamentals <i>|</i> <b>EE</b> Estimates <i>|</i> <b>RV</b> Relative Value <i>|</i> <b>ANR</b> Consensus <i>|</i> <b>CAT</b> Catalysts</div>'
        '<div class="pt-analyst-monitor-grid">'
        f'<section><header><span>REPORTED RESULTS</span><small>{escape(str(earnings.get("fiscal_period") or "Latest quarter"))}</small></header>{_terminal_rows(results_rows)}</section>'
        f'<section><header><span>STREET ESTIMATES</span><small>Forward consensus</small></header>{_terminal_rows(estimate_rows)}</section>'
        f'<section><header><span>VALUATION / FUNDING</span><small>Market-implied risk</small></header>{_terminal_rows(valuation_rows)}</section>'
        f'<section><header><span>CATALYST / CONSENSUS</span><small>Event monitor</small></header>{_terminal_rows(catalyst_rows)}</section>'
        '</div>'
    )


def _revenue_consensus_figure(frame: pd.DataFrame, financials: dict) -> go.Figure | None:
    if frame.empty:
        return None
    actual = _numeric_series(frame.tail(6), "revenue")
    periods = _chart_periods(frame.tail(6))
    estimates = financials.get("consensus_revenue")
    estimate_values = [_estimate_value(estimates, "0q", "avg"), _estimate_value(estimates, "+1q", "avg")]
    estimate_lows = [_estimate_value(estimates, "0q", "low"), _estimate_value(estimates, "+1q", "low")]
    estimate_highs = [_estimate_value(estimates, "0q", "high"), _estimate_value(estimates, "+1q", "high")]
    divisor, unit = _money_scale(actual, pd.Series([value for value in estimate_values if value is not None], dtype=float))
    figure = go.Figure()
    if not actual.dropna().empty:
        figure.add_trace(go.Bar(x=periods, y=actual / divisor, name="Reported", marker_color="#36a9e1", hovertemplate=f"%{{x}}<br>Revenue: {unit}%{{y:,.1f}}<extra></extra>"))
    valid_estimates = [(label, value, low, high) for label, value, low, high in zip(("Next Q Est.", "Q+2 Est."), estimate_values, estimate_lows, estimate_highs) if value is not None]
    if valid_estimates:
        figure.add_trace(
            go.Bar(
                x=[item[0] for item in valid_estimates],
                y=[item[1] / divisor for item in valid_estimates],
                name="Consensus",
                marker_color="#d69a2d",
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[max(0, (item[3] - item[1]) / divisor) if item[3] is not None else 0 for item in valid_estimates],
                    arrayminus=[max(0, (item[1] - item[2]) / divisor) if item[2] is not None else 0 for item in valid_estimates],
                    color="#f0c969",
                ),
                hovertemplate=f"%{{x}}<br>Consensus revenue: {unit}%{{y:,.1f}}<extra></extra>",
            )
        )
    figure.update_yaxes(title_text=f"Revenue ({unit})")
    figure.update_layout(title=dict(text="REVENUE: REPORTED / CONSENSUS", x=0.01, font=dict(size=11, color="#d69a2d")))
    return _apply_terminal_chart_layout(figure, height=285)


def _margin_progression_figure(frame: pd.DataFrame) -> go.Figure | None:
    if frame.empty:
        return None
    periods = _chart_periods(frame)
    figure = go.Figure()
    traces = (("gross_margin", "Gross Margin", "#48c97a"), ("operating_margin", "Operating Margin", "#36a9e1"), ("fcf_margin", "FCF Margin", "#ee6670"))
    for key, label, color in traces:
        values = _numeric_series(frame, key)
        if values.dropna().empty:
            continue
        figure.add_trace(go.Scatter(x=periods, y=values, name=label, mode="lines+markers", line=dict(color=color, width=2), marker=dict(size=5), hovertemplate=f"%{{x}}<br>{label}: %{{y:.1f}}%<extra></extra>"))
    if not figure.data:
        return None
    figure.add_hline(y=0, line_color="#65737b", line_width=1)
    figure.update_yaxes(title_text="Margin", ticksuffix="%")
    figure.update_layout(title=dict(text="MARGIN / CASH CONVERSION", x=0.01, font=dict(size=11, color="#d69a2d")))
    return _apply_terminal_chart_layout(figure, height=285)


def _company_decision_figures(frame: pd.DataFrame, quarterly: bool, analysis, financials: dict | None = None) -> str:
    financials = financials or {}
    latest = financials.get("latest_financials") or {}
    quote = financials.get("latest_quote") or {}
    estimates = financials.get("consensus_revenue")
    revenue_growth = _period_growth(frame, "revenue", quarterly)
    gross_margin = _latest_value(frame, "gross_margin")
    gross_margin_change = _period_change(frame, "gross_margin", quarterly)
    operating_margin = _latest_value(frame, "operating_margin")
    fcf = _latest_value(frame, "free_cash_flow")
    fcf_margin = _latest_value(frame, "fcf_margin")
    cash = _latest_value(frame, "cash")
    debt = _latest_value(frame, "total_debt")
    net_cash = cash - debt if cash is not None and debt is not None else None
    runway = (cash / abs(fcf * 4)) if quarterly and cash is not None and fcf is not None and fcf < 0 else (cash / abs(fcf)) if cash is not None and fcf is not None and fcf < 0 else None
    shares = to_float(analysis.company.shares_outstanding)
    enterprise_value = to_float(quote.get("enterprise_value")) or to_float(analysis.company.enterprise_value)
    quarterly_revenue = _numeric_series(frame.tail(4), "revenue").dropna()
    ttm_revenue = to_float(quarterly_revenue.sum()) if len(quarterly_revenue) == 4 else None
    ev_sales = enterprise_value / ttm_revenue if enterprise_value is not None and ttm_revenue not in (None, 0) else None
    fcf_ttm = to_float(quote.get("free_cash_flow"))
    market_cap = to_float(quote.get("market_cap")) or to_float(analysis.company.market_cap)
    fcf_yield = fcf_ttm / market_cap * 100 if fcf_ttm is not None and market_cap not in (None, 0) else None
    fy1_growth = _estimate_value(estimates, "+1y", "growth")
    earnings = financials.get("latest_reported_earnings") or {}
    eps_surprise = to_float(earnings.get("eps_surprise_pct"))
    tiles = [
        _figure_tile("Revenue Growth", percent(revenue_growth, 1) if revenue_growth is not None else "N/A", "YoY" if quarterly and len(frame) >= 5 else "vs earliest available", tone_for_value(revenue_growth)),
        _figure_tile("Gross Margin", _format_margin(gross_margin), f"{gross_margin_change:+.1f} pts vs prior year" if gross_margin_change is not None else "Comparable history unavailable", tone_for_value(gross_margin_change)),
        _figure_tile("Operating Margin", _format_margin(operating_margin), "Current reported period", tone_for_value(operating_margin)),
        _figure_tile("EPS Surprise", percent(eps_surprise, 1), "Latest reported result vs consensus", tone_for_value(eps_surprise)),
        _figure_tile("FY1 Revenue Growth", percent((fy1_growth or 0) * 100, 1) if fy1_growth is not None else "N/A", "Street consensus", tone_for_value(fy1_growth)),
        _figure_tile("EV / Sales", _multiple(ev_sales), "TTM reported revenue", "warn" if ev_sales is not None and ev_sales > 10 else "neutral"),
        _figure_tile("FCF Yield", percent(fcf_yield, 1), f"Runway {runway:.1f}y" if runway is not None else "Self-funding or unavailable", tone_for_value(fcf_yield)),
        _figure_tile("Net Cash / Debt", money(net_cash) if net_cash is not None else "N/A", f"Shares {shares / 1_000_000:.1f}M" if shares is not None else "Share count unavailable", tone_for_value(net_cash)),
    ]
    return f'<div class="pt-decision-figures">{"".join(tiles)}</div>'


def _thesis_workbench(analysis, frame: pd.DataFrame, quarterly: bool) -> str:
    signal = analysis.investment_signal
    revenue_growth = _period_growth(frame, "revenue", quarterly)
    gross_margin = _latest_value(frame, "gross_margin")
    evidence_parts = []
    if revenue_growth is not None:
        evidence_parts.append(f"revenue {percent(revenue_growth, 1)}")
    if gross_margin is not None:
        evidence_parts.append(f"gross margin {_format_margin(gross_margin)}")
    evidence = ", ".join(evidence_parts) or "reported operating evidence is incomplete"
    base_case = next((item for item in analysis.valuation_scenarios if item.name == "Base Case"), None)
    valuation = base_case.assumption if base_case else "Base-case assumptions require review."
    primary_risk = analysis.risks[0] if analysis.risks else None
    risk = f"{primary_risk.risk_name}: {primary_risk.description}" if primary_risk else "No ranked risk available."
    upgrade = signal.upgrade_triggers[0] if signal.upgrade_triggers else (analysis.what_must_be_true[0].description if analysis.what_must_be_true else "New operating evidence above the base case.")
    downgrade = signal.downgrade_triggers[0] if signal.downgrade_triggers else (primary_risk.description if primary_risk else "Base-case evidence fails to materialize.")
    expected_return = analysis.expected_value_detail.expected_return
    rows = [
        ("Current Call", f"{signal.signal} | {percent(expected_return, 0)} modeled 36M return | {signal.conviction} conviction"),
        ("Reported Proof", evidence.capitalize() + "."),
        ("Valuation Bridge", valuation),
        ("Primary Risk", risk),
        ("Upgrade Evidence", upgrade),
        ("Invalidation", downgrade),
    ]
    markup = "".join(f'<div><span>{escape(label)}</span><p>{escape(value)}</p></div>' for label, value in rows)
    return f'<div class="pt-thesis-workbench"><div class="pt-thesis-workbench-head"><span>THESIS WORKBENCH</span><strong>Evidence ready for an investment memo</strong><small>Model output, not investment advice</small></div><div class="pt-thesis-workbench-grid">{markup}</div></div>'


def _render_company_visual_research(analysis, financials: dict) -> None:
    frame, quarterly = _financial_history(financials)
    if frame.empty:
        render_html('<div class="pt-shell pt-chart-empty"><strong>FUNDAMENTAL TREND MONITOR</strong><p>No reliable financial history is available for charting.</p></div>')
        return
    revenue_figure = _revenue_consensus_figure(frame, financials)
    margin_figure = _margin_progression_figure(frame)
    with st.container(border=True):
        render_html('<div class="pt-chart-anchor"><span>FA / EE / RV</span><h2>Analyst Monitor</h2><p>Reported results, forward consensus, valuation, funding risk, and catalysts in one decision surface.</p></div>' + _analyst_monitor_panels(analysis, financials, frame, quarterly))
        chart_columns = st.columns(2)
        with chart_columns[0]:
            if revenue_figure is not None:
                st.plotly_chart(revenue_figure, use_container_width=True, config={"displayModeBar": False}, key=f"revenue_consensus_{analysis.company.ticker}")
            else:
                st.info("Revenue history and consensus estimates are unavailable.")
        with chart_columns[1]:
            if margin_figure is not None:
                st.plotly_chart(margin_figure, use_container_width=True, config={"displayModeBar": False}, key=f"margin_progression_{analysis.company.ticker}")
            else:
                st.info("Margin and cash-conversion history are unavailable.")
        render_html(_company_decision_figures(frame, quarterly, analysis, financials) + _thesis_workbench(analysis, frame, quarterly))


def render_long_term_company_stats(analysis) -> None:
    financials = load_latest_company_financials(analysis.company.ticker)
    _render_company_visual_research(analysis, financials)


def _fmt_peer_percent(value: object, fractional: bool = False) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if fractional:
        number *= 100
    return percent(number, 1)


def _peer_tone(label: str) -> str:
    return "good" if label == "Leading" else "warn" if label == "Competitive" else "bad" if label == "Lagging" else "neutral"


def _peer_narrative(symbol: str, frame: pd.DataFrame) -> str:
    selected = frame.loc[frame["ticker"] == symbol]
    peers = frame.loc[frame["ticker"] != symbol]
    if selected.empty or peers.empty:
        return "Peer-relative evidence is incomplete. PineTerminal will show unavailable fields rather than infer missing performance."
    row = selected.iloc[0]
    parts = []
    for key, label, fractional, lower_is_better in (
        ("return_3m", "three-month price performance", False, False),
        ("revenue_growth", "revenue growth", True, False),
        ("gross_margin", "gross margin", True, False),
        ("fcf_yield", "free-cash-flow yield", False, False),
        ("ev_to_sales", "EV/Sales", False, True),
    ):
        if key not in peers:
            continue
        value = to_float(row.get(key))
        median = pd.to_numeric(peers[key], errors="coerce").median()
        if value is None or pd.isna(median):
            continue
        display_value = value * 100 if fractional else value
        display_median = float(median) * 100 if fractional else float(median)
        relation = "below" if display_value < display_median else "above"
        favorable = (display_value < display_median) if lower_is_better else (display_value > display_median)
        suffix = "x" if key == "ev_to_sales" else "%"
        parts.append(f"{label} is {relation} the peer median ({display_value:.1f}{suffix} vs {display_median:.1f}{suffix}; {'favorable' if favorable else 'unfavorable'})")
    return ("; ".join(parts) + ".") if parts else "Comparable peer metrics are not yet sufficiently complete for a reliable relative read."


def _peer_positioning_figure(symbol: str, frame: pd.DataFrame) -> go.Figure | None:
    if frame.empty:
        return None
    def peer_column(key: str) -> pd.Series:
        if key not in frame:
            return pd.Series(float("nan"), index=frame.index, dtype=float)
        return pd.to_numeric(frame[key], errors="coerce")

    growth = peer_column("revenue_growth") * 100
    margin = peer_column("gross_margin") * 100
    complete = frame.loc[growth.notna() & margin.notna()].copy()
    if len(complete) >= 2:
        complete["growth_pct"] = growth.loc[complete.index]
        complete["margin_pct"] = margin.loc[complete.index]
        market_cap = peer_column("market_cap").loc[complete.index]
        if market_cap.notna().any():
            logged = market_cap.clip(lower=1).apply(lambda value: log10(value) if pd.notna(value) else float("nan"))
            spread = logged.max() - logged.min()
            sizes = 16 + ((logged - logged.min()) / spread * 18) if spread and pd.notna(spread) else pd.Series(24.0, index=complete.index)
            complete["marker_size"] = sizes.fillna(20)
        else:
            complete["marker_size"] = 20
        colors = ["#d69a2d" if ticker == symbol else "#36a9e1" for ticker in complete["ticker"]]
        outlines = ["#f4c65d" if ticker == symbol else "#1d6c91" for ticker in complete["ticker"]]
        companies = complete["company"] if "company" in complete else complete["ticker"]
        return_3m = pd.to_numeric(complete["return_3m"], errors="coerce") if "return_3m" in complete else pd.Series(float("nan"), index=complete.index)
        ev_sales = pd.to_numeric(complete["ev_to_sales"], errors="coerce") if "ev_to_sales" in complete else pd.Series(float("nan"), index=complete.index)
        figure = go.Figure(
            go.Scatter(
                x=complete["growth_pct"],
                y=complete["margin_pct"],
                text=complete["ticker"],
                customdata=pd.DataFrame({"company": companies, "return_3m": return_3m, "ev_to_sales": ev_sales}).to_numpy(),
                mode="markers+text",
                textposition="top center",
                textfont=dict(size=10, color="#dce4e8"),
                marker=dict(size=complete["marker_size"], color=colors, line=dict(color=outlines, width=1.5), opacity=0.88),
                hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Revenue growth: %{x:.1f}%<br>Gross margin: %{y:.1f}%<br>EV/Sales: %{customdata[2]:.1f}x<br>3M return: %{customdata[1]:.1f}%<extra></extra>",
                name="Peer set",
            )
        )
        x_median = float(complete["growth_pct"].median())
        y_median = float(complete["margin_pct"].median())
        figure.add_vline(x=x_median, line_width=1, line_dash="dot", line_color="#52616a")
        figure.add_hline(y=y_median, line_width=1, line_dash="dot", line_color="#52616a")
        figure.update_xaxes(title_text="Revenue Growth (TTM)", ticksuffix="%")
        figure.update_yaxes(title_text="Gross Margin (TTM)", ticksuffix="%")
        figure.update_layout(title=dict(text="PEER GROWTH / QUALITY POSITIONING", x=0.01, font=dict(size=11, color="#d69a2d")), showlegend=False)
        return _apply_terminal_chart_layout(figure, height=330)
    returns = peer_column("return_3m")
    available = frame.loc[returns.notna()].copy()
    if available.empty:
        return None
    available["return_3m_value"] = returns.loc[available.index]
    available = available.sort_values("return_3m_value")
    figure = go.Figure(
        go.Bar(
            x=available["return_3m_value"],
            y=available["ticker"],
            orientation="h",
            marker_color=["#d69a2d" if ticker == symbol else "#36a9e1" for ticker in available["ticker"]],
            hovertemplate="%{y}<br>3M return: %{x:.1f}%<extra></extra>",
        )
    )
    figure.update_xaxes(title_text="3M Return", ticksuffix="%")
    figure.update_layout(title=dict(text="PEER PRICE CONFIRMATION", x=0.01, font=dict(size=11, color="#d69a2d")), showlegend=False)
    return _apply_terminal_chart_layout(figure, height=300)


def _peer_decision_figures(symbol: str, frame: pd.DataFrame) -> str:
    selected = frame.loc[frame["ticker"] == symbol]
    peers = frame.loc[frame["ticker"] != symbol]
    if selected.empty:
        return '<div class="pt-decision-figures"><div class="pt-decision-figure"><span>Peer Read</span><strong>N/A</strong><small>Selected ticker data unavailable</small></div></div>'
    row = selected.iloc[0]
    tiles = []
    for key, label, fractional, lower_is_better in (
        ("return_3m", "3M Price", False, False),
        ("revenue_growth", "Revenue Growth", True, False),
        ("gross_margin", "Gross Margin", True, False),
        ("fcf_yield", "FCF Yield", False, False),
        ("ev_to_sales", "EV / Sales", False, True),
        ("target_upside", "Street Upside", False, False),
    ):
        value = to_float(row.get(key))
        peer_values = pd.to_numeric(peers[key], errors="coerce").dropna() if key in peers else pd.Series(dtype=float)
        median = to_float(peer_values.median()) if not peer_values.empty else None
        display = value * 100 if fractional and value is not None else value
        display_median = median * 100 if fractional and median is not None else median
        suffix = "x" if key == "ev_to_sales" else "%"
        value_label = f"{display:.1f}{suffix}" if display is not None else "N/A"
        if display is not None and display_median is not None:
            better = display < display_median if lower_is_better else display > display_median
            context = f"Peer median {display_median:.1f}{suffix}"
            tone = "good" if better else "bad"
        else:
            context, tone = "Peer comparison unavailable", "neutral"
        tiles.append(_figure_tile(label, value_label, context, tone))
    return f'<div class="pt-decision-figures pt-peer-figures">{"".join(tiles)}</div>'


def _peer_median(frame: pd.DataFrame, key: str) -> float | None:
    if key not in frame:
        return None
    values = pd.to_numeric(frame[key], errors="coerce").dropna()
    return to_float(values.median()) if not values.empty else None


def _peer_market_cap(value: object) -> str:
    number = to_float(value)
    return money(number) if number is not None else "N/A"


def render_competitive_intelligence(analysis) -> None:
    company = analysis.company
    frame, status = fetch_competitive_intelligence(company.ticker, company.sector, company.industry, tuple(company.themes))
    if frame.empty:
        render_html('<div class="pt-shell pt-company-research-shell"><div class="pt-research-head"><div><span>COMPETITIVE INTELLIGENCE</span><h2>Peer Performance</h2></div></div><p class="pt-placeholder">No reliable peer data available.</p></div>')
        return
    rows = []
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker") or "")
        is_selected = ticker == company.ticker
        relative = str(row.get("relative_read") or "Insufficient data")
        forward_pe = to_float(row.get("forward_pe"))
        ev_sales = to_float(row.get("ev_to_sales"))
        analyst_count = to_float(row.get("analyst_count"))
        street_rating = str(row.get("street_rating") or "N/A")
        rows.append(
            f"""
            <tr class="{'selected' if is_selected else ''}">
              <td><strong>{escape(ticker)}</strong><small>{escape(str(row.get('company') or ticker))}</small></td>
              <td>{_peer_market_cap(row.get('market_cap'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_3m')))}">{_fmt_peer_percent(row.get('return_3m'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_1y')))}">{_fmt_peer_percent(row.get('return_1y'))}</td>
              <td>{_fmt_peer_percent(row.get('revenue_growth'), True)}</td>
              <td>{_fmt_peer_percent(row.get('gross_margin'), True)}</td>
              <td>{_fmt_peer_percent(row.get('operating_margin'), True)}</td>
              <td class="{tone_for_value(to_float(row.get('fcf_yield')))}">{_fmt_peer_percent(row.get('fcf_yield'))}</td>
              <td>{_multiple(ev_sales)}</td>
              <td>{_multiple(forward_pe)}</td>
              <td class="{tone_for_value(to_float(row.get('target_upside')))}">{_fmt_peer_percent(row.get('target_upside'))}</td>
              <td><span class="pt-peer-badge {_peer_tone(relative)}">{escape(relative)}</span><small>{escape(street_rating)}{f' / {int(analyst_count)}' if analyst_count is not None else ''}</small></td>
            </tr>
            """
        )
    peers_only = frame.loc[frame["ticker"] != company.ticker]
    median_row = f"""
      <tr class="peer-median">
        <td><strong>PEER MEDIAN</strong><small>Excludes {escape(company.ticker)}</small></td>
        <td>{_peer_market_cap(_peer_median(peers_only, 'market_cap'))}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'return_3m'))}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'return_1y'))}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'revenue_growth'), True)}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'gross_margin'), True)}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'operating_margin'), True)}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'fcf_yield'))}</td>
        <td>{_multiple(_peer_median(peers_only, 'ev_to_sales'))}</td>
        <td>{_multiple(_peer_median(peers_only, 'forward_pe'))}</td>
        <td>{_fmt_peer_percent(_peer_median(peers_only, 'target_upside'))}</td>
        <td><span class="pt-peer-badge neutral">Reference</span></td>
      </tr>
    """
    peer_figure = _peer_positioning_figure(company.ticker, frame)
    with st.container(border=True):
        render_html(
            f'<div class="pt-chart-anchor pt-peer-chart-anchor"><span>COMP / RV</span><h2>Competitive Intelligence</h2><p>Growth, profitability, cash generation, relative valuation, price confirmation, and Street expectations.</p><div class="pt-chart-coverage"><span>Coverage</span><b>{status.get("symbols_loaded", 0)}/{status.get("symbols_requested", len(frame))}</b><small>{escape(str(status.get("status") or "Unknown"))}</small></div></div>'
        )
        if peer_figure is not None:
            st.plotly_chart(peer_figure, use_container_width=True, config={"displayModeBar": False}, key=f"peer_positioning_{company.ticker}")
        else:
            st.info("Peer chart requires at least two comparable companies.")
        render_html(
            _peer_decision_figures(company.ticker, frame)
            + f'<div class="pt-peer-table-wrap"><table class="pt-peer-table pt-comp-table"><thead><tr><th>Company</th><th>Mkt Cap</th><th>3M</th><th>1Y</th><th>Rev Gr</th><th>Gross Mgn</th><th>Op Mgn</th><th>FCF Yld</th><th>EV/Sales</th><th>Fwd P/E</th><th>Target</th><th>Street / Rank</th></tr></thead><tbody>{"".join(rows)}{median_row}</tbody></table></div>'
            + f'<div class="pt-peer-read"><span>Relative-Value Read</span><p>{escape(_peer_narrative(company.ticker, frame))}</p></div>'
            + f'<div class="pt-source-foot">{escape(str(status.get("source") or "Yahoo Finance/yfinance"))} | refreshed {escape(fmt_date(status.get("last_updated")))}</div>'
        )
