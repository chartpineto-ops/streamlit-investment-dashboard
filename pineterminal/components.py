from __future__ import annotations

from html import escape
from math import cos, pi, sin

import pandas as pd
import streamlit as st

from pineterminal.calculations import (
    calculate_expected_return,
    calculate_future_value_bridge,
    calculate_fundamental_score,
    calculate_net_readthrough_score,
)
from pineterminal.types import (
    CompanyAnalysis,
    CompanyProfile,
    FundamentalMetric,
    MarketReadThroughItem,
    SensitivityTable,
    ValuationModel,
    ValuationScenario,
)
from pineterminal.valuation import format_financial_value, get_scenario_labels_by_method, get_valuation_model
from utils.rendering import render_html


METRIC_BADGES = {
    "Revenue Growth": "RG",
    "Gross Margin": "GM",
    "Operating Leverage": "OL",
    "Free Cash Flow": "FCF",
    "Balance Sheet": "BS",
    "Customers / Backlog": "CB",
    "Competitive Position": "CP",
    "Execution Quality": "EQ",
}


def signal_visual(signal: str) -> dict[str, str]:
    states = {
        "Strong Buy": {"slug": "strong-buy", "tone": "good", "icon": "double-up"},
        "Buy": {"slug": "buy", "tone": "good", "icon": "up"},
        "Speculative Buy": {"slug": "speculative-buy", "tone": "good", "icon": "up-right"},
        "Hold": {"slug": "hold", "tone": "warn", "icon": "flat"},
        "Avoid": {"slug": "avoid", "tone": "bad", "icon": "down-right"},
        "Sell": {"slug": "sell", "tone": "bad", "icon": "down"},
    }
    return states.get(signal, {"slug": "neutral", "tone": "neutral", "icon": "flat"})


def svg_icon(name: str, extra_class: str = "") -> str:
    paths = {
        "double-up": '<path d="M7 13l5-5 5 5"/><path d="M7 19l5-5 5 5"/>',
        "up": '<path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>',
        "up-right": '<path d="M7 17L17 7"/><path d="M9 7h8v8"/>',
        "flat": '<path d="M5 12h14"/>',
        "down-right": '<path d="M7 7l10 10"/><path d="M17 9v8H9"/>',
        "down": '<path d="M12 5v14"/><path d="M5 12l7 7 7-7"/>',
        "growth": '<path d="M4 18h16"/><path d="M5 15l5-5 4 3 6-8"/><path d="M16 5h4v4"/>',
        "percent": '<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/>',
        "shield": '<path d="M12 3l7 3v5c0 5-3.5 8-7 10-3.5-2-7-5-7-10V6l7-3z"/>',
        "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M17 7l3-3"/><path d="M18 4h2v2"/>',
        "bear": '<path d="M12 5v14"/><path d="M5 12l7 7 7-7"/>',
        "base": '<circle cx="12" cy="12" r="7"/><path d="M12 5v14"/><path d="M5 12h14"/>',
        "bull": '<path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>',
        "check": '<path d="M5 12l4 4 10-10"/>',
        "minus": '<path d="M5 12h14"/>',
        "node": '<circle cx="7" cy="12" r="2"/><circle cx="17" cy="7" r="2"/><circle cx="17" cy="17" r="2"/><path d="M9 11l6-4"/><path d="M9 13l6 4"/>',
        "wrench": '<path d="M14 6a4 4 0 0 0 5 5l-8 8a3 3 0 0 1-4-4l8-8z"/>',
        "users": '<circle cx="9" cy="8" r="3"/><path d="M3 19a6 6 0 0 1 12 0"/><circle cx="17" cy="9" r="2"/><path d="M15 17a4 4 0 0 1 6 2"/>',
        "droplet": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 10v6"/><path d="M12 7h.01"/>',
    }
    body = paths.get(name, paths["info"])
    return f'<svg class="pt-svg-icon {escape(extra_class)}" viewBox="0 0 24 24" aria-hidden="true">{body}</svg>'


def signal_gauge(signal: str, score: float) -> str:
    visual = signal_visual(signal)
    safe_score = max(0.0, min(10.0, score or 0.0))
    fill = max(2.0, safe_score * 10.0)
    theta = pi - (safe_score / 10.0) * pi
    needle_x = 60 + 42 * cos(theta)
    needle_y = 60 - 42 * sin(theta)
    return f"""
    <svg class="pt-gauge {visual["tone"]} {visual["slug"]}" viewBox="0 0 120 72" aria-label="Signal gauge">
      <path class="pt-gauge-track" pathLength="100" d="M12 60 A48 48 0 0 1 108 60"></path>
      <path class="pt-gauge-fill" pathLength="100" style="stroke-dasharray:{fill:.1f} 100" d="M12 60 A48 48 0 0 1 108 60"></path>
      <line class="pt-gauge-needle" x1="60" y1="60" x2="{needle_x:.1f}" y2="{needle_y:.1f}"></line>
      <circle class="pt-gauge-hub" cx="60" cy="60" r="4"></circle>
    </svg>
    """


def signal_badge_icon(signal: str) -> str:
    visual = signal_visual(signal)
    return f'<div class="pt-decision-icon {visual["tone"]} {visual["slug"]}">{svg_icon(visual["icon"], "pt-signal-svg")}</div>'


def business_quality_icon(category: str) -> str:
    key = {
        "Growth": "growth",
        "Profitability": "percent",
        "Balance Sheet": "shield",
        "Execution": "target",
    }.get(category, "generic")
    return f'<span class="pt-line-icon pt-quality-icon">{svg_icon(key, "pt-quality-svg")}</span>'


def scenario_icon(name: str) -> str:
    key = "bear" if "Bear" in name else "bull" if "Bull" in name else "base"
    return f'<span class="pt-scenario-icon {key}">{svg_icon(key, "pt-scenario-svg")}</span>'


def driver_icon(kind: str) -> str:
    icon = "check" if kind == "positive" else "minus" if kind == "negative" else "node"
    tone = "good" if kind == "positive" else "bad" if kind == "negative" else "info"
    return f'<span class="pt-driver-dot {tone}">{svg_icon(icon)}</span>'


def risk_icon(name: str) -> str:
    cls = risk_icon_class(name)
    icon = {"scaling": "wrench", "customer": "users", "dilution": "droplet"}.get(cls, "info")
    return f'<span class="pt-risk-icon {cls}">{svg_icon(icon)}</span>'


def risk_icon_class(name: str) -> str:
    value = name.casefold()
    if "customer" in value:
        return "customer"
    if "dilution" in value or "capital" in value:
        return "dilution"
    if "scaling" in value or "technology" in value or "product" in value or "execution" in value:
        return "scaling"
    return "generic"


def money(value: float, decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.{decimals}f}T"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.{decimals}f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    return f"${value:,.0f}"


def price(value: float) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def percent(value: float, decimals: int = 1, signed: bool = True) -> str:
    if value is None:
        return "N/A"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:.{decimals}f}%"


def tone_for_value(value: float) -> str:
    if value is None:
        return "neutral"
    if value > 0:
        return "good"
    if value < 0:
        return "bad"
    return "neutral"


def tone_for_impact(text: str) -> str:
    value = text.casefold()
    if "positive" in value or "buy" in value or "met" in value or "tracking" in value:
        return "good"
    if "negative" in value or "risk" in value or "not met" in value or "at risk" in value or "high" == value:
        return "bad"
    if "medium" in value or "hold" in value or "monitor" in value or "proof" in value or "needs" in value:
        return "warn"
    return "neutral"


def tone_for_signal(signal: str) -> str:
    if signal in {"Strong Buy", "Buy", "Speculative Buy"}:
        return "good"
    if signal == "Hold":
        return "warn"
    if signal in {"Avoid", "Sell"}:
        return "bad"
    return "neutral"


def compact_date(value: str) -> str:
    months = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }
    parts = value.split("-")
    if len(parts) == 3 and parts[1] in months:
        return f"{months[parts[1]]} {int(parts[2])}, {parts[0]}"
    return value


def data_label(label: str) -> str:
    return f'<span class="pt-data-label">{escape(label)}</span>'


def html(markup: str) -> None:
    compact_markup = " ".join(markup.split())
    render_html(compact_markup)


def section(title: str, subtitle: str = "", body: str = "", action: str = "") -> str:
    subtitle_html = f"<small>{escape(subtitle)}</small>" if subtitle else ""
    action_html = f'<a class="pt-section-action">{escape(action)}</a>' if action else ""
    return f'<div class="pt-section"><div class="pt-section-title"><span>{escape(title)}</span><div>{subtitle_html}{action_html}</div></div>{body}</div>'


def value_row(label: str, value: str, tone: str = "neutral") -> str:
    return f'<div class="pt-kv-row"><span>{escape(label)}</span><b class="{escape(tone)}">{escape(value)}</b></div>'


def detail_row(label: str, value: str) -> str:
    return f'<div class="pt-detail-row"><span>{escape(label)}</span><b>{escape(value)}</b></div>'


def render_brand() -> None:
    html(
        """
        <div class="pt-brand">
          <span class="pt-brand-mark">P</span>
          <strong><span>Pine</span>Terminal</strong>
        </div>
        """
    )


def render_watchlist_sidebar(rows: list[dict[str, object]]) -> None:
    body = "".join(
        f'<div class="pt-watch-row"><b>{escape(str(row["Ticker"]))}</b><span>{price(float(row["Price"]))}</span><span class="{tone_for_value(float(row["Daily Change"]))}">{percent(float(row["Daily Change"]), 2)}</span></div>'
        for row in rows
    )
    html(f'<div class="pt-side-title">My Watchlist</div>{body}<div class="pt-add-ticker">+ Add Ticker</div>')


def render_topbar(page: str, ticker: str, currency: str, data_mode: str = "Demo", last_updated: str = "2026-05-31 13:45 ET") -> None:
    context = f"ACTIVE {ticker}" if page != "Company" else f"EQUITY RESEARCH / {ticker}"
    html(
        f"""
        <div class="pt-topbar">
          <div class="pt-breadcrumb"><span>PT</span> / <b>{escape(page.upper())}</b> / {escape(context)}</div>
        </div>
        """
    )


def _week52_position(current_price: float | None, week52_low: float | None, week52_high: float | None) -> float:
    if current_price is None or week52_low is None or week52_high is None:
        return 50.0
    spread = week52_high - week52_low
    if spread <= 0:
        return 50.0
    return max(0, min(100, ((current_price - week52_low) / spread) * 100))


def company_profile_from_analysis(analysis: CompanyAnalysis) -> CompanyProfile:
    company = analysis.company
    fundamental_score = calculate_fundamental_score(analysis.fundamental_metrics)
    expected_return = calculate_expected_return(analysis.expected_value, company.current_price)
    day_change_dollar = company.day_change_dollar
    if day_change_dollar is None and company.current_price is not None and company.daily_change is not None:
        day_change_dollar = round(company.current_price * company.daily_change / 100, 2)
    if fundamental_score >= 8.5:
        fundamental_label = "High Quality Compounder"
    elif fundamental_score >= 7.0:
        fundamental_label = "Emerging Compounder"
    elif fundamental_score >= 5.5:
        fundamental_label = "Improving / Watchlist"
    elif fundamental_score >= 4.0:
        fundamental_label = "Speculative / Needs Proof"
    else:
        fundamental_label = "Weak Fundamentals"
    return CompanyProfile(
        ticker=company.ticker,
        company_name=company.company_name,
        sector=company.sector,
        industry=company.industry,
        themes=company.themes,
        current_price=company.current_price,
        day_change_dollar=day_change_dollar,
        day_change_percent=company.daily_change,
        market_cap=company.market_cap,
        enterprise_value=company.enterprise_value,
        week52_low=company.week52_low,
        week52_high=company.week52_high,
        week52_current_position=_week52_position(company.current_price, company.week52_low, company.week52_high),
        fundamental_score=fundamental_score,
        fundamental_label=fundamental_label,
        expected36m_return=expected_return,
        expected_return_label="Base Case",
        investment_signal=analysis.investment_signal.signal,
        confidence=analysis.investment_signal.conviction,
        risk_level=analysis.investment_signal.risk_level,
        market_status=company.market_status,
        last_updated=company.last_updated,
        data_mode=company.data_mode,
        data_source=company.data_source,
        pre_market_change_percent=company.pre_market_change_percent,
        after_hours_change_percent=company.after_hours_change_percent,
    )


def render_company_header(profile: CompanyProfile) -> str:
    primary_theme = profile.themes[0] if profile.themes else profile.industry
    signal_tone = tone_for_signal(profile.investment_signal)
    gauge = signal_gauge(profile.investment_signal, profile.fundamental_score)
    day_change = profile.day_change_dollar
    if day_change is None:
        day_change_label = "N/A"
    else:
        day_change_label = f"{'+' if day_change > 0 else '-' if day_change < 0 else ''}{price(abs(day_change))}"
    tags = "".join(f'<span class="pt-tag">{escape(theme)}</span>' for theme in profile.themes[:3])
    source_title = f"Last updated {profile.last_updated} | {profile.data_source}"
    price_detail = (
        f'<small class="pt-muted">Pre {percent(profile.pre_market_change_percent, 1)} | AH {percent(profile.after_hours_change_percent, 1)}</small>'
        if profile.pre_market_change_percent is not None or profile.after_hours_change_percent is not None
        else ""
    )
    return f"""
    <div class="pt-header">
      <div class="pt-company-block">
        <div class="pt-company-title">
          <div class="pt-ticker">{escape(profile.ticker)}</div>
          <div>
            <strong>{escape(profile.company_name)}</strong>
            <small>{escape(profile.sector)} &bull; {escape(profile.industry)} / {escape(primary_theme)}</small>
          </div>
          <span class="pt-header-star">*</span>
        </div>
        <div class="pt-tags">{tags}{render_data_sources_details(profile, source_title)}</div>
      </div>
      <div class="pt-header-market">
        <div class="pt-kpi pt-current-price"><span>Current Price</span><strong>{price(profile.current_price)}</strong><b class="{tone_for_value(profile.day_change_percent)}">{day_change_label} ({percent(profile.day_change_percent, 2)})</b>{price_detail}</div>
        <div class="pt-kpi"><span>Market Cap</span><strong>{money(profile.market_cap)}</strong></div>
        <div class="pt-kpi pt-range-kpi"><span>52W Range</span><strong>{price(profile.week52_low)} to {price(profile.week52_high)}</strong><div class="pt-range"><div class="pt-range-track"><i style="left:{profile.week52_current_position:.1f}%"></i></div></div></div>
      </div>
      <div class="pt-header-signal">
        <div class="pt-kpi pt-signal-kpi">
          <div><span>Analyst Call</span><strong class="{signal_tone}">{escape(profile.investment_signal)}</strong><b>Conviction {escape(profile.confidence)} | Risk {escape(profile.risk_level)}</b></div>
          {gauge}
        </div>
      </div>
    </div>
    """


def render_data_sources_details(profile: CompanyProfile, source_title: str) -> str:
    source = profile.data_source or "N/A"
    market_source = "Yahoo Finance" if "Yahoo" in source else source
    filing_source = "SEC XBRL" if "SEC" in source or "XBRL" in source else "N/A"
    return f"""
    <details class="pt-data-sources">
      <summary title="{escape(source_title)}">Data Sources</summary>
      <div class="pt-floating-panel pt-data-sources-panel">
        <strong>Data Sources</strong>
        {detail_row("Market price", market_source)}
        {detail_row("Financial statements", filing_source)}
        {detail_row("Filing source", filing_source)}
        {detail_row("Derived metrics", "PineTerminal internal model")}
        {detail_row("Data mode", profile.data_mode)}
        {detail_row("Last updated", profile.last_updated)}
      </div>
    </details>
    """


def render_metric_card(metric: FundamentalMetric) -> str:
    tone = "good" if metric.score >= 7 else "warn" if metric.score >= 5 else "bad"
    badge = METRIC_BADGES.get(metric.name, metric.name[:2].upper())
    return f"""
    <div class="pt-metric-card">
      <div class="pt-metric-head"><span class="pt-metric-icon">{escape(badge)}</span><span class="pt-mini-label">{escape(metric.name)}</span></div>
      <strong>{escape(metric.value)}</strong>
      <em>{escape(metric.label)}</em>
      <div class="pt-progress {tone}"><i style="width:{metric.score * 10:.0f}%"></i></div>
      <em class="{tone}">{metric.score:.1f}/10</em>
      {data_label(metric.data_type)}
    </div>
    """


def render_business_quality(analysis: CompanyAnalysis) -> str:
    cards = "".join(render_metric_card(metric) for metric in analysis.fundamental_metrics)
    return section("Business Quality", "Fundamental Engine", f'<div class="pt-quality-grid">{cards}</div>')


def render_scenario_card(scenario: ValuationScenario, current_price: float) -> str:
    name_tone = "bad" if "Bear" in scenario.name else "good" if "Bull" in scenario.name else "info"
    implied_return = calculate_expected_return(scenario.future_share_price, current_price)
    return f"""
    <div class="pt-scenario-card {name_tone}">
      <div class="pt-scenario-title">
        <h4 class="{name_tone}">{escape(scenario.name)}</h4>
        {data_label("Model")}
      </div>
      <dl>
        {_scenario_metric_row(scenario)}
        {_scenario_driver_row(scenario)}
        {value_row("Future Price", price(scenario.future_share_price), "info" if name_tone == "info" else name_tone)}
        {value_row("Return", percent(implied_return, 0), tone_for_value(implied_return))}
      </dl>
      <small class="pt-scenario-note">{escape(scenario.assumption)}</small>
    </div>
    """


def render_future_value_model(analysis: CompanyAnalysis) -> str:
    model = _valuation_model_for_analysis(analysis)
    cards = "".join(render_scenario_card(item, model.current_price or analysis.company.current_price) for item in model.scenarios)
    expected_return = model.expected_return
    probability_rows = "".join(
        value_row(f"{item.name} ({item.probability:.0%})", price(item.future_share_price))
        for item in model.scenarios
    )
    body = f"""
      <div class="pt-fv-grid">
        <div class="pt-scenario-grid">{cards}</div>
        <div class="pt-expected-card">
          <div class="pt-expected-head"><span class="pt-mini-label">Probability-Weighted Expected Value</span>{data_label("Derived")}</div>
          <strong>{price(model.expected_value) if model.expected_value is not None else "N/A"}</strong>
          <div class="pt-data-list pt-expected-list">
            {value_row("Upside / Downside", percent(expected_return, 1) if expected_return is not None else "N/A", tone_for_value(expected_return or 0.0))}
            {probability_rows}
            {value_row("Current Price", price(model.current_price) if model.current_price is not None else "N/A")}
          </div>
        </div>
      </div>
    """
    return section("Future Value Model", "Future Value Engine", body)


def render_readthrough_table(rows: list[MarketReadThroughItem]) -> str:
    body = ""
    for row in rows:
        tone = tone_for_value(row.impact_score)
        transmission = f"{row.transmission_path} {row.why_it_matters} {row.thesis_impact}"
        tickers = "".join(f'<span class="pt-ticker-chip">{escape(ticker)}</span>' for ticker in row.impacted_tickers)
        body += (
            f'<tr title="{escape(transmission)}">'
            f'<td class="pt-date-cell">{escape(compact_date(row.date))}</td>'
            f'<td><div class="pt-market-copy"><strong>{escape(row.market_update)}</strong><small>{escape(row.theme)}</small><small>Path: {escape(row.transmission_path)}</small></div></td>'
            f'<td><div class="pt-ticker-chips">{tickers}</div></td>'
            f'<td><span class="pt-pill {tone}">{escape(row.impact)} {row.impact_score:+.1f}</span></td>'
            f"<td>{escape(row.confidence)}</td>"
            "</tr>"
        )
    return f"""
    <table class="pt-table pt-readthrough-table">
      <thead><tr><th>Date</th><th>Market Update (Theme)</th><th>Impacted Tickers</th><th>Impact</th><th>Confidence</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
    """


def render_market_readthrough(analysis: CompanyAnalysis) -> str:
    rows = analysis.market_read_through
    body = render_readthrough_table(rows) + '<div class="pt-section-footer">See Full Market Read-Through Feed</div>'
    return section("Market Read-Through", "Indirect Catalyst Radar", body, action="View All")


def render_must_be_true(analysis: CompanyAnalysis) -> str:
    rows = ""
    for item in analysis.what_must_be_true:
        tone = tone_for_impact(item.status)
        mark = "OK" if tone != "bad" else "!"
        rows += (
            f'<div class="pt-check-row"><span class="pt-check {tone}">{mark}</span>'
            f'<div title="{escape(item.evidence)}"><strong>{escape(item.description)}</strong><small>{escape(item.valuation_lever)} &bull; {escape(item.confidence)} confidence</small></div>'
            f'<span class="pt-row-status {tone}">{escape(item.status)}</span></div>'
        )
    base = next((item for item in analysis.valuation_scenarios if item.name == "Base Case"), None)
    subtitle = f"To reach Base Case {price(base.future_share_price)}" if base else "To reach Base Case"
    return section("What Must Be True?", subtitle, f'<div class="pt-check-list">{rows}</div>')


def render_bridge(analysis: CompanyAnalysis) -> str:
    bridge_start = analysis.company.current_price
    rows = f'<div class="pt-bridge-row start"><span>Current Price</span><b>{price(bridge_start)}</b></div>'
    for item in analysis.future_value_bridge:
        tone = "bad" if item.type == "negative" else "good"
        sign = "-" if item.type == "negative" else "+"
        rows += f'<div class="pt-bridge-row"><div class="pt-bridge-label"><span>{escape(item.label)}</span><small>{escape(item.explanation)}</small></div><b class="{tone}">{sign}{price(abs(item.value_impact))}</b></div>'
    final_value = calculate_future_value_bridge(bridge_start, analysis.future_value_bridge)
    rows += f'<div class="pt-bridge-row final"><span>Base Case Future Value</span><b class="info">{price(final_value)}</b></div>'
    return section("Future Value Bridge", "Base Case", rows)


def render_market_implied(analysis: CompanyAnalysis) -> str:
    model = _valuation_model_for_analysis(analysis)
    if model.valuation_method != "EV/Sales":
        base = next((item for item in model.scenarios if item.name == "Base Case"), model.scenarios[0])
        labels = get_scenario_labels_by_method(model.valuation_method)
        driver_value = price(base.future_share_price) if model.valuation_method == "Asset Price Scenario" else f"{base.valuation_multiple:.1f}x" if base.valuation_multiple is not None else "N/A"
        body = f"""
        <div class="pt-implied-grid">
          <div class="pt-data-list pt-implied-side">
            <span class="pt-mini-label">Selected Model</span>
            {value_row("Ticker", model.ticker)}
            {value_row("Valuation Method", model.valuation_method)}
            {value_row(str(labels["metric_label"]).format(year=model.model_year), base.valuation_metric_display)}
          </div>
          <div class="pt-data-list pt-implied-side">
            <span class="pt-mini-label">Expected Value</span>
            {value_row(base.valuation_multiple_label, driver_value, "good")}
            {value_row("Probability-Weighted Value", price(model.expected_value) if model.expected_value is not None else "N/A", "good")}
            {value_row("Expected Return", percent(model.expected_return, 1) if model.expected_return is not None else "N/A", tone_for_value(model.expected_return or 0.0))}
          </div>
        </div>
        <div class="pt-banner neutral">{escape(model.interpretation)} {data_label(model.data_status)}</div>
        """
        return section("Model-Implied Assumptions", "What the selected valuation model prices in", body)
    item = analysis.market_implied_assumptions
    body = f"""
    <div class="pt-implied-grid">
      <div class="pt-data-list pt-implied-side">
        <span class="pt-mini-label">Market-Implied</span>
        {value_row("Implied 2028 Revenue", money(item.implied_revenue, 0))}
        {value_row("Implied EV / Sales", f"{item.implied_ev_sales:.1f}x")}
        {value_row("Implied Gross Margin", percent(item.implied_gross_margin, 0, False))}
        {value_row("Implied Revenue CAGR", percent(item.implied_revenue_cagr, 0, False))}
      </div>
      <div class="pt-data-list pt-implied-side">
        <span class="pt-mini-label">Your Base Case</span>
        {value_row("Your Base Case Revenue", money(item.base_revenue, 0), "good")}
        {value_row("Your Base Case EV / Sales", f"{item.base_ev_sales:.1f}x", "good")}
        {value_row("Your Base Case Gross Margin", percent(item.base_gross_margin, 0, False), "good")}
        {value_row("Your Base Case CAGR", percent(item.base_revenue_cagr, 0, False), "good")}
      </div>
    </div>
    <div class="pt-banner {escape(item.tone)}">{escape(item.conclusion)} {data_label(item.status)}</div>
    """
    return section("Market-Implied Assumptions", "What current price prices in", body)


def render_updates(analysis: CompanyAnalysis) -> str:
    rows = ""
    for item in analysis.thesis_updates:
        tone = tone_for_impact(item.impact)
        thesis_arrow = "Up" if tone == "good" else "Down" if tone == "bad" else "Flat"
        valuation_arrow = thesis_arrow
        rows += (
            f'<div class="pt-update-row"><div class="pt-update-meta"><span class="pt-update-icon {tone}"></span><small>{escape(compact_date(item.date))}</small></div>'
            f'<div class="pt-update-copy"><strong>{escape(item.title)}</strong><small><b>Impact:</b> {escape(item.explanation)}</small></div>'
            f'<span class="pt-pill {tone}">{escape(item.impact)}</span>'
            f'<div class="pt-arrow-stack"><small>Thesis</small><b class="{tone}">{thesis_arrow}</b><small>Valuation</small><b class="{tone}">{valuation_arrow}</b></div></div>'
        )
    return section("Latest Updates & Thesis Impact", "", rows, action="View All")


def render_risks(analysis: CompanyAnalysis) -> str:
    rows = ""
    for item in analysis.risks:
        tone = tone_for_impact(item.severity)
        rows += (
            f'<div class="pt-risk-row"><b class="pt-risk-rank">{item.rank}</b>'
            f'<div class="pt-risk-copy" title="{escape(item.mitigant)}"><strong>{escape(item.risk_name)}</strong><small>{escape(item.description)}</small></div>'
            f'<span class="pt-pill {tone}">{escape(item.severity)}</span></div>'
        )
    return section("Top Risks to Thesis", "", f'<div class="pt-risk-list">{rows}</div><div class="pt-section-footer">View All Risks & Mitigants</div>')


def render_sensitivity_table(table: SensitivityTable, current_price: float) -> str:
    body = sensitivity_table_markup(table, current_price)
    return section("Sensitivity Table", "2028 Price Target", body)


def render_signal(analysis: CompanyAnalysis) -> str:
    signal = analysis.investment_signal
    breakdown = ""
    for label, (score, weight) in signal.score_breakdown.items():
        tone = "bad" if "Risk" in label and score < 6 else "good" if score >= 7 else "warn"
        breakdown += f'<div class="pt-score-chip"><span>{escape(label)}</span><strong class="{tone}">{score:.1f}<small>/10</small></strong><em>{weight:.0%} weight</em></div>'
    body = f"""
    <div class="pt-final-grid">
      <div class="pt-signal-callout">
        <span class="pt-mini-label">Investment Signal</span>
        <strong class="{tone_for_signal(signal.signal)}">{escape(signal.signal)}</strong>
        <p class="pt-placeholder">{escape(signal.summary)}</p>
      </div>
      <div class="pt-score-area"><span class="pt-mini-label">Score Breakdown</span><div class="pt-score-breakdown">{breakdown}</div></div>
      <div class="pt-total-score-card">
        <span class="pt-mini-label">Total Score</span>
        <strong class="{tone_for_signal(signal.signal)}">{signal.total_score:.1f}<small>/10</small></strong>
        <div class="pt-data-list">
          {value_row("Conviction", signal.conviction, "warn")}
          {value_row("Risk Level", signal.risk_level, tone_for_impact(signal.risk_level))}
        </div>
      </div>
    </div>
    """
    return section("Investment Signal", "", body)


def _key_stats_for_analysis(analysis: CompanyAnalysis) -> dict[str, str]:
    company = analysis.company
    base = next((item for item in analysis.valuation_scenarios if item.name == "Base Case"), analysis.valuation_scenarios[0])
    if company.shares_outstanding is not None:
        shares = money(company.shares_outstanding, 1).replace("$", "")
    else:
        shares = f"{base.diluted_shares_outstanding / 1_000_000:.1f}M"
    if company.cash_burn_ttm is not None:
        cash_burn = "FCF positive" if company.cash_burn_ttm >= 0 else money(abs(company.cash_burn_ttm))
    else:
        cash_burn = "N/A"
    return {
        "shares": shares,
        "insider": "N/A",
        "cash": money(company.cash) if company.cash is not None else "N/A",
        "revenue": money(company.revenue_ttm) if company.revenue_ttm is not None else "N/A",
        "gross_margin": percent(company.gross_margin, 0, False) if company.gross_margin is not None else "N/A",
        "cash_burn": cash_burn,
    }


def render_key_stats(analysis: CompanyAnalysis) -> str:
    values = _key_stats_for_analysis(analysis)
    stats = f"""
    <div class="pt-data-list pt-key-stats-grid pt-compact-kv">
      {value_row("Shares Outstanding (Dil.)", values["shares"])}
      {value_row("Insider Ownership", values["insider"])}
      {value_row("Cash & Equivalents", values["cash"])}
      {value_row("Revenue Run-Rate / TTM", values["revenue"])}
      {value_row("Gross Margin", values["gross_margin"])}
      {value_row("Cash Burn Run-Rate / TTM", values["cash_burn"])}
    </div>
    """
    return section("Key Stats", "", stats)


def render_next_events(analysis: CompanyAnalysis) -> str:
    events = "".join(value_row(item["event"], item["date"]) for item in analysis.next_events)
    events_body = f'<div class="pt-data-list pt-events-list pt-compact-kv">{events}</div>'
    return section("Next Events", "", events_body)


def _metric_by_name(analysis: CompanyAnalysis, name: str) -> FundamentalMetric | None:
    return next((metric for metric in analysis.fundamental_metrics if metric.name == name), None)


def _score_tone(score: float, *, risk: bool = False) -> str:
    if risk and score < 5:
        return "bad"
    if score >= 7:
        return "good"
    if score >= 5:
        return "warn"
    return "bad"


def _decision_summary(signal: str, risk_level: str) -> str:
    if signal in {"Strong Buy", "Buy", "Speculative Buy"}:
        return f"High-upside, high-risk setup. The future value case is attractive, but execution, dilution, and the {risk_level.casefold()} risk profile still need monitoring."
    if signal == "Hold":
        return "Fundamentals are improving, but the current price already discounts much of the upside. New evidence matters more than headline valuation from here."
    return "Risk/reward is unfavorable at the current setup. Better evidence or a lower entry price would be needed."


def _bottom_line(analysis: CompanyAnalysis) -> str:
    ticker = analysis.company.ticker
    signal = analysis.investment_signal.signal
    expected_return = analysis.expected_value_detail.expected_return
    if signal == "Hold" or abs(expected_return) < 15:
        return f"{ticker} remains a high-risk execution story. The stock is no longer obviously cheap at the current price, but upside remains if revenue scales and dilution stays controlled."
    if expected_return > 15:
        return f"{ticker} offers attractive upside, but the thesis still depends on revenue scaling, margin progress, and disciplined dilution."
    return f"{ticker} has an unfavorable setup at the current price unless execution improves or valuation resets."


def _thesis_status(analysis: CompanyAnalysis) -> tuple[str, str]:
    score = analysis.thesis_summary.net_thesis_impact_score
    if score > 0.8:
        return "Strengthening", "good"
    if score < -0.3:
        return "Weakening", "bad"
    return "Tracking", "warn"


def _score_breakdown_rows(analysis: CompanyAnalysis) -> str:
    label_map = {
        "Fundamental Score": "Business Quality",
        "Valuation / Upside": "Valuation Upside",
        "Catalyst / Momentum": "Catalyst Support",
        "Risk Adjustment": "Risk Adjustment",
    }
    rows = ""
    for label, (score, _weight) in analysis.investment_signal.score_breakdown.items():
        display = label_map.get(label, label)
        tone = _score_tone(score, risk="Risk" in label)
        rows += f"""
        <div class="pt-decision-score">
          <span>{escape(display)}</span>
          <strong class="{tone}">{score:.1f}<small>/10</small></strong>
          <i class="{tone}" style="--score:{max(0, min(100, score * 10)):.0f}%"></i>
        </div>
        """
    total_tone = tone_for_signal(analysis.investment_signal.signal)
    rows += f"""
    <div class="pt-decision-score total">
      <span>Total Score</span>
      <strong class="{total_tone}">{analysis.investment_signal.total_score:.1f}<small>/10</small></strong>
      <i class="{total_tone}" style="--score:{max(0, min(100, analysis.investment_signal.total_score * 10)):.0f}%"></i>
    </div>
    """
    return rows


def render_methodology_details() -> str:
    sections = [
        ("Business Quality", "Revenue quality, margin quality, balance sheet strength, and execution credibility."),
        ("Future Value / Valuation Upside", "Bear/base/bull scenario analysis, expected value versus current price, and whether the market already prices in execution."),
        ("Catalyst Support", "Forward demand drivers, company catalysts, and sector or macro tailwinds and headwinds."),
        ("Risk Adjustment", "Execution risk, dilution risk, customer concentration, financing risk, and multiple compression risk."),
        ("Thesis Momentum", "Whether recent updates are strengthening or weakening confidence and whether model inputs are moving in the right direction."),
    ]
    definitions = [
        ("Strong Buy", "Exceptional risk/reward with strong business quality, attractive forward value, and supportive catalysts."),
        ("Buy", "Positive setup with meaningful upside and manageable risks."),
        ("Speculative Buy", "Attractive upside, but execution and uncertainty remain elevated."),
        ("Hold", "Balanced setup. Upside exists, but the current price already reflects much of the thesis."),
        ("Avoid", "Risk/reward is not attractive given current evidence and valuation."),
        ("Sell", "Thesis is deteriorating or valuation/risk is materially unfavorable."),
    ]
    section_rows = "".join(f"<li><b>{escape(label)}</b><span>{escape(copy)}</span></li>" for label, copy in sections)
    definition_rows = "".join(f"<li><b>{escape(label)}</b><span>{escape(copy)}</span></li>" for label, copy in definitions)
    return f"""
    <details class="pt-methodology">
      <summary>View Methodology</summary>
      <div class="pt-methodology-panel">
        <strong>PineTerminal Forward Decision Framework</strong>
        <p>The PineTerminal signal is forward-looking. It combines present business quality with scenario-based valuation, catalyst strength, risk adjustment, and thesis momentum. The goal is not just to score the company today, but to assess where the thesis is heading and whether the current stock price appropriately reflects that path.</p>
        <div class="pt-methodology-pillars"><span>Business Quality</span><span>Future Value</span><span>Catalyst Support</span><span>Risk Adjustment</span><span>Thesis Momentum</span></div>
        <em>Core methodology pillars</em>
        <ul>{section_rows}</ul>
        <em>Signal definitions</em>
        <ul>{definition_rows}</ul>
      </div>
    </details>
    """


def render_investment_decision(analysis: CompanyAnalysis) -> str:
    signal = analysis.investment_signal
    expected_return = analysis.expected_value_detail.expected_return
    status, status_tone = _thesis_status(analysis)
    signal_tone = tone_for_signal(signal.signal)
    return f"""
    <div class="pt-section pt-decision-card">
      <div class="pt-decision-main">
        {signal_badge_icon(signal.signal)}
        <div class="pt-decision-copy">
          <div class="pt-section-title flat"><span>Analyst View</span></div>
          <strong class="{signal_tone}">{escape(signal.signal)}</strong>
          <p>{escape(_decision_summary(signal.signal, signal.risk_level))}</p>
          <div class="pt-bottom-line-callout">{escape(_bottom_line(analysis))}</div>
        </div>
        <div class="pt-decision-quick">
          {value_row("Implied 36M Return", percent(expected_return, 0), tone_for_value(expected_return))}
          {value_row("Thesis Direction", status, status_tone)}
          {value_row("Conviction", signal.conviction, "warn")}
          {value_row("Principal Risk", signal.risk_level, tone_for_impact(signal.risk_level))}
        </div>
      </div>
      <div class="pt-decision-breakdown">
        <div class="pt-score-label"><span class="pt-mini-label">Score Breakdown</span><small>Scores reflect both current evidence and expected future trajectory.</small></div>
        <div class="pt-decision-score-grid">{_score_breakdown_rows(analysis)}</div>
        {render_methodology_details()}
      </div>
    </div>
    """


def _quarter_label(label: str) -> str:
    value = label.replace("2026 ", "").replace("2025 ", "").strip()
    return value if value else label


def _quality_headline(analysis: CompanyAnalysis, name: str, metric: FundamentalMetric | None) -> str:
    if metric is None:
        return "N/A"
    if name == "Growth":
        label = _quarter_label(metric.label)
        if "revenue" in label.casefold():
            return f"{label} {metric.value}."
        return f"{label} revenue {metric.value}."
    if name == "Profitability":
        return f"Gross margin {metric.value}."
    if name == "Balance Sheet":
        cash = analysis.company.cash or 0
        debt = analysis.company.debt or 0
        net_cash = cash - debt
        if net_cash >= 0:
            return f"Net cash {money(net_cash)}."
        return f"Net debt {money(abs(net_cash))}."
    if name == "Execution":
        return f"{metric.label}."
    return f"{metric.value} - {metric.label}"


def _quality_interpretation(name: str, analysis: CompanyAnalysis) -> str:
    if name == "Growth":
        return "Revenue is scaling, but the base remains small."
    if name == "Profitability":
        return "Margins are improving, but the company is not yet self-funding."
    if name == "Balance Sheet":
        return "Low debt helps, but dilution risk remains if cash burn persists."
    if name == "Execution":
        return "Execution is improving, but scaling remains unproven."
    return "Needs continued evidence."


def _metric_interpretation(metric: FundamentalMetric) -> str:
    trend = {"up": "improving", "down": "deteriorating", "flat": "stable"}.get(metric.trend, "tracked")
    return f"{metric.status}. Current evidence is {metric.value} ({metric.label}); trend is {trend}."


def render_fundamental_engine_panel(analysis: CompanyAnalysis) -> str:
    rows = ""
    for metric in analysis.fundamental_metrics:
        tone = _score_tone(metric.score)
        rows += f"""
        <tr>
          <td><strong>{escape(metric.name)}</strong></td>
          <td><span class="{tone}">{metric.score:.1f}/10</span></td>
          <td>{escape(metric.value)} <small>{escape(metric.label)}</small></td>
          <td>{escape(_metric_interpretation(metric))}</td>
        </tr>
        """
    return f"""
    <div class="pt-detail-panel">
      <div class="pt-detail-heading"><strong>Full Fundamental Engine</strong><span>8 Metrics</span></div>
      <table class="pt-table pt-detail-table">
        <thead><tr><th>Metric</th><th>Score</th><th>Current Metric</th><th>Interpretation</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def render_fundamental_engine_details(analysis: CompanyAnalysis) -> str:
    return f"""
    <details class="pt-inline-details pt-full-engine-details">
      <summary>View Full Fundamental Engine (8 Metrics)</summary>
      {render_fundamental_engine_panel(analysis)}
    </details>
    """


def render_decision_business_quality(analysis: CompanyAnalysis) -> str:
    metrics = {
        "Growth": _metric_by_name(analysis, "Revenue Growth"),
        "Profitability": _metric_by_name(analysis, "Gross Margin"),
        "Balance Sheet": _metric_by_name(analysis, "Balance Sheet"),
        "Execution": _metric_by_name(analysis, "Execution Quality"),
    }
    cards = ""
    for name, metric in metrics.items():
        score = metric.score if metric else 0.0
        tone = _score_tone(score)
        headline = _quality_headline(analysis, name, metric)
        interpretation = _quality_interpretation(name, analysis)
        cards += f"""
        <div class="pt-quality-pillar">
          {business_quality_icon(name)}
          <div>
            <strong>{escape(name)}</strong>
            <b class="{tone}">{score:.1f}<small>/10</small></b>
            <em>{escape(headline)}</em>
            <p>{escape(interpretation)}</p>
          </div>
        </div>
        """
    body = f'<div class="pt-quality-pillars">{cards}</div>{render_fundamental_engine_details(analysis)}'
    return section("Operating Quality", "Evidence from the latest reported period", body)


def _scenario_tone(name: str) -> str:
    if "Bear" in name:
        return "bad"
    if "Bull" in name:
        return "good"
    return "info"


def _valuation_model_for_analysis(analysis: CompanyAnalysis) -> ValuationModel:
    return analysis.valuation_model or get_valuation_model(analysis.company)


def _scenario_metric_row(scenario: ValuationScenario) -> str:
    labels = get_scenario_labels_by_method(scenario.valuation_method)
    label = str(labels["metric_label"]).format(year=scenario.year)
    value = scenario.valuation_metric_display or format_financial_value(scenario.valuation_metric_value, "dollars")
    return value_row(label, value)


def _scenario_driver_row(scenario: ValuationScenario) -> str:
    if scenario.valuation_method == "Asset Price Scenario":
        return value_row("NAV / Share Estimate", price(scenario.future_share_price))
    if scenario.valuation_multiple is None:
        return value_row(scenario.valuation_multiple_label, "N/A")
    return value_row(scenario.valuation_multiple_label, f"{scenario.valuation_multiple:.1f}x")


def _model_warning_markup(model: ValuationModel) -> str:
    if not model.warnings:
        return ""
    warning_text = " ".join(model.warnings[:2])
    return f"""
    <div class="pt-model-warning">
      {svg_icon("info")}
      <span>Valuation model inputs are incomplete or stale. Review assumptions.</span>
      <small>{escape(warning_text)}</small>
    </div>
    """


def render_decision_scenario_card(scenario: ValuationScenario, current_price: float | None) -> str:
    tone = _scenario_tone(scenario.name)
    scenario_return = calculate_expected_return(scenario.future_share_price, current_price or 0.0)
    return f"""
    <div class="pt-decision-scenario {tone}">
      <h4 class="{tone}">{scenario_icon(scenario.name)}<span>{escape(scenario.name)}</span></h4>
      <strong>{price(scenario.future_share_price)}</strong>
      <b class="{tone_for_value(scenario_return)}">{percent(scenario_return, 0)}</b>
      <span>{scenario.probability:.0%} Probability</span>
      <div class="pt-data-list">
        {_scenario_metric_row(scenario)}
        {_scenario_driver_row(scenario)}
      </div>
      <p>{escape(scenario.assumption)}</p>
    </div>
    """


def _valuation_interpretation(analysis: CompanyAnalysis) -> str:
    return _valuation_model_for_analysis(analysis).interpretation


def render_bridge_panel(analysis: CompanyAnalysis) -> str:
    rows = f'{detail_row("Current Price", price(analysis.company.current_price))}'
    for item in analysis.future_value_bridge:
        tone = "bad" if item.type == "negative" else "good"
        sign = "-" if item.type == "negative" else "+"
        rows += f'<div class="pt-detail-row"><span>{escape(item.label)}<small>{escape(item.explanation)}</small></span><b class="{tone}">{sign}{price(abs(item.value_impact))}</b></div>'
    final_value = calculate_future_value_bridge(analysis.company.current_price, analysis.future_value_bridge)
    rows += f'<div class="pt-detail-row total"><span>Base Case Future Value</span><b class="info">{price(final_value)}</b></div>'
    return f'<div class="pt-detail-card"><strong>Future Value Bridge</strong>{rows}</div>'


def render_market_implied_panel(analysis: CompanyAnalysis) -> str:
    model = _valuation_model_for_analysis(analysis)
    if model.valuation_method != "EV/Sales":
        base = next((item for item in model.scenarios if item.name == "Base Case"), model.scenarios[0])
        driver_value = price(base.future_share_price) if model.valuation_method == "Asset Price Scenario" else f"{base.valuation_multiple:.1f}x" if base.valuation_multiple is not None else "N/A"
        return f"""
        <div class="pt-detail-card">
          <strong>Model-Implied Assumptions</strong>
          {detail_row("Selected ticker", model.ticker)}
          {detail_row("Valuation method", model.valuation_method)}
          {detail_row(str(get_scenario_labels_by_method(model.valuation_method)["metric_label"]).format(year=model.model_year), base.valuation_metric_display)}
          {detail_row(base.valuation_multiple_label, driver_value)}
          {detail_row("Probability-weighted value", price(model.expected_value) if model.expected_value is not None else "N/A")}
          <p class="pt-detail-note neutral">{escape(model.interpretation)}</p>
        </div>
        """
    item = analysis.market_implied_assumptions
    return f"""
    <div class="pt-detail-card">
      <strong>Market-Implied Assumptions</strong>
      {detail_row("Implied 2028 Revenue", money(item.implied_revenue, 0))}
      {detail_row("Implied EV / Sales", f"{item.implied_ev_sales:.1f}x")}
      {detail_row("Implied Gross Margin", percent(item.implied_gross_margin, 0, False))}
      {detail_row("Base Revenue", money(item.base_revenue, 0))}
      {detail_row("Base EV / Sales", f"{item.base_ev_sales:.1f}x")}
      <p class="pt-detail-note {escape(item.tone)}">{escape(item.conclusion)}</p>
    </div>
    """


def sensitivity_table_markup(
    table: SensitivityTable,
    current_price: float,
    *,
    valuation_method: str = "Revenue Multiple",
    metric_label: str = "Revenue",
    multiple_label: str = "Revenue Multiple",
) -> str:
    unit = "eps" if valuation_method == "P/E" else "asset_price" if valuation_method == "Asset Price Scenario" else "dollars"
    header = "".join(f"<th>{format_financial_value(value, unit)}</th>" for value in table.revenue_columns)
    rows = ""
    for multiple in table.multiple_rows:
        cells = ""
        for revenue in table.revenue_columns:
            classes = ["base"] if (revenue, multiple) == table.highlighted_cell else []
            classes.append("upside" if table.values[(revenue, multiple)] > current_price else "downside")
            cells += f'<td class="{" ".join(classes)}">{price(table.values[(revenue, multiple)])}</td>'
        row_label = f"{multiple:.2f}x" if valuation_method == "Asset Price Scenario" else f"{multiple:.1f}x"
        rows += f"<tr><th>{row_label}</th>{cells}</tr>"
    return f"""
    <div class="pt-sensitivity">
      <table class="pt-table pt-sensitivity-table">
        <thead><tr><th>{escape(multiple_label)}</th>{header}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <small class="pt-table-note">{escape(metric_label)} across columns. {escape(table.note)} Current price: {price(current_price)}.</small>
    """


def render_valuation_details(analysis: CompanyAnalysis, model: ValuationModel) -> str:
    labels = get_scenario_labels_by_method(model.valuation_method)
    metric_header = str(labels["metric_label"]).format(year=model.model_year)
    driver_header = str(labels["multiple_label"])
    formula_rows = "".join(detail_row(f"Step {idx}", str(row)) for idx, row in enumerate(labels["formula"], start=1))
    scenario_rows = ""
    math_rows = ""
    for scenario in model.scenarios:
        scenario_return = calculate_expected_return(scenario.future_share_price, model.current_price or 0.0)
        contribution = scenario.future_share_price * scenario.probability
        driver_value = price(scenario.future_share_price) if model.valuation_method == "Asset Price Scenario" else f"{scenario.valuation_multiple:.1f}x" if scenario.valuation_multiple is not None else "N/A"
        scenario_rows += f"""
        <tr>
          <td><strong>{escape(scenario.name)}</strong></td>
          <td>{escape(scenario.valuation_metric_display)}</td>
          <td>{escape(driver_value)}</td>
          <td>{price(scenario.future_share_price)}</td>
          <td>{percent(scenario_return, 1)}</td>
          <td>{scenario.probability:.0%}</td>
          <td>{escape(scenario.assumption_quality)}</td>
          <td>{escape(scenario.assumption)}</td>
        </tr>
        """
        math_rows += detail_row(f"{scenario.name} contribution", f"{price(scenario.future_share_price)} x {scenario.probability:.0%} = {price(contribution)}")
    expected_value = model.expected_value
    expected_return = model.expected_return
    warnings = "".join(f"<li>{escape(item)}</li>" for item in model.warnings)
    warning_block = f'<div class="pt-detail-card wide warn"><strong>Model Warnings</strong><ul class="pt-detail-list">{warnings}</ul></div>' if warnings else ""
    return f"""
    <details class="pt-inline-details pt-valuation-details">
      <summary>View valuation details</summary>
      <div class="pt-detail-panel">
        <div class="pt-detail-heading"><strong>Valuation Details</strong><span>{escape(model.ticker)} | {escape(model.valuation_method)} | {escape(model.data_status)}</span></div>
        <table class="pt-table pt-detail-table">
          <thead><tr><th>Scenario</th><th>{escape(metric_header)}</th><th>{escape(driver_header)}</th><th>Future Price</th><th>Return</th><th>Probability</th><th>Quality</th><th>Assumption</th></tr></thead>
          <tbody>{scenario_rows}</tbody>
        </table>
        <div class="pt-detail-grid two">
          <div class="pt-detail-card">
            <strong>Expected Value Math</strong>
            {math_rows}
            {detail_row("Probability-weighted value", price(expected_value) if expected_value is not None else "N/A")}
            {detail_row("Current price", price(model.current_price) if model.current_price is not None else "N/A")}
            {detail_row("Expected return", percent(expected_return, 1) if expected_return is not None else "N/A")}
          </div>
          <div class="pt-detail-card">
            <strong>Calculation Formula</strong>
            {formula_rows}
            {detail_row("Key assumption", model.key_assumption)}
            {detail_row("Interpretation", model.interpretation)}
            {detail_row("Freshness / Source", model.data_status)}
          </div>
          {render_bridge_panel(analysis)}
          {render_market_implied_panel(analysis)}
        </div>
        {warning_block}
        <div class="pt-detail-card wide">
          <strong>Sensitivity Matrix</strong>
          {sensitivity_table_markup(analysis.sensitivity_table, analysis.company.current_price, valuation_method=model.valuation_method, metric_label=metric_header, multiple_label=driver_header)}
        </div>
      </div>
    </details>
    """


def render_decision_future_value(analysis: CompanyAnalysis) -> str:
    model = _valuation_model_for_analysis(analysis)
    scenarios = "".join(render_decision_scenario_card(item, model.current_price) for item in model.scenarios)
    expected_return = model.expected_return
    body = f"""
    {_model_warning_markup(model)}
    <div class="pt-decision-scenarios">{scenarios}</div>
    <div class="pt-expected-strip">
      {value_row("Probability-Weighted Expected Value", price(model.expected_value) if model.expected_value is not None else "N/A", "good")}
      {value_row("Current Price", price(model.current_price) if model.current_price is not None else "N/A")}
      {value_row("Expected Return", percent(expected_return, 1) if expected_return is not None else "N/A", tone_for_value(expected_return or 0.0))}
      {value_row("Interpretation", model.interpretation, "neutral")}
    </div>
    <div class="pt-scenario-footer">
      <span>Key assumption: {escape(model.key_assumption)} <small>{escape(model.data_status)}</small></span>
      {render_valuation_details(analysis, model)}
    </div>
    """
    return section("Valuation Framework", "Scenario-weighted, not a point target", body)


def _driver_items(analysis: CompanyAnalysis, *, positive: bool) -> list[str]:
    configured = analysis.positive_drivers if positive else analysis.negative_drivers
    if configured:
        return list(configured[:3])
    desired = []
    for item in analysis.thesis_updates:
        tone = tone_for_impact(item.impact)
        if positive and tone == "good":
            desired.append(item.explanation)
        elif not positive and tone == "bad":
            desired.append(item.explanation)
    if positive:
        for item in analysis.what_must_be_true:
            desired.append(item.description)
    else:
        for item in analysis.risks:
            desired.append(item.description)
    cleaned = []
    for text in desired:
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:3] or ["N/A"]


def render_decision_thesis_drivers(analysis: CompanyAnalysis) -> str:
    positive = "".join(f"<li>{driver_icon('positive')}{escape(item)}</li>" for item in _driver_items(analysis, positive=True))
    negative = "".join(f"<li>{driver_icon('negative')}{escape(item)}</li>" for item in _driver_items(analysis, positive=False))
    levers = list(analysis.key_levers)
    if not levers:
        for item in analysis.what_must_be_true:
            if item.valuation_lever not in levers:
                levers.append(item.valuation_lever)
        for item in analysis.future_value_bridge:
            if item.label not in levers:
                levers.append(item.label)
    lever_rows = "".join(f"<li>{driver_icon('lever')}{escape(item)}</li>" for item in levers[:5])
    body = f"""
    <div class="pt-drivers-grid">
      <div><h4 class="good">Positive Drivers</h4><ul>{positive}</ul></div>
      <div><h4 class="bad">Negative Drivers</h4><ul>{negative}</ul></div>
      <div class="pt-key-levers"><h4>Key Levers</h4><ul>{lever_rows}</ul></div>
    </div>
    """
    return section("Thesis Evidence", "What is strengthening or weakening conviction", body)


def render_decision_checklist(analysis: CompanyAnalysis) -> str:
    rows = ""
    for item in analysis.what_must_be_true[:5]:
        tone = tone_for_impact(item.status)
        rows += f'<li><span>{escape(item.description)}</span><b class="pt-status-badge {tone}">{escape(item.status)}</b></li>'
    legend = (
        '<div class="pt-status-legend">'
        '<span><i class="good"></i>Tracking</span>'
        '<span><i class="warn"></i>Needs Proof / Monitoring</span>'
        '<span><i class="bad"></i>At Risk</span>'
        '</div>'
    )
    body = f'{legend}<ul class="pt-simple-checklist">{rows}</ul><p class="pt-bottom-line">Bottom line: Upside depends on execution, not just hype.</p>'
    return section("Conditions for Upside", "Evidence required for the base case", body)


def render_decision_risks(analysis: CompanyAnalysis) -> str:
    rows = ""
    for idx, item in enumerate(analysis.risks[:3], start=1):
        tone = tone_for_impact(item.severity)
        risk_name = _plain_risk_name(item.risk_name)
        rows += f"""
        <tr>
          <td><span class="pt-risk-name"><b>{idx}</b>{risk_icon(risk_name)}<span>{escape(risk_name)}</span></span></td>
          <td><span class="pt-pill {tone}">{escape(item.severity)}</span></td>
          <td>{escape(item.description)}</td>
          <td>{escape(item.mitigant)}</td>
        </tr>
        """
    body = f"""
    <table class="pt-table pt-key-risk-table">
      <thead><tr><th>Risk</th><th>Severity</th><th>Why it matters</th><th>What would reduce this risk</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    {render_all_risks_details(analysis)}
    """
    return section("Principal Risks", "Top 3", body)


def render_all_risks_details(analysis: CompanyAnalysis) -> str:
    rows = ""
    for idx, item in enumerate(analysis.risks, start=1):
        tone = tone_for_impact(item.severity)
        risk_name = _plain_risk_name(item.risk_name)
        rows += f"""
        <tr>
          <td><span class="pt-risk-name"><b>{idx}</b>{risk_icon(risk_name)}<span>{escape(risk_name)}</span></span></td>
          <td><span class="pt-pill {tone}">{escape(item.severity)}</span></td>
          <td>{escape(item.description)}</td>
          <td>{escape(item.mitigant)}</td>
          <td>{escape(item.current_status)}</td>
        </tr>
        """
    return f"""
    <details class="pt-inline-details right">
      <summary>View All Risks & Mitigants</summary>
      <div class="pt-detail-panel">
        <div class="pt-detail-heading"><strong>All Tracked Risks</strong><span>{len(analysis.risks)} risks</span></div>
        <table class="pt-table pt-detail-table">
          <thead><tr><th>Risk</th><th>Severity</th><th>Why it matters</th><th>What would reduce this risk</th><th>Status / Trend</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </details>
    """


def _plain_risk_name(name: str) -> str:
    value = name.casefold()
    if "customer" in value:
        return "Customer Concentration Risk"
    if "dilution" in value or "capital" in value:
        return "Dilution Risk"
    if "technology" in value or "product" in value or "execution" in value:
        return "Scaling Risk"
    return name


def render_thesis_update_rows(analysis: CompanyAnalysis, limit: int | None = None) -> str:
    rows = ""
    updates = analysis.thesis_updates if limit is None else analysis.thesis_updates[:limit]
    for item in updates:
        tone = tone_for_impact(item.impact)
        thesis_arrow = "Up" if tone == "good" else "Down" if tone == "bad" else "Flat"
        valuation_arrow = thesis_arrow
        rows += f"""
        <tr>
          <td><span class="pt-change-dot {tone}"></span>{escape(compact_date(item.date))}</td>
          <td><strong>{escape(item.title)}</strong></td>
          <td>{escape(item.type)}</td>
          <td><span class="pt-pill {tone}">{escape(item.impact)}</span></td>
          <td><b class="{tone}">{thesis_arrow}</b></td>
          <td><b class="{tone}">{valuation_arrow}</b></td>
          <td>{escape(item.explanation)}</td>
          <td>{escape(item.dashboard_adjustment)}</td>
        </tr>
        """
    return rows


def render_all_updates_details(analysis: CompanyAnalysis) -> str:
    rows = render_thesis_update_rows(analysis)
    return f"""
    <details class="pt-inline-details centered">
      <summary>View All Updates & Thesis Impact</summary>
      <div class="pt-detail-panel">
        <div class="pt-detail-heading"><strong>Full Thesis Update Feed</strong><span>{len(analysis.thesis_updates)} updates</span></div>
        <table class="pt-table pt-changes-table pt-detail-table">
          <thead><tr><th>Date</th><th>Update</th><th>Type</th><th>Impact</th><th>Thesis Impact</th><th>Valuation Impact</th><th>Why it matters</th><th>Model Impact</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </details>
    """


def render_decision_recent_changes(analysis: CompanyAnalysis) -> str:
    rows = render_thesis_update_rows(analysis, 4)
    body = f"""
    <table class="pt-table pt-changes-table">
      <thead><tr><th>Date</th><th>Update</th><th>Type</th><th>Impact</th><th>Thesis Impact</th><th>Valuation Impact</th><th>Why it matters</th><th>Model Impact</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    {render_all_updates_details(analysis)}
    """
    return section("Thesis Delta", "What changed, why it matters, and model impact", body)


def render_key_stats_panel(analysis: CompanyAnalysis) -> str:
    values = _key_stats_for_analysis(analysis)
    return f"""
    <div class="pt-detail-card">
      <strong>Key Stats</strong>
      {detail_row("Shares Outstanding (Dil.)", values["shares"])}
      {detail_row("Insider Ownership", values["insider"])}
      {detail_row("Cash & Equivalents", values["cash"])}
      {detail_row("Revenue Run-Rate / TTM", values["revenue"])}
      {detail_row("Gross Margin", values["gross_margin"])}
      {detail_row("Cash Burn Run-Rate / TTM", values["cash_burn"])}
    </div>
    """


def render_next_events_panel(analysis: CompanyAnalysis) -> str:
    rows = "".join(detail_row(item["event"], item["date"]) for item in analysis.next_events)
    if not rows:
        rows = detail_row("Next events", "N/A")
    return f'<div class="pt-detail-card"><strong>Next Events</strong>{rows}</div>'


def render_advanced_model_details(analysis: CompanyAnalysis) -> str:
    model = _valuation_model_for_analysis(analysis)
    labels = get_scenario_labels_by_method(model.valuation_method)
    metric_label = str(labels["metric_label"]).format(year=model.model_year)
    multiple_label = str(labels["multiple_label"])
    return f"""
    <details class="pt-section pt-advanced-details">
      <summary>
        <span class="pt-lock-icon"></span>
        <span>
          <strong>Model & Source Detail <small>(Expand)</small></strong>
          <p>Assumptions, sensitivities, market-implied expectations, source provenance, and the full evidence trail.</p>
        </span>
        <b class="pt-accordion-caret"></b>
      </summary>
      <div class="pt-advanced-content">
        {render_fundamental_engine_panel(analysis)}
        <div class="pt-detail-grid two">
          {render_bridge_panel(analysis)}
          {render_market_implied_panel(analysis)}
          {render_key_stats_panel(analysis)}
          {render_next_events_panel(analysis)}
        </div>
        <div class="pt-detail-card wide">
          <strong>Sensitivity Table</strong>
          {sensitivity_table_markup(analysis.sensitivity_table, analysis.company.current_price, valuation_method=model.valuation_method, metric_label=metric_label, multiple_label=multiple_label)}
        </div>
        <div class="pt-detail-card wide">
          <strong>Full Read-Through Feed</strong>
          {render_readthrough_table(analysis.market_read_through)}
        </div>
      </div>
    </details>
    """


def render_company_dashboard(analysis: CompanyAnalysis) -> None:
    company_profile = company_profile_from_analysis(analysis)
    html(
        '<div class="pt-shell pt-decision-shell">'
        + render_company_header(company_profile)
        + render_investment_decision(analysis)
        + f'<div class="pt-decision-row">{render_decision_business_quality(analysis)}{render_decision_future_value(analysis)}</div>'
        + render_decision_thesis_drivers(analysis)
        + f'<div class="pt-decision-row pt-risk-decision-row">{render_decision_checklist(analysis)}{render_decision_risks(analysis)}</div>'
        + render_decision_recent_changes(analysis)
        + render_advanced_model_details(analysis)
        + "</div>"
    )


def render_dataframe(rows: list[dict[str, object]], height: int = 360) -> None:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=height)
