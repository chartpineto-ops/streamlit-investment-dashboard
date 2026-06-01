from __future__ import annotations

from dataclasses import replace
from math import isfinite

from data.financials import load_latest_company_financials
from data.market_data import fetch_quote
from pineterminal.calculations import (
    calculate_expected_return,
    calculate_fundamental_score,
    calculate_investment_signal,
    classify_investment_signal,
    generate_signal_summary,
)
from pineterminal.demo_data import ANALYSES, COMPANIES, build_company_analysis_for_company
from pineterminal.types import Company, CompanyAnalysis, FundamentalMetric
from utils.formatting import clean_ticker, fmt_date


def _number(value: object) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return number if isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _money(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.1f}M"
    return f"{sign}${magnitude:,.0f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _field(financials: dict, key: str) -> float | None:
    packet = financials.get("financial_data_packet") or {}
    fields = packet.get("fields") or {}
    return _number((fields.get(key) or {}).get("value"))


def _field_period(financials: dict) -> str:
    packet = financials.get("financial_data_packet") or {}
    return str(packet.get("structured_values_period_label") or packet.get("reported_period_label") or "Latest period")


def _score_margin(value: float | None) -> float:
    if value is None:
        return 5.0
    if value >= 60:
        return 8.5
    if value >= 35:
        return 7.3
    if value >= 20:
        return 6.2
    if value >= 0:
        return 4.8
    return 3.0


def _score_cash_flow(fcf: float | None, revenue: float | None) -> float:
    if fcf is None:
        return 5.0
    if fcf >= 0:
        return 7.2
    margin = abs(fcf) / revenue if revenue else None
    if margin is None:
        return 4.5
    if margin < 0.15:
        return 5.6
    if margin < 0.50:
        return 4.4
    return 3.4


def _score_balance_sheet(cash: float | None, debt: float | None, fcf: float | None) -> float:
    if cash is None and debt is None:
        return 5.0
    cash_value = cash or 0.0
    debt_value = debt or 0.0
    if cash_value > debt_value * 3:
        return 7.4
    if cash_value >= debt_value:
        return 6.5
    if fcf is not None and fcf < 0 and cash_value / abs(fcf) < 4:
        return 4.2
    return 5.4


def _themes_for_company(base: Company | None, quote: dict) -> list[str]:
    if base is not None:
        return base.themes
    themes = []
    for value in (quote.get("industry"), quote.get("sector"), quote.get("quote_type")):
        text = str(value or "").strip()
        if text and text not in themes:
            themes.append(text)
    return themes or ["General Equity"]


def _generic_company(symbol: str, quote: dict) -> Company:
    price = _number(quote.get("price")) or 1.0
    market_cap = _number(quote.get("market_cap")) or 0.0
    return Company(
        ticker=symbol,
        company_name=str(quote.get("company_name") or symbol),
        sector=str(quote.get("sector") or "Unknown"),
        industry=str(quote.get("industry") or "General Equity"),
        themes=_themes_for_company(None, quote),
        current_price=price,
        daily_change=_number(quote.get("daily_change_pct")) or 0.0,
        market_cap=market_cap,
        enterprise_value=_number(quote.get("enterprise_value")) or market_cap,
        week52_low=_number(quote.get("fifty_two_week_low")) or price,
        week52_high=_number(quote.get("fifty_two_week_high")) or price,
        market_status="Live Quote",
        last_updated=str(quote.get("last_updated") or "N/A"),
        data_mode="Live Quote",
        data_source=str(quote.get("source") or "Yahoo Finance/yfinance"),
        day_change_dollar=_number(quote.get("daily_change")),
        shares_outstanding=_number(quote.get("shares_outstanding")),
    )


def _merge_company(symbol: str, base: Company | None, quote: dict, financials: dict) -> Company:
    fallback = base or _generic_company(symbol, quote)
    latest = financials.get("latest_financials") or {}
    revenue = _field(financials, "revenue") or _number(latest.get("revenue"))
    gross_margin = _field(financials, "gross_margin") or _number(latest.get("gross_margin"))
    fcf = _field(financials, "free_cash_flow") or _number(latest.get("free_cash_flow"))
    cash = _field(financials, "cash") or _number(latest.get("cash")) or _number(quote.get("total_cash"))
    debt = _field(financials, "total_debt") or _number(latest.get("total_debt")) or _number(quote.get("total_debt"))
    shares = _number(quote.get("shares_outstanding")) or _number(latest.get("shares_outstanding")) or fallback.shares_outstanding
    quote_ok = quote.get("status") == "OK"
    financial_ok = financials.get("status") not in {None, "Error"}
    data_source = "Yahoo Finance"
    if financial_ok:
        data_source += " + SEC XBRL"
    return replace(
        fallback,
        ticker=symbol,
        company_name=str(quote.get("company_name") or fallback.company_name),
        sector=str(quote.get("sector") or fallback.sector),
        industry=str(quote.get("industry") or fallback.industry),
        themes=_themes_for_company(fallback if base else None, quote),
        current_price=_number(quote.get("price")) or fallback.current_price,
        daily_change=_number(quote.get("daily_change_pct")) if _number(quote.get("daily_change_pct")) is not None else fallback.daily_change,
        market_cap=_number(quote.get("market_cap")) or fallback.market_cap,
        enterprise_value=_number(quote.get("enterprise_value")) or fallback.enterprise_value,
        week52_low=_number(quote.get("fifty_two_week_low")) or fallback.week52_low,
        week52_high=_number(quote.get("fifty_two_week_high")) or fallback.week52_high,
        market_status="Live Quote" if quote_ok else fallback.market_status,
        last_updated=fmt_date(quote.get("last_updated") or financials.get("last_updated") or fallback.last_updated),
        data_mode="Live + Model" if quote_ok else "Demo Fallback",
        data_source=data_source if quote_ok else fallback.data_source,
        revenue_ttm=(revenue * 4) if revenue is not None else fallback.revenue_ttm,
        gross_margin=gross_margin if gross_margin is not None else fallback.gross_margin,
        cash=cash if cash is not None else fallback.cash,
        debt=debt if debt is not None else fallback.debt,
        day_change_dollar=_number(quote.get("daily_change")) if _number(quote.get("daily_change")) is not None else fallback.day_change_dollar,
        shares_outstanding=shares,
        cash_burn_ttm=(fcf * 4) if fcf is not None else fallback.cash_burn_ttm,
    )


def _live_metrics(base_metrics: list[FundamentalMetric], financials: dict) -> list[FundamentalMetric]:
    latest = financials.get("latest_financials") or {}
    period = _field_period(financials)
    revenue = _field(financials, "revenue") or _number(latest.get("revenue"))
    revenue_yoy = _field(financials, "revenue_yoy_growth") or _number(latest.get("revenue_yoy"))
    gross_margin = _field(financials, "gross_margin") or _number(latest.get("gross_margin"))
    operating_income = _field(financials, "operating_income") or _number(latest.get("operating_income"))
    fcf = _field(financials, "free_cash_flow") or _number(latest.get("free_cash_flow"))
    cash = _field(financials, "cash") or _number(latest.get("cash"))
    debt = _field(financials, "total_debt") or _number(latest.get("total_debt"))
    replacements = {
        "Revenue Growth": (
            _percent(revenue_yoy) if revenue_yoy is not None else _money(revenue),
            "YoY growth" if revenue_yoy is not None else f"{period} revenue",
            7.0 if revenue_yoy is not None and revenue_yoy > 30 else 5.8 if revenue is not None else 5.0,
            "up" if revenue_yoy is not None and revenue_yoy > 0 else "flat",
            "Positive" if revenue_yoy is not None and revenue_yoy > 0 else "Neutral",
        ),
        "Gross Margin": (_percent(gross_margin), period, _score_margin(gross_margin), "flat", "Neutral"),
        "Operating Leverage": (_money(operating_income), f"{period} operating income", 6.5 if operating_income and operating_income > 0 else 4.5, "flat", "Neutral"),
        "Free Cash Flow": (_money(fcf), f"{period} FCF", _score_cash_flow(fcf, revenue), "down" if fcf and fcf < 0 else "up", "Positive" if fcf and fcf > 0 else "Negative"),
        "Balance Sheet": ("Net Cash" if (cash or 0) >= (debt or 0) else "Net Debt", f"Cash {_money(cash)} / debt {_money(debt)}", _score_balance_sheet(cash, debt, fcf), "flat", "Positive" if (cash or 0) >= (debt or 0) else "Neutral"),
    }
    rows = []
    for metric in base_metrics:
        values = replacements.get(metric.name)
        if values is None:
            rows.append(metric)
            continue
        value, label, score, trend, status = values
        rows.append(replace(metric, value=value, label=label, score=score, trend=trend, status=status, data_type="Live Source"))
    return rows


def _recalculate_signal(analysis: CompanyAnalysis, metrics: list[FundamentalMetric]) -> CompanyAnalysis:
    expected_return = calculate_expected_return(analysis.expected_value, analysis.company.current_price)
    breakdown = dict(analysis.investment_signal.score_breakdown)
    fundamental_score = calculate_fundamental_score(metrics)
    valuation_score = breakdown.get("Valuation / Upside", (5.0, 0.30))[0]
    catalyst_score = breakdown.get("Catalyst / Momentum", (5.0, 0.20))[0]
    risk_score = breakdown.get("Risk Adjustment", (5.0, 0.15))[0]
    total_score = calculate_investment_signal(
        fundamental_score=fundamental_score,
        valuation_upside_score=valuation_score,
        catalyst_momentum_score=catalyst_score,
        risk_adjustment_score=risk_score,
    )
    signal_label = classify_investment_signal(total_score)
    investment_signal = replace(
        analysis.investment_signal,
        signal=signal_label,
        total_score=total_score,
        summary=generate_signal_summary(signal_label, analysis.investment_signal.risk_level),
        score_breakdown={
            "Fundamental Score": (fundamental_score, 0.35),
            "Valuation / Upside": (valuation_score, 0.30),
            "Catalyst / Momentum": (catalyst_score, 0.20),
            "Risk Adjustment": (risk_score, 0.15),
        },
    )
    expected_detail = replace(
        analysis.expected_value_detail,
        current_price=analysis.company.current_price,
        expected_return=expected_return,
    )
    return replace(analysis, fundamental_metrics=metrics, investment_signal=investment_signal, expected_value_detail=expected_detail)


def load_dashboard_analysis(ticker: str) -> CompanyAnalysis:
    symbol = clean_ticker(ticker) or "AMPX"
    base = COMPANIES.get(symbol)
    quote = fetch_quote(symbol)
    financials = load_latest_company_financials(symbol)
    company = _merge_company(symbol, base, quote, financials)
    analysis = build_company_analysis_for_company(company)
    if financials.get("status") not in {None, "Error"}:
        analysis = _recalculate_signal(analysis, _live_metrics(analysis.fundamental_metrics, financials))
    return analysis


def search_tickers() -> list[str]:
    return sorted(ANALYSES.keys())
