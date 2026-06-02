from __future__ import annotations

from math import isfinite

from pineterminal.calculations import calculate_expected_return
from pineterminal.types import Company, ValuationModel, ValuationScenario


METHOD_LABELS = {
    "EV/Sales": {
        "metric": "Revenue",
        "metric_label": "Revenue ({year})",
        "multiple_label": "EV / Sales",
        "formula": (
            "Future EV = Future Revenue x EV/Sales Multiple",
            "Future Equity Value = Future EV - Net Debt",
            "Future Share Price = Future Equity Value / Diluted Shares",
        ),
    },
    "EV/EBITDA": {
        "metric": "EBITDA",
        "metric_label": "EBITDA ({year})",
        "multiple_label": "EV / EBITDA",
        "formula": (
            "Future EV = Future EBITDA x EV/EBITDA Multiple",
            "Future Equity Value = Future EV - Net Debt",
            "Future Share Price = Future Equity Value / Diluted Shares",
        ),
    },
    "P/E": {
        "metric": "EPS",
        "metric_label": "EPS ({year})",
        "multiple_label": "P/E Multiple",
        "formula": ("Future Share Price = Future EPS x P/E Multiple",),
    },
    "Asset Price Scenario": {
        "metric": "Asset Price",
        "metric_label": "Bitcoin Price",
        "multiple_label": "NAV / Share Estimate",
        "formula": ("Future ETF Value = NAV / share based on asset price scenario",),
    },
    "Revenue Multiple": {
        "metric": "Revenue",
        "metric_label": "Revenue ({year})",
        "multiple_label": "Revenue Multiple",
        "formula": (
            "Future Equity Value = Future Revenue x Revenue Multiple",
            "Future Share Price = Future Equity Value / Diluted Shares",
        ),
    },
}


VALUATION_SPECS: dict[str, dict[str, object]] = {
    "AMPX": {
        "valuation_method": "EV/Sales",
        "model_year": 2028,
        "net_debt": 5_000_000,
        "shares": 90_750_000,
        "key_assumption": "Revenue reaches $260M by 2028 at 7.0x EV / Sales.",
        "scenarios": [
            ("Bear Case", 115_000_000, 4.0, 76_000_000, 0.25, "Growth slows and dilution increases.", "Needs proof"),
            ("Base Case", 260_000_000, 7.0, 90_750_000, 0.50, "Revenue growth continues and margins improve.", "Model assumptions"),
            ("Bull Case", 500_000_000, 10.0, 111_000_000, 0.25, "Customer adoption accelerates and premium multiple holds.", "Upside case"),
        ],
    },
    "MRVL": {
        "valuation_method": "EV/Sales",
        "model_year": 2028,
        "net_debt": 3_100_000_000,
        "shares": 865_000_000,
        "key_assumption": "AI data-center, custom silicon, and networking growth must offset cyclical pressure in legacy segments.",
        "scenarios": [
            ("Bear Case", 8_200_000_000, 5.0, 865_000_000, 0.25, "AI infrastructure demand slows, legacy semiconductor weakness persists, and valuation multiple compresses.", "Needs monitoring"),
            ("Base Case", 10_400_000_000, 7.6, 865_000_000, 0.50, "Data-center and custom silicon growth offset cyclical weakness, with valuation multiple broadly holding.", "Model assumptions"),
            ("Bull Case", 13_200_000_000, 9.2, 865_000_000, 0.25, "AI custom silicon and networking demand accelerate, supporting revenue growth and premium multiple.", "Upside case"),
        ],
    },
    "VICR": {
        "valuation_method": "EV/Sales",
        "model_year": 2028,
        "net_debt": -250_000_000,
        "shares": 44_000_000,
        "key_assumption": "Revenue recovery and margin normalization are required for upside.",
        "scenarios": [
            ("Bear Case", 350_000_000, 3.0, 44_000_000, 0.25, "Power electronics demand remains uneven and margin recovery stalls.", "Needs proof"),
            ("Base Case", 525_000_000, 4.5, 44_000_000, 0.50, "Revenue recovers as power component demand improves and margins normalize.", "Model assumptions"),
            ("Bull Case", 720_000_000, 6.0, 44_000_000, 0.25, "High-performance power module adoption strengthens and valuation support improves.", "Upside case"),
        ],
    },
    "IONQ": {
        "valuation_method": "EV/Sales",
        "model_year": 2028,
        "net_debt": -420_000_000,
        "shares": 270_000_000,
        "key_assumption": "Long-term quantum adoption must accelerate enough to justify current valuation.",
        "scenarios": [
            ("Bear Case", 420_000_000, 6.0, 270_000_000, 0.25, "Commercial quantum adoption remains slow and speculative multiples compress.", "Needs proof"),
            ("Base Case", 690_000_000, 9.0, 270_000_000, 0.50, "Government and enterprise pilots convert gradually into early commercial revenue.", "Model assumptions"),
            ("Bull Case", 1_100_000_000, 12.0, 290_000_000, 0.25, "Quantum adoption moves into early production workloads and premium valuation holds.", "Upside case"),
        ],
    },
    "MP": {
        "valuation_method": "EV/EBITDA",
        "model_year": 2028,
        "net_debt": -67_000_000,
        "shares": 174_000_000,
        "key_assumption": "Rare earth pricing and downstream magnet execution drive upside.",
        "scenarios": [
            ("Bear Case", 180_000_000, 12.0, 174_000_000, 0.25, "Rare earth pricing remains soft and processing margins stay pressured.", "Needs monitoring"),
            ("Base Case", 420_000_000, 12.0, 174_000_000, 0.50, "Policy support and downstream execution improve EBITDA visibility.", "Model assumptions"),
            ("Bull Case", 700_000_000, 13.5, 180_000_000, 0.25, "Commodity pricing, defense demand, and magnet execution lift earnings power.", "Upside case"),
        ],
    },
    "FBTC": {
        "valuation_method": "Asset Price Scenario",
        "model_year": 2028,
        "key_assumption": "Expected value is primarily driven by Bitcoin price scenarios.",
        "scenarios": [
            ("Bear Case", 85_000, None, None, 0.25, "Bitcoin price falls and ETF NAV declines.", "Needs monitoring", 0.72),
            ("Base Case", 140_000, None, None, 0.50, "Bitcoin appreciates moderately while ETF demand remains constructive.", "Model assumptions", 1.18),
            ("Bull Case", 210_000, None, None, 0.25, "Bitcoin materially appreciates as institutional allocation expands.", "Upside case", 1.75),
        ],
    },
    "CEG": {
        "valuation_method": "P/E",
        "model_year": 2028,
        "key_assumption": "Power demand and nuclear contract pricing support long-term earnings growth.",
        "scenarios": [
            ("Bear Case", 13.50, 18.0, None, 0.25, "Power pricing cools and grid delays limit earnings growth.", "Needs monitoring"),
            ("Base Case", 17.50, 20.0, None, 0.50, "Data-center power contracts support durable earnings growth.", "Model assumptions"),
            ("Bull Case", 21.00, 22.0, None, 0.25, "Nuclear scarcity and long-duration contracts support premium earnings power.", "Upside case"),
        ],
    },
    "NVDA": {
        "valuation_method": "P/E",
        "model_year": 2028,
        "key_assumption": "AI compute demand and margin durability must support premium valuation.",
        "scenarios": [
            ("Bear Case", 34.00, 28.0, None, 0.25, "AI demand normalizes and premium semiconductor multiples compress.", "Needs monitoring"),
            ("Base Case", 45.00, 32.0, None, 0.50, "AI compute demand stays durable and margins remain structurally high.", "Model assumptions"),
            ("Bull Case", 58.00, 38.0, None, 0.25, "AI platform demand expands across training, inference, networking, and software attach.", "Upside case"),
        ],
    },
}


def _number(value: object) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return number if isfinite(number) else None
    except (TypeError, ValueError):
        return None


def get_valuation_method(ticker: str) -> str:
    spec = VALUATION_SPECS.get(ticker.upper())
    if spec:
        return str(spec["valuation_method"])
    return "EV/Sales"


def getValuationMethod(ticker: str) -> str:
    return get_valuation_method(ticker)


def get_scenario_labels_by_method(valuation_method: str) -> dict[str, object]:
    return METHOD_LABELS.get(valuation_method, METHOD_LABELS["EV/Sales"])


def getScenarioLabelsByMethod(valuation_method: str) -> dict[str, object]:
    return get_scenario_labels_by_method(valuation_method)


def format_financial_value(value: float | None, unit: str = "dollars") -> str:
    if value is None:
        return "N/A"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if unit in {"per_share", "eps"}:
        return f"{sign}${magnitude:,.2f}"
    if unit == "asset_price":
        return f"{sign}${magnitude:,.0f}"
    if magnitude >= 1_000_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000_000:.1f}T"
    if magnitude >= 1_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        value_m = magnitude / 1_000_000
        return f"{sign}${value_m:,.0f}M" if value_m >= 100 else f"{sign}${value_m:,.1f}M"
    if unit == "dollars":
        return f"{sign}${magnitude / 1_000_000:.1f}M"
    return f"{sign}${magnitude:,.0f}"


def formatFinancialValue(value: float | None, unit: str = "dollars") -> str:
    return format_financial_value(value, unit)


def _safe_current_price(company: Company) -> float | None:
    price = _number(company.current_price)
    return price if price is not None and price > 0 else None


def _net_debt(company: Company, spec: dict[str, object]) -> float:
    if company.debt is not None or company.cash is not None:
        return float(company.debt or 0.0) - float(company.cash or 0.0)
    return float(spec.get("net_debt") or 0.0)


def _shares(company: Company, spec: dict[str, object], scenario_shares: object) -> float | None:
    explicit = _number(scenario_shares)
    if explicit and explicit > 0:
        return explicit
    spec_shares = _number(spec.get("shares"))
    if spec_shares and spec_shares > 0:
        return spec_shares
    if company.shares_outstanding and company.shares_outstanding > 0:
        return float(company.shares_outstanding)
    if company.market_cap and company.current_price:
        inferred = company.market_cap / company.current_price
        return inferred if inferred > 0 else None
    return None


def _method_unit(valuation_method: str) -> str:
    if valuation_method == "P/E":
        return "eps"
    if valuation_method == "Asset Price Scenario":
        return "asset_price"
    return "dollars"


def calculate_scenario_output(
    *,
    company: Company,
    spec: dict[str, object],
    scenario_spec: tuple[object, ...],
    valuation_method: str,
) -> ValuationScenario:
    labels = get_scenario_labels_by_method(valuation_method)
    name = str(scenario_spec[0])
    metric_value = _number(scenario_spec[1])
    multiple = _number(scenario_spec[2])
    probability = _number(scenario_spec[4]) or 0.0
    explanation = str(scenario_spec[5])
    assumption_quality = str(scenario_spec[6]) if len(scenario_spec) > 6 else "Model assumptions"
    price_factor = _number(scenario_spec[7]) if len(scenario_spec) > 7 else None
    current_price = _safe_current_price(company)
    year = int(spec.get("model_year") or 2028)
    net_debt = _net_debt(company, spec)
    shares = _shares(company, spec, scenario_spec[3])
    future_enterprise_value = 0.0
    warning = ""

    if valuation_method in {"EV/Sales", "EV/EBITDA", "Revenue Multiple"}:
        if metric_value is None or metric_value <= 0 or multiple is None or multiple <= 0 or not shares:
            future_share_price = 0.0
            warning = "Missing revenue, multiple, or share-count input."
        else:
            future_enterprise_value = metric_value * multiple
            future_share_price = round((future_enterprise_value - net_debt) / shares, 2)
    elif valuation_method == "P/E":
        if metric_value is None or metric_value <= 0 or multiple is None or multiple <= 0:
            future_share_price = 0.0
            warning = "Missing EPS or P/E multiple input."
        else:
            future_share_price = round(metric_value * multiple, 2)
    elif valuation_method == "Asset Price Scenario":
        if current_price is None:
            future_share_price = 0.0
            warning = "Missing current ETF price."
        elif price_factor is None or price_factor <= 0:
            future_share_price = 0.0
            warning = "Missing NAV/share scenario factor."
        else:
            future_share_price = round(current_price * price_factor, 2)
    else:
        future_share_price = 0.0
        warning = f"Unsupported valuation method: {valuation_method}."

    scenario_return = calculate_expected_return(future_share_price, current_price or 0.0)
    unit = _method_unit(valuation_method)
    metric_display = format_financial_value(metric_value, unit)
    future_revenue = metric_value if valuation_method == "EV/Sales" else None
    return ValuationScenario(
        name=name,
        year=year,
        revenue=metric_value or 0.0,
        ev_sales_multiple=multiple or 0.0,
        future_enterprise_value=future_enterprise_value,
        net_debt=net_debt,
        diluted_shares_outstanding=shares or 0.0,
        future_share_price=future_share_price,
        implied_return=scenario_return,
        probability=probability,
        assumption=explanation,
        data_type="Ticker-Specific Model Assumption",
        valuation_method=valuation_method,
        valuation_metric=str(labels["metric"]),
        future_revenue=future_revenue,
        future_revenue_display=format_financial_value(future_revenue, "dollars") if future_revenue else "N/A",
        valuation_metric_value=metric_value,
        valuation_metric_display=metric_display,
        valuation_multiple=multiple,
        valuation_multiple_label=str(labels["multiple_label"]),
        net_debt_adjustment=net_debt,
        assumption_quality=assumption_quality,
        warning=warning,
    )


def calculateScenarioOutput(*, company: Company, spec: dict[str, object], scenario_spec: tuple[object, ...], valuation_method: str) -> ValuationScenario:
    return calculate_scenario_output(company=company, spec=spec, scenario_spec=scenario_spec, valuation_method=valuation_method)


def _normalize_probabilities(scenarios: list[ValuationScenario]) -> tuple[list[ValuationScenario], list[str]]:
    from dataclasses import replace

    probability_sum = sum(item.probability for item in scenarios)
    if not scenarios or abs(probability_sum - 1.0) <= 0.001:
        return scenarios, []
    if probability_sum <= 0:
        equal = 1.0 / len(scenarios)
        return [replace(item, probability=equal) for item in scenarios], ["Scenario probabilities were missing and have been normalized."]
    normalized = [replace(item, probability=item.probability / probability_sum) for item in scenarios]
    return normalized, ["Scenario probabilities did not sum to 100% and have been normalized."]


def calculate_expected_value_for_scenarios(scenarios: list[ValuationScenario]) -> float | None:
    if not scenarios or any(item.future_share_price <= 0 for item in scenarios):
        return None
    return round(sum(item.future_share_price * item.probability for item in scenarios), 2)


def calculateExpectedValue(scenarios: list[ValuationScenario]) -> float | None:
    return calculate_expected_value_for_scenarios(scenarios)


def calculate_expected_return_for_model(expected_value: float | None, current_price: float | None) -> float | None:
    if expected_value is None or current_price is None or current_price <= 0:
        return None
    return calculate_expected_return(expected_value, current_price)


def calculateExpectedReturn(expected_value: float | None, current_price: float | None) -> float | None:
    return calculate_expected_return_for_model(expected_value, current_price)


def _fallback_spec(company: Company) -> dict[str, object]:
    revenue_anchor = company.revenue_ttm or max(company.market_cap / 8, 50_000_000)
    revenue_anchor = revenue_anchor if revenue_anchor >= 1_000_000 else revenue_anchor * 1_000_000
    current_multiple = company.enterprise_value / revenue_anchor if revenue_anchor else 5.0
    current_multiple = max(1.0, min(12.0, current_multiple))
    shares = company.shares_outstanding or (company.market_cap / company.current_price if company.current_price else 100_000_000)
    return {
        "valuation_method": "EV/Sales",
        "model_year": 2028,
        "key_assumption": f"{company.ticker} requires revenue growth and valuation support to justify upside.",
        "scenarios": [
            ("Bear Case", revenue_anchor * 0.85, current_multiple * 0.65, shares * 1.03, 0.25, "Growth slows and valuation multiple compresses.", "Needs review"),
            ("Base Case", revenue_anchor * 1.35, current_multiple, shares * 1.07, 0.50, "Revenue improves and the current valuation framework holds.", "Needs review"),
            ("Bull Case", revenue_anchor * 1.90, current_multiple * 1.25, shares * 1.12, 0.25, "Growth accelerates and market awards a premium valuation framework.", "Needs review"),
        ],
    }


def _interpretation(
    *,
    ticker: str,
    valuation_method: str,
    expected_return: float | None,
    base_return: float | None,
) -> str:
    if expected_return is None:
        return "Valuation model inputs are incomplete or stale. Review assumptions."
    symbol = ticker.upper()
    if symbol == "MRVL":
        if expected_return < 0:
            return "Base case sits below today's price; upside depends on stronger AI data-center growth and multiple support."
        return "Expected value is above today's price, supported by AI data-center growth assumptions."
    if symbol == "AMPX" and (base_return or 0) < 0:
        return "Base case is slightly below today's price; upside depends on bull-case execution."
    if valuation_method == "Asset Price Scenario":
        return "Expected value is driven by asset-price scenarios and ETF NAV sensitivity."
    if (base_return or 0) < 0 and expected_return < 15:
        return "Base case sits below today's price; upside depends on stronger execution and valuation support."
    if expected_return < 15:
        return "Expected return is modest, so the signal stays balanced even if the bull case is attractive."
    if expected_return > 40:
        return "Expected value is meaningfully above today's price, but execution and market support still decide the path."
    return "Expected value is above today's price, but the model still needs confirming evidence."


def get_ticker_specific_scenario_language(ticker: str, scenario_type: str) -> str:
    spec = VALUATION_SPECS.get(ticker.upper())
    if not spec:
        return ""
    for row in spec["scenarios"]:  # type: ignore[index]
        if str(row[0]).casefold().startswith(scenario_type.casefold()):
            return str(row[5])
    return ""


def getTickerSpecificScenarioLanguage(ticker: str, scenarioType: str) -> str:
    return get_ticker_specific_scenario_language(ticker, scenarioType)


def validate_valuation_model(model: ValuationModel) -> list[str]:
    warnings = list(model.warnings)
    if not model.ticker:
        warnings.append("Valuation model ticker is missing.")
    if model.current_price is None or model.current_price <= 0:
        warnings.append("Current price is missing.")
    if not model.scenarios:
        warnings.append("Scenario assumptions are missing.")
    probability_sum = sum(item.probability for item in model.scenarios)
    if model.scenarios and abs(probability_sum - 1.0) > 0.01:
        warnings.append("Scenario probabilities do not sum to 100%.")
    for scenario in model.scenarios:
        if scenario.warning:
            warnings.append(f"{scenario.name}: {scenario.warning}")
        if scenario.future_share_price <= 0:
            warnings.append(f"{scenario.name}: future share price is missing.")
        if model.valuation_method in {"EV/Sales", "EV/EBITDA", "Revenue Multiple"}:
            if (scenario.valuation_metric_value or 0) <= 0 or (scenario.valuation_multiple or 0) <= 0:
                warnings.append(f"{scenario.name}: model metric or multiple is missing.")
            if scenario.diluted_shares_outstanding <= 0:
                warnings.append(f"{scenario.name}: diluted shares are missing.")
        if model.valuation_method == "P/E" and ((scenario.valuation_metric_value or 0) <= 0 or (scenario.valuation_multiple or 0) <= 0):
            warnings.append(f"{scenario.name}: EPS or P/E multiple is missing.")
    return list(dict.fromkeys(warnings))


def validateValuationModel(model: ValuationModel) -> list[str]:
    return validate_valuation_model(model)


def get_valuation_model(company: Company) -> ValuationModel:
    from dataclasses import replace

    symbol = company.ticker.upper()
    spec = VALUATION_SPECS.get(symbol) or _fallback_spec(company)
    valuation_method = str(spec["valuation_method"])
    current_price = _safe_current_price(company)
    scenarios = [
        calculate_scenario_output(company=company, spec=spec, scenario_spec=tuple(row), valuation_method=valuation_method)
        for row in spec["scenarios"]  # type: ignore[index]
    ]
    scenarios, warnings = _normalize_probabilities(scenarios)
    expected_value = calculate_expected_value_for_scenarios(scenarios)
    expected_return = calculate_expected_return_for_model(expected_value, current_price)
    base = next((item for item in scenarios if item.name == "Base Case"), scenarios[0] if scenarios else None)
    base_return = calculate_expected_return(base.future_share_price, current_price or 0.0) if base else None
    data_status = "Updated from latest available financials" if "Live" in company.data_mode else "Model assumptions"
    if spec is not VALUATION_SPECS.get(symbol):
        data_status = "Needs refresh"
        warnings.append("Ticker-specific valuation assumptions are not yet configured.")
    model = ValuationModel(
        ticker=symbol,
        current_price=current_price,
        model_year=int(spec.get("model_year") or 2028),
        currency=company.currency,
        revenue_unit="USD",
        diluted_shares_outstanding=base.diluted_shares_outstanding if base else None,
        net_debt=base.net_debt if base else None,
        scenarios=scenarios,
        expected_value=expected_value,
        expected_return=expected_return,
        key_assumption=str(spec["key_assumption"]),
        interpretation=_interpretation(ticker=symbol, valuation_method=valuation_method, expected_return=expected_return, base_return=base_return),
        data_status=data_status,
        last_updated=company.last_updated,
        valuation_method=valuation_method,
        warnings=warnings,
    )
    validation_warnings = validate_valuation_model(model)
    if validation_warnings != model.warnings:
        model = replace(model, warnings=validation_warnings)
    return model


def getValuationModel(company: Company) -> ValuationModel:
    return get_valuation_model(company)
