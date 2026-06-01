from __future__ import annotations

from html import escape

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
    ValuationScenario,
)


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
    if "negative" in value or "risk" in value or "not met" in value or "high" == value:
        return "bad"
    if "medium" in value or "hold" in value or "monitor" in value:
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
    st.markdown(compact_markup, unsafe_allow_html=True)


def section(title: str, subtitle: str = "", body: str = "", action: str = "") -> str:
    subtitle_html = f"<small>{escape(subtitle)}</small>" if subtitle else ""
    action_html = f'<a class="pt-section-action">{escape(action)}</a>' if action else ""
    return f'<div class="pt-section"><div class="pt-section-title"><span>{escape(title)}</span><div>{subtitle_html}{action_html}</div></div>{body}</div>'


def value_row(label: str, value: str, tone: str = "neutral") -> str:
    return f'<div class="pt-kv-row"><span>{escape(label)}</span><b class="{escape(tone)}">{escape(value)}</b></div>'


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
    html(
        f"""
        <div class="pt-topbar">
          <div class="pt-breadcrumb">Dashboard / <b>{escape(ticker)}</b></div>
          <div class="pt-actions">
            <span class="pt-action">+ Add to Watchlist</span>
            <span class="pt-action">Share</span>
            <span class="pt-action">{escape(currency)}</span>
          </div>
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
    day_change = profile.day_change_dollar
    if day_change is None:
        day_change_label = "N/A"
    else:
        day_change_label = f"{'+' if day_change > 0 else '-' if day_change < 0 else ''}{price(abs(day_change))}"
    tags = "".join(f'<span class="pt-tag">{escape(theme)}</span>' for theme in profile.themes[:3])
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
        <div class="pt-tags">{tags}<span class="pt-status-pill">{escape(profile.market_status)}</span></div>
        <small class="pt-muted">Last updated {escape(profile.last_updated)} &bull; {escape(profile.data_source)}</small>
      </div>
      <div class="pt-header-market">
        <div class="pt-kpi pt-current-price"><span>Current Price {data_label(profile.data_mode)}</span><strong>{price(profile.current_price)}</strong><b class="{tone_for_value(profile.day_change_percent)}">{day_change_label} ({percent(profile.day_change_percent, 2)})</b>{price_detail}</div>
        <div class="pt-kpi"><span>Market Cap</span><strong>{money(profile.market_cap)}</strong></div>
        <div class="pt-kpi"><span>Enterprise Value</span><strong>{money(profile.enterprise_value)}</strong></div>
        <div class="pt-kpi pt-range-kpi"><span>52W Range</span><strong>{price(profile.week52_low)} to {price(profile.week52_high)}</strong><div class="pt-range"><div class="pt-range-track"><i style="left:{profile.week52_current_position:.1f}%"></i></div></div></div>
      </div>
      <div class="pt-header-signal">
        <div class="pt-kpi pt-score-big"><span>Fundamental Score {data_label("Derived")}</span><strong>{profile.fundamental_score:.1f}</strong><b>/10</b><small class="good">{escape(profile.fundamental_label)}</small></div>
        <div class="pt-kpi"><span>Expected 36M Return {data_label("Derived")}</span><strong class="{tone_for_value(profile.expected36m_return)}">{percent(profile.expected36m_return, 0)}</strong><b>{escape(profile.expected_return_label)}</b></div>
        <div class="pt-kpi"><span>Investment Signal {data_label("Derived")}</span><strong class="{signal_tone}">{escape(profile.investment_signal)}</strong><b>Confidence: {escape(profile.confidence)} | Risk: {escape(profile.risk_level)}</b></div>
        <div class="pt-gauge" title="Signal gauge"></div>
      </div>
    </div>
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
        {value_row(str(scenario.year) + " Revenue", money(scenario.revenue, 0))}
        {value_row("EV / Sales Multiple", f"{scenario.ev_sales_multiple:.1f}x")}
        {value_row("Future Price", price(scenario.future_share_price), "info" if name_tone == "info" else name_tone)}
        {value_row("Return", percent(implied_return, 0), tone_for_value(implied_return))}
      </dl>
      <small class="pt-scenario-note">{escape(scenario.assumption)}</small>
    </div>
    """


def render_future_value_model(analysis: CompanyAnalysis) -> str:
    cards = "".join(render_scenario_card(item, analysis.company.current_price) for item in analysis.valuation_scenarios)
    expected_return = analysis.expected_value_detail.expected_return
    probability_rows = "".join(
        value_row(f"{item.name} ({item.probability:.0%})", price(item.future_share_price))
        for item in analysis.valuation_scenarios
    )
    body = f"""
      <div class="pt-fv-grid">
        <div class="pt-scenario-grid">{cards}</div>
        <div class="pt-expected-card">
          <div class="pt-expected-head"><span class="pt-mini-label">Probability-Weighted Expected Value</span>{data_label("Derived")}</div>
          <strong>{price(analysis.expected_value)}</strong>
          <div class="pt-data-list pt-expected-list">
            {value_row("Upside / Downside", percent(expected_return, 1), tone_for_value(expected_return))}
            {probability_rows}
            {value_row("Current Price", price(analysis.company.current_price))}
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
    header = "".join(f"<th>{money(value, 0)}</th>" for value in table.revenue_columns)
    rows = ""
    for multiple in table.multiple_rows:
        cells = ""
        for revenue in table.revenue_columns:
            classes = ["base"] if (revenue, multiple) == table.highlighted_cell else []
            classes.append("upside" if table.values[(revenue, multiple)] > current_price else "downside")
            cls = " ".join(classes)
            cells += f'<td class="{cls}">{price(table.values[(revenue, multiple)])}</td>'
        rows += f"<tr><th>{multiple:.1f}x</th>{cells}</tr>"
    footer = f"Blue box = Base Case revenue x multiple estimate. Current price marker: {price(current_price)}."
    body = f'<div class="pt-sensitivity"><table class="pt-table pt-sensitivity-table"><thead><tr><th>EV / Sales Multiple</th>{header}</tr></thead><tbody>{rows}</tbody></table></div><small class="pt-table-note">{escape(footer)}</small>'
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
    overrides = {
        "AMPX": {"shares": "56.4M", "insider": "6.1%", "cash_burn": "$46.0M"},
        "MRVL": {"shares": "865.0M", "insider": "0.7%", "cash_burn": "FCF positive"},
        "IONQ": {"shares": "270.0M", "insider": "11.4%", "cash_burn": "$129.0M"},
        "MP": {"shares": "174.0M", "insider": "8.5%", "cash_burn": "$184.0M"},
        "FBTC": {"shares": "790.0M", "insider": "N/A", "cash_burn": "N/A"},
        "NVDA": {"shares": "2.47B", "insider": "4.2%", "cash_burn": "FCF positive"},
        "CEG": {"shares": "311.0M", "insider": "0.5%", "cash_burn": "FCF positive"},
    }
    extra = overrides.get(company.ticker, {})
    if company.shares_outstanding is not None:
        shares = money(company.shares_outstanding, 1).replace("$", "")
    else:
        shares = extra.get("shares", f"{base.diluted_shares_outstanding / 1_000_000:.1f}M")
    if company.cash_burn_ttm is not None:
        cash_burn = "FCF positive" if company.cash_burn_ttm >= 0 else money(abs(company.cash_burn_ttm))
    else:
        cash_burn = extra.get("cash_burn", "N/A")
    return {
        "shares": shares,
        "insider": extra.get("insider", "N/A"),
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


def render_company_dashboard(analysis: CompanyAnalysis) -> None:
    company_profile = company_profile_from_analysis(analysis)
    html(
        '<div class="pt-shell">'
        + render_company_header(company_profile)
        + render_business_quality(analysis)
        + f'<div class="pt-row-valuation">{render_future_value_model(analysis)}{render_market_readthrough(analysis)}</div>'
        + f'<div class="pt-row-assumptions">{render_must_be_true(analysis)}{render_bridge(analysis)}{render_market_implied(analysis)}</div>'
        + f'<div class="pt-row-impact">{render_sensitivity_table(analysis.sensitivity_table, analysis.company.current_price)}{render_risks(analysis)}{render_updates(analysis)}</div>'
        + f'<div class="pt-row-bottom">{render_signal(analysis)}{render_key_stats(analysis)}{render_next_events(analysis)}</div>'
        + "</div>"
    )


def render_dataframe(rows: list[dict[str, object]], height: int = 360) -> None:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=height)
