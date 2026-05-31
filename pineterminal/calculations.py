from __future__ import annotations

from collections.abc import Iterable, Mapping

from pineterminal.types import (
    ExpectedValue,
    FutureValueBridgeItem,
    FundamentalMetric,
    MarketImpliedAssumptions,
    MarketReadThroughItem,
    ThemeExposure,
    ValuationScenario,
)


def _number(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_fundamental_score(metrics: Iterable[FundamentalMetric]) -> float:
    weighted_total = 0.0
    weight_total = 0.0
    for metric in metrics:
        score = _number(metric.score)
        weight = _number(metric.weight)
        if score is None or weight is None or weight <= 0:
            continue
        weighted_total += score * weight
        weight_total += weight
    return round(weighted_total / weight_total, 1) if weight_total else 0.0


def classify_business_quality(score: float) -> str:
    if score >= 8.5:
        return "High Quality Compounder"
    if score >= 7.0:
        return "Emerging Compounder"
    if score >= 5.5:
        return "Improving / Watchlist"
    if score >= 4.0:
        return "Speculative / Needs Proof"
    return "Weak Fundamentals"


def calculate_expected_value(scenarios: Iterable[ValuationScenario]) -> float:
    return round(sum(item.future_share_price * item.probability for item in scenarios), 2)


def calculate_expected_value_detail(scenarios: Iterable[ValuationScenario], current_price: float) -> ExpectedValue:
    rows = list(scenarios)
    contributions = {item.name: round(item.future_share_price * item.probability, 2) for item in rows}
    expected_price = round(sum(contributions.values()), 2)
    return ExpectedValue(
        expected_value_price=expected_price,
        current_price=current_price,
        expected_return=calculate_expected_return(expected_price, current_price),
        scenario_contributions=contributions,
    )


def calculate_expected_return(expected_value_price: float, current_price: float) -> float:
    if current_price == 0:
        return 0.0
    return round(((expected_value_price - current_price) / current_price) * 100, 1)


def calculate_future_enterprise_value(revenue: float, multiple: float) -> float:
    return revenue * multiple


def calculate_future_share_price(
    *,
    revenue: float,
    multiple: float,
    net_debt: float,
    diluted_shares_outstanding: float,
) -> float:
    if diluted_shares_outstanding <= 0:
        return 0.0
    enterprise_value = calculate_future_enterprise_value(revenue, multiple)
    equity_value = enterprise_value - net_debt
    return round(equity_value / diluted_shares_outstanding, 2)


def calculate_scenario_share_price(scenario: ValuationScenario) -> float:
    return calculate_future_share_price(
        revenue=scenario.revenue,
        multiple=scenario.ev_sales_multiple,
        net_debt=scenario.net_debt,
        diluted_shares_outstanding=scenario.diluted_shares_outstanding,
    )


def calculate_scenario_return(future_share_price: float, current_price: float) -> float:
    return calculate_expected_return(future_share_price, current_price)


def calculate_future_value_bridge(current_price: float, bridge_items: Iterable[FutureValueBridgeItem]) -> float:
    value = current_price
    for item in bridge_items:
        impact = abs(item.value_impact)
        if item.type == "negative":
            value -= impact
        else:
            value += impact
    return round(value, 2)


def calculate_investment_signal(
    *,
    fundamental_score: float,
    valuation_upside_score: float,
    catalyst_momentum_score: float,
    risk_adjustment_score: float,
) -> float:
    return round(
        fundamental_score * 0.35
        + valuation_upside_score * 0.30
        + catalyst_momentum_score * 0.20
        + risk_adjustment_score * 0.15,
        1,
    )


def classify_investment_signal(score: float, risk_level: str = "Medium") -> str:
    if score >= 8.5:
        return "Strong Buy"
    if score >= 7.0:
        return "Buy"
    if score >= 6.0:
        return "Speculative Buy"
    if score >= 4.5:
        return "Hold"
    if score >= 3.0:
        return "Avoid"
    return "Sell"


def classify_impact_score(score: float) -> str:
    if score >= 3.5:
        return "Strong Positive"
    if score >= 1.0:
        return "Positive"
    if score <= -3.5:
        return "Strong Negative"
    if score <= -1.0:
        return "Negative"
    return "Neutral"


def compare_market_implied_to_base_case(
    *,
    implied_revenue: float,
    base_revenue: float,
    implied_ev_sales: float,
    base_ev_sales: float,
) -> tuple[str, str]:
    if base_revenue <= 0:
        return "Market price broadly aligns with base case.", "warn"
    revenue_gap = (implied_revenue - base_revenue) / base_revenue
    multiple_gap = implied_ev_sales - base_ev_sales
    if revenue_gap > 0.20 and multiple_gap >= -1.0:
        return "Market expects more growth than our base case. Limited margin for error.", "bad"
    if revenue_gap < -0.20:
        return "Base case exceeds market expectations. Potential valuation gap.", "good"
    return "Market price broadly aligns with base case.", "warn"


def confidence_weight(confidence: str) -> float:
    value = confidence.casefold()
    if value == "high":
        return 1.0
    if value == "medium":
        return 0.75
    return 0.55


def calculate_net_readthrough_score(items: Iterable[MarketReadThroughItem]) -> float:
    weighted_total = 0.0
    weight_total = 0.0
    for item in items:
        weight = confidence_weight(item.confidence)
        weighted_total += item.impact_score * weight
        weight_total += weight
    return round(weighted_total / weight_total, 1) if weight_total else 0.0


def generate_signal_summary(signal: str, risk_level: str) -> str:
    summaries = {
        "Strong Buy": "Strong fundamentals, attractive upside, and supportive catalysts outweigh risks.",
        "Buy": "Positive risk/reward with solid fundamentals and meaningful upside.",
        "Speculative Buy": "High upside, high risk. Thesis is promising but execution risk remains material.",
        "Hold": "Balanced setup. Upside and risk are roughly matched.",
        "Avoid": "Risk/reward is unattractive. Upside does not adequately compensate for fundamental or valuation risk.",
        "Sell": "Thesis appears impaired or valuation/risk profile is unfavorable.",
    }
    summary = summaries.get(signal, "No rating available from the current model.")
    if risk_level == "High" and signal in {"Buy", "Strong Buy"}:
        return summary + " Risk remains high, so position sizing and milestone tracking matter."
    return summary


def getThemeReadThroughForTicker(
    ticker: str,
    company_themes: Iterable[str],
    market_updates: Iterable[Mapping[str, object]],
    theme_exposures: Iterable[ThemeExposure],
) -> list[MarketReadThroughItem]:
    """CamelCase alias kept for future TypeScript parity."""
    return get_theme_read_through_for_ticker(ticker, company_themes, market_updates, theme_exposures)


def get_theme_read_through_for_ticker(
    ticker: str,
    company_themes: Iterable[str],
    market_updates: Iterable[Mapping[str, object]],
    theme_exposures: Iterable[ThemeExposure],
) -> list[MarketReadThroughItem]:
    symbol = ticker.upper()
    company_theme_set = {theme.casefold() for theme in company_themes}
    exposures = {item.theme: item for item in theme_exposures}
    rows: list[MarketReadThroughItem] = []

    for update in market_updates:
        theme = str(update.get("theme", ""))
        exposure = exposures.get(theme)
        if exposure is None:
            continue
        impacted = [item.upper() for item in exposure.impacted_tickers]
        ticker_match = symbol in impacted
        theme_match = theme.casefold() in company_theme_set
        related_match = any(theme.casefold() in item or item in theme.casefold() for item in company_theme_set)
        long_duration_match = theme == "Rates / Treasury Yields" and any("growth" in item for item in company_theme_set)
        if not (ticker_match or theme_match or related_match or long_duration_match):
            continue

        direction = -1 if str(update.get("impact", exposure.default_impact)).startswith("Negative") else 1
        theme_match_strength = 1.0 if ticker_match else 0.75
        company_exposure = 0.92 if theme_match or related_match else 0.68
        revenue_relevance = 0.90 if direction > 0 else 0.72
        time_horizon_weight = 0.86
        confidence = str(update.get("confidence", "Medium"))
        score = direction * 5 * theme_match_strength * company_exposure * revenue_relevance * time_horizon_weight * confidence_weight(confidence)
        score = max(-5.0, min(5.0, round(score, 1)))
        rows.append(
            MarketReadThroughItem(
                date=str(update.get("date", "")),
                market_update=str(update.get("market_update", "")),
                theme=theme,
                impacted_tickers=exposure.impacted_tickers,
                impact=classify_impact_score(score),
                impact_score=score,
                confidence=confidence,
                transmission_path=exposure.transmission_path,
                why_it_matters=str(update.get("why_it_matters", "")),
                affected_valuation_lever=str(update.get("affected_valuation_lever", ", ".join(exposure.related_valuation_levers))),
                thesis_impact=str(update.get("thesis_impact", "Strengthens thesis" if direction > 0 else "Weakens thesis")),
            )
        )
    return rows


def with_market_implied_conclusion(assumptions: MarketImpliedAssumptions) -> MarketImpliedAssumptions:
    conclusion, tone = compare_market_implied_to_base_case(
        implied_revenue=assumptions.implied_revenue,
        base_revenue=assumptions.base_revenue,
        implied_ev_sales=assumptions.implied_ev_sales,
        base_ev_sales=assumptions.base_ev_sales,
    )
    return MarketImpliedAssumptions(
        implied_revenue=assumptions.implied_revenue,
        implied_ev_sales=assumptions.implied_ev_sales,
        implied_gross_margin=assumptions.implied_gross_margin,
        implied_revenue_cagr=assumptions.implied_revenue_cagr,
        base_revenue=assumptions.base_revenue,
        base_ev_sales=assumptions.base_ev_sales,
        base_gross_margin=assumptions.base_gross_margin,
        base_revenue_cagr=assumptions.base_revenue_cagr,
        conclusion=conclusion,
        tone=tone,
    )
