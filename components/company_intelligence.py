from __future__ import annotations

from html import escape
from math import log10

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data.financials import load_latest_company_financials
from pineterminal.components import money, percent, price, tone_for_signal, tone_for_value
from services.competitive_intelligence_service import fetch_competitive_intelligence
from utils.formatting import fmt_date, to_float
from utils.rendering import render_html


def _clean_values(frame: pd.DataFrame, key: str) -> list[tuple[str, float]]:
    if frame is None or frame.empty or key not in frame:
        return []
    rows: list[tuple[str, float]] = []
    for _, row in frame.tail(8).iterrows():
        value = to_float(row.get(key))
        if value is not None:
            rows.append((str(row.get("period") or "Period"), value))
    return rows


def _comparison(points: list[tuple[str, float]], quarterly: bool) -> tuple[float | None, str]:
    if len(points) < 2:
        return None, "History unavailable"
    comparison_index = -5 if quarterly and len(points) >= 5 else 0
    prior_label, prior = points[comparison_index]
    latest = points[-1][1]
    return latest - prior, f"vs {prior_label}"


def _trend(change: float | None, threshold: float, inverse: bool = False) -> tuple[str, str]:
    if change is None:
        return "Insufficient history", "neutral"
    adjusted = -change if inverse else change
    if adjusted > threshold:
        return "Improving", "good"
    if adjusted < -threshold:
        return "Deteriorating", "bad"
    return "Stable", "warn"


def _sparkline(points: list[tuple[str, float]], tone: str) -> str:
    values = [value for _, value in points[-6:]]
    if len(values) < 2:
        return '<div class="pt-trend-empty">No comparable history</div>'
    low, high = min(values), max(values)
    spread = high - low
    coords = []
    for index, value in enumerate(values):
        x = 4 + index * (92 / max(1, len(values) - 1))
        y = 30 if spread == 0 else 52 - ((value - low) / spread * 42)
        coords.append(f"{x:.1f},{y:.1f}")
    return f'<svg class="pt-trend-spark {tone}" viewBox="0 0 100 58" preserveAspectRatio="none" aria-hidden="true"><polyline points="{" ".join(coords)}"></polyline></svg>'


def _metric_card(label: str, current: str, comparison: str, status: str, tone: str, points: list[tuple[str, float]], interpretation: str) -> str:
    return f"""
    <div class="pt-lt-metric">
      <div class="pt-lt-metric-head"><span>{escape(label)}</span><b class="{tone}">{escape(status)}</b></div>
      <strong>{escape(current)}</strong>
      <small>{escape(comparison)}</small>
      {_sparkline(points, tone)}
      <p>{escape(interpretation)}</p>
    </div>
    """


def _format_margin(value: float | None) -> str:
    return percent(value, 1, signed=False) if value is not None else "N/A"


def _format_change(change: float | None, suffix: str, comparison_label: str) -> str:
    if change is None:
        return comparison_label
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}{suffix} {comparison_label}"


def _long_term_metrics(analysis, financials: dict) -> tuple[list[str], dict[str, int], str]:
    history = financials.get("quarterly_history")
    quarterly = isinstance(history, pd.DataFrame) and not history.empty
    if not quarterly:
        history = financials.get("annual_history")
    if not isinstance(history, pd.DataFrame):
        history = pd.DataFrame()
    cards: list[str] = []
    counts = {"good": 0, "warn": 0, "bad": 0, "neutral": 0}

    revenue = _clean_values(history, "revenue")
    revenue_change, revenue_compare = _comparison(revenue, quarterly)
    revenue_growth = (revenue_change / revenue[-5 if quarterly and len(revenue) >= 5 else 0][1] * 100) if revenue_change is not None and revenue[-5 if quarterly and len(revenue) >= 5 else 0][1] else None
    status, tone = _trend(revenue_growth, 5)
    counts[tone] += 1
    cards.append(_metric_card("Revenue", money(revenue[-1][1]) if revenue else "N/A", _format_change(revenue_growth, "%", revenue_compare), status, tone, revenue, "Sustained top-line growth expands the earnings base; small-base spikes need confirmation."))

    for label, key, threshold, interpretation in (
        ("Gross Margin", "gross_margin", 1.0, "Gross-margin expansion signals pricing power and improving unit economics."),
        ("Operating Margin", "operating_margin", 1.0, "Operating leverage matters more than revenue growth that never reaches the bottom line."),
        ("Free Cash Flow Margin", "fcf_margin", 1.0, "Positive and rising free cash flow reduces financing and dilution dependence."),
    ):
        points = _clean_values(history, key)
        change, compare = _comparison(points, quarterly)
        status, tone = _trend(change, threshold)
        counts[tone] += 1
        cards.append(_metric_card(label, _format_margin(points[-1][1]) if points else "N/A", _format_change(change, " pts", compare), status, tone, points, interpretation))

    net_cash_points = []
    cash = _clean_values(history, "cash")
    debt = _clean_values(history, "total_debt")
    debt_by_period = dict(debt)
    for period, cash_value in cash:
        if period in debt_by_period:
            net_cash_points.append((period, cash_value - debt_by_period[period]))
    net_cash_change, net_cash_compare = _comparison(net_cash_points, quarterly)
    status, tone = _trend(net_cash_change, max(abs(net_cash_points[-1][1]) * 0.05, 1.0) if net_cash_points else 1.0)
    counts[tone] += 1
    cards.append(_metric_card("Net Cash / Debt", money(net_cash_points[-1][1]) if net_cash_points else "N/A", (f"{money(net_cash_change)} {net_cash_compare}" if net_cash_change is not None else net_cash_compare), status, tone, net_cash_points, "Balance-sheet direction determines resilience and the need for outside capital."))

    shares = _clean_values(history, "shares_outstanding")
    current_shares = to_float(analysis.company.shares_outstanding)
    if current_shares is not None and (not shares or shares[-1][1] != current_shares):
        shares.append(("Current", current_shares))
    shares_change, shares_compare = _comparison(shares, quarterly=False)
    shares_growth = (shares_change / shares[0][1] * 100) if shares_change is not None and shares[0][1] else None
    status, tone = _trend(shares_growth, 3.0, inverse=True)
    counts[tone] += 1
    cards.append(_metric_card("Share Count", f"{current_shares / 1_000_000:.1f}M" if current_shares is not None else "N/A", _format_change(shares_growth, "%", shares_compare), status, tone, shares, "Per-share value can lag company growth when issuance persistently expands the share count."))

    period_label = str(history.iloc[-1].get("period") or "Latest filing") if not history.empty else "No reliable filing history"
    return cards, counts, period_label


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


def _operating_progression_figure(frame: pd.DataFrame) -> go.Figure | None:
    if frame.empty:
        return None
    periods = _chart_periods(frame)
    revenue = _numeric_series(frame, "revenue")
    gross_margin = _numeric_series(frame, "gross_margin")
    divisor, unit = _money_scale(revenue)
    if revenue.dropna().empty and gross_margin.dropna().empty:
        return None
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    if not revenue.dropna().empty:
        figure.add_trace(
            go.Bar(
                x=periods,
                y=revenue / divisor,
                name="Revenue",
                marker_color="#36a9e1",
                hovertemplate=f"%{{x}}<br>Revenue: {unit}%{{y:,.1f}}<extra></extra>",
            ),
            secondary_y=False,
        )
    if not gross_margin.dropna().empty:
        figure.add_trace(
            go.Scatter(
                x=periods,
                y=gross_margin,
                name="Gross Margin",
                mode="lines+markers",
                line=dict(color="#48c97a", width=2),
                marker=dict(size=6, color="#48c97a", line=dict(color="#07100b", width=1)),
                hovertemplate="%{x}<br>Gross margin: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )
    figure.update_yaxes(title_text=f"Revenue ({unit})", secondary_y=False)
    figure.update_yaxes(title_text="Gross Margin (%)", ticksuffix="%", secondary_y=True)
    figure.update_layout(title=dict(text="REVENUE SCALE / UNIT ECONOMICS", x=0.01, font=dict(size=11, color="#d69a2d")))
    return _apply_terminal_chart_layout(figure)


def _capital_discipline_figure(frame: pd.DataFrame) -> go.Figure | None:
    if frame.empty:
        return None
    periods = _chart_periods(frame)
    operating_income = _numeric_series(frame, "operating_income")
    free_cash_flow = _numeric_series(frame, "free_cash_flow")
    cash = _numeric_series(frame, "cash")
    debt = _numeric_series(frame, "total_debt")
    net_cash = cash - debt
    divisor, unit = _money_scale(operating_income, free_cash_flow, net_cash)
    if operating_income.dropna().empty and free_cash_flow.dropna().empty and net_cash.dropna().empty:
        return None
    figure = go.Figure()
    if not operating_income.dropna().empty:
        figure.add_trace(
            go.Bar(
                x=periods,
                y=operating_income / divisor,
                name="Operating Income",
                marker_color=["#36a9e1" if value >= 0 else "#9c4650" for value in operating_income.fillna(0)],
                hovertemplate=f"%{{x}}<br>Operating income: {unit}%{{y:,.1f}}<extra></extra>",
            )
        )
    if not free_cash_flow.dropna().empty:
        figure.add_trace(
            go.Bar(
                x=periods,
                y=free_cash_flow / divisor,
                name="Free Cash Flow",
                marker_color=["#48c97a" if value >= 0 else "#ee6670" for value in free_cash_flow.fillna(0)],
                hovertemplate=f"%{{x}}<br>Free cash flow: {unit}%{{y:,.1f}}<extra></extra>",
            )
        )
    if not net_cash.dropna().empty:
        figure.add_trace(
            go.Scatter(
                x=periods,
                y=net_cash / divisor,
                name="Net Cash / Debt",
                mode="lines+markers",
                line=dict(color="#d69a2d", width=2),
                marker=dict(size=6, color="#d69a2d"),
                hovertemplate=f"%{{x}}<br>Net cash / debt: {unit}%{{y:,.1f}}<extra></extra>",
            )
        )
    figure.update_yaxes(title_text=f"Reported Value ({unit})")
    figure.update_layout(title=dict(text="PROFIT CONVERSION / FUNDING RISK", x=0.01, font=dict(size=11, color="#d69a2d")))
    return _apply_terminal_chart_layout(figure)


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


def _company_decision_figures(frame: pd.DataFrame, quarterly: bool, analysis) -> str:
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
    tiles = [
        _figure_tile("Revenue Growth", percent(revenue_growth, 1) if revenue_growth is not None else "N/A", "YoY" if quarterly and len(frame) >= 5 else "vs earliest available", tone_for_value(revenue_growth)),
        _figure_tile("Gross Margin", _format_margin(gross_margin), f"{gross_margin_change:+.1f} pts vs prior year" if gross_margin_change is not None else "Comparable history unavailable", tone_for_value(gross_margin_change)),
        _figure_tile("Operating Margin", _format_margin(operating_margin), "Current reported period", tone_for_value(operating_margin)),
        _figure_tile("FCF Margin", _format_margin(fcf_margin), f"FCF {money(fcf)}" if fcf is not None else "FCF unavailable", tone_for_value(fcf_margin)),
        _figure_tile("Net Cash / Debt", money(net_cash) if net_cash is not None else "N/A", "Liquidity after reported debt", tone_for_value(net_cash)),
        _figure_tile("Cash Runway", f"{runway:.1f} yrs" if runway is not None else "Self-funding" if fcf is not None and fcf >= 0 else "N/A", "At current reported burn rate", "warn" if runway is not None and runway < 2 else "good" if runway is not None or (fcf is not None and fcf >= 0) else "neutral"),
        _figure_tile("Share Count", f"{shares / 1_000_000:.1f}M" if shares is not None else "N/A", "Monitor dilution per quarter", "warn"),
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
    operating_figure = _operating_progression_figure(frame)
    capital_figure = _capital_discipline_figure(frame)
    with st.container(border=True):
        render_html('<div class="pt-chart-anchor"><span>FUNDAMENTAL TREND MONITOR</span><h2>Operating Evidence in Motion</h2><p>Reported history only. Hover for period detail; figures below translate the chart into thesis evidence.</p></div>')
        chart_columns = st.columns(2)
        with chart_columns[0]:
            if operating_figure is not None:
                st.plotly_chart(operating_figure, use_container_width=True, config={"displayModeBar": False}, key=f"operating_progression_{analysis.company.ticker}")
            else:
                st.info("Revenue and margin history are unavailable.")
        with chart_columns[1]:
            if capital_figure is not None:
                st.plotly_chart(capital_figure, use_container_width=True, config={"displayModeBar": False}, key=f"capital_discipline_{analysis.company.ticker}")
            else:
                st.info("Cash-flow and balance-sheet history are unavailable.")
        render_html(_company_decision_figures(frame, quarterly, analysis) + _thesis_workbench(analysis, frame, quarterly))


def render_long_term_company_stats(analysis) -> None:
    financials = load_latest_company_financials(analysis.company.ticker)
    cards, counts, period_label = _long_term_metrics(analysis, financials)
    improving = counts["good"]
    deteriorating = counts["bad"]
    if improving > deteriorating:
        trend, trend_tone = "Progressing", "good"
    elif deteriorating > improving:
        trend, trend_tone = "Declining", "bad"
    else:
        trend, trend_tone = "Mixed", "warn"
    recommendation = analysis.investment_signal.signal
    recommendation_tone = tone_for_signal(recommendation)
    support = "supports" if trend_tone == "good" else "challenges" if trend_tone == "bad" else "does not yet fully confirm"
    source = (financials.get("source_metadata") or {}).get("financials") or "SEC XBRL / Yahoo Finance financial statements"
    render_html(
        f"""
        <div class="pt-shell pt-company-research-shell">
          <div class="pt-research-head">
            <div><span>LONG-TERM OPERATING TREND</span><h2>Progression That Matters</h2><p>Reported growth, margins, cash generation, balance-sheet direction, and per-share discipline.</p></div>
            <div class="pt-research-verdict"><span>Operating Evidence</span><b class="{trend_tone}">{trend}</b><small>{improving} improving / {deteriorating} deteriorating</small></div>
          </div>
          <div class="pt-lt-grid">{"".join(cards)}</div>
          <div class="pt-recommendation-read"><span>Read on Recommendation</span><strong class="{recommendation_tone}">{escape(recommendation)}</strong><p>The reported operating trend {support} the current recommendation. Valuation, catalysts, and risk controls remain separate inputs; social attention is not used as a standalone recommendation signal.</p></div>
          <div class="pt-source-foot">Through {escape(period_label)} | {escape(str(source))}</div>
        </div>
        """
    )
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
    for key, label, fractional in (("return_3m", "three-month price performance", False), ("revenue_growth", "revenue growth", True), ("gross_margin", "gross margin", True)):
        if key not in peers:
            continue
        value = to_float(row.get(key))
        median = pd.to_numeric(peers[key], errors="coerce").median()
        if value is None or pd.isna(median):
            continue
        display_value = value * 100 if fractional else value
        display_median = float(median) * 100 if fractional else float(median)
        relation = "above" if display_value > display_median else "below"
        parts.append(f"{label} is {relation} the peer median ({display_value:.1f}% vs {display_median:.1f}%)")
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
        figure = go.Figure(
            go.Scatter(
                x=complete["growth_pct"],
                y=complete["margin_pct"],
                text=complete["ticker"],
                customdata=complete[["company", "return_3m"]].to_numpy(),
                mode="markers+text",
                textposition="top center",
                textfont=dict(size=10, color="#dce4e8"),
                marker=dict(size=complete["marker_size"], color=colors, line=dict(color=outlines, width=1.5), opacity=0.88),
                hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Revenue growth: %{x:.1f}%<br>Gross margin: %{y:.1f}%<br>3M return: %{customdata[1]:.1f}%<extra></extra>",
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
    for key, label, fractional in (("return_3m", "3M Relative Return", False), ("revenue_growth", "Revenue Growth", True), ("gross_margin", "Gross Margin", True), ("price_to_sales", "Price / Sales", False)):
        value = to_float(row.get(key))
        peer_values = pd.to_numeric(peers[key], errors="coerce").dropna() if key in peers else pd.Series(dtype=float)
        median = to_float(peer_values.median()) if not peer_values.empty else None
        display = value * 100 if fractional and value is not None else value
        display_median = median * 100 if fractional and median is not None else median
        suffix = "x" if key == "price_to_sales" else "%"
        value_label = f"{display:.1f}{suffix}" if display is not None else "N/A"
        if display is not None and display_median is not None:
            better = display < display_median if key == "price_to_sales" else display > display_median
            context = f"Peer median {display_median:.1f}{suffix}"
            tone = "good" if better else "bad"
        else:
            context, tone = "Peer comparison unavailable", "neutral"
        tiles.append(_figure_tile(label, value_label, context, tone))
    relative = str(row.get("relative_read") or "Insufficient data")
    tiles.append(_figure_tile("Relative Read", relative, "Growth, quality, valuation, and price", _peer_tone(relative)))
    return f'<div class="pt-decision-figures pt-peer-figures">{"".join(tiles)}</div>'


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
        valuation = to_float(row.get("forward_pe"))
        sales_multiple = to_float(row.get("price_to_sales"))
        operating_margin = to_float(row.get("operating_margin"))
        valuation_label = (
            f"{valuation:.1f}x P/E"
            if valuation is not None and valuation > 0 and operating_margin is not None and operating_margin > 0
            else f"{sales_multiple:.1f}x P/S"
            if sales_multiple is not None
            else "N/A"
        )
        rows.append(
            f"""
            <tr class="{'selected' if is_selected else ''}">
              <td><strong>{escape(ticker)}</strong><small>{escape(str(row.get('company') or ticker))}</small></td>
              <td class="{tone_for_value(to_float(row.get('return_1m')))}">{_fmt_peer_percent(row.get('return_1m'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_3m')))}">{_fmt_peer_percent(row.get('return_3m'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_1y')))}">{_fmt_peer_percent(row.get('return_1y'))}</td>
              <td>{_fmt_peer_percent(row.get('revenue_growth'), True)}</td>
              <td>{_fmt_peer_percent(row.get('gross_margin'), True)}</td>
              <td>{_fmt_peer_percent(row.get('operating_margin'), True)}</td>
              <td>{escape(valuation_label)}</td>
              <td><span class="pt-peer-badge {_peer_tone(relative)}">{escape(relative)}</span></td>
            </tr>
            """
        )
    peer_figure = _peer_positioning_figure(company.ticker, frame)
    with st.container(border=True):
        render_html(
            f'<div class="pt-chart-anchor pt-peer-chart-anchor"><span>COMPETITIVE INTELLIGENCE</span><h2>Peer Performance</h2><p>Operating quality, valuation, and price confirmation against the closest available industry/theme cohort.</p><div class="pt-chart-coverage"><span>Coverage</span><b>{status.get("symbols_loaded", 0)}/{status.get("symbols_requested", len(frame))}</b><small>{escape(str(status.get("status") or "Unknown"))}</small></div></div>'
        )
        if peer_figure is not None:
            st.plotly_chart(peer_figure, use_container_width=True, config={"displayModeBar": False}, key=f"peer_positioning_{company.ticker}")
        else:
            st.info("Peer chart requires at least two comparable companies.")
        render_html(
            _peer_decision_figures(company.ticker, frame)
            + f'<div class="pt-peer-table-wrap"><table class="pt-peer-table"><thead><tr><th>Company</th><th>1M</th><th>3M</th><th>1Y</th><th>Rev Growth</th><th>Gross Mgn TTM</th><th>Op Mgn TTM</th><th>Valuation</th><th>Relative Read</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            + f'<div class="pt-peer-read"><span>Analyst Comparison</span><p>{escape(_peer_narrative(company.ticker, frame))}</p></div>'
            + f'<div class="pt-source-foot">{escape(str(status.get("source") or "Yahoo Finance/yfinance"))} | refreshed {escape(fmt_date(status.get("last_updated")))}</div>'
        )
