from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

from data.filings import extract_sec_concept_value, fetch_latest_periodic_sec_filing, fetch_latest_sec_filing, get_sec_company_facts
from data.market_data import fetch_quote
from utils.formatting import clean_ticker, now_et, safe_div, safe_format_date, to_float
from utils.validation import status_from_warnings

FIELD_MAP = {
    "revenue": ("Total Revenue", "Operating Revenue", "Revenue"),
    "cost_of_revenue": ("Cost Of Revenue", "Cost Revenue"),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income", "Operating Income Loss"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "eps": ("Diluted EPS", "Basic EPS", "EPS"),
    "cash": ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
    "current_assets": ("Current Assets", "Total Current Assets"),
    "total_assets": ("Total Assets",),
    "current_liabilities": ("Current Liabilities", "Total Current Liabilities"),
    "total_liabilities": ("Total Liabilities Net Minority Interest", "Total Liabilities"),
    "total_debt": ("Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"),
    "shareholders_equity": ("Stockholders Equity", "Total Equity Gross Minority Interest"),
    "operating_cash_flow": ("Operating Cash Flow", "Total Cash From Operating Activities"),
    "capital_expenditures": ("Capital Expenditure", "Capital Expenditures"),
    "free_cash_flow": ("Free Cash Flow",),
    "financing_cash_flow": ("Financing Cash Flow", "Total Cash From Financing Activities"),
    "investing_cash_flow": ("Investing Cash Flow", "Total Cash From Investing Activities"),
    "cash_change": ("Changes In Cash", "Net Change In Cash"),
}

MIN_MEANINGFUL_REVENUE = 1_000_000

SEC_CONCEPTS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ),
    "gross_profit": ("GrossProfit", "GrossProfitLoss"),
    "cost_of_revenue": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfServicesRevenue",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ),
    "operating_income": (
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ),
    "net_income": ("NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasic", "EarningsPerShareBasicAndDiluted"),
    "cash": (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndDueFromBanks",
        "Cash",
    ),
    "total_assets": ("Assets",),
    "shareholders_equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "CommonStocksIncludingAdditionalPaidInCapital",
        "RetainedEarningsAccumulatedDeficit",
    ),
    "operating_cash_flow": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    "capital_expenditures": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForProceedsFromProductiveAssets",
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
        "CapitalExpendituresIncurredButNotYetPaid",
    ),
    "shares_outstanding": (
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "EntityCommonStockSharesOutstanding",
    ),
}

SEC_TOTAL_DEBT_BROAD_CONCEPTS = (
    "DebtAndFinanceLeaseObligations",
    "LongTermDebtAndFinanceLeaseObligations",
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
)

SEC_DEBT_COMPONENT_CONCEPTS = {
    "current_debt": ("DebtCurrent", "LongTermDebtCurrent", "ShortTermDebt"),
    "long_term_debt": ("LongTermDebt",),
    "short_term_borrowings": ("ShortTermBorrowings",),
    "notes_payable": ("NotesPayable", "ConvertibleNotesPayable"),
    "finance_lease": ("FinanceLeaseLiability",),
    "operating_lease": ("OperatingLeaseLiability",),
}

SEC_ATTEMPTED_CONCEPTS = {
    **SEC_CONCEPTS,
    "total_debt": SEC_TOTAL_DEBT_BROAD_CONCEPTS + tuple(concept for concepts in SEC_DEBT_COMPONENT_CONCEPTS.values() for concept in concepts),
    "free_cash_flow": ("calculated_from_operating_cash_flow_less_capex",),
}
SEC_ATTEMPTED_CONCEPTS["gross_profit"] = SEC_CONCEPTS["gross_profit"] + SEC_CONCEPTS["cost_of_revenue"]

RECONCILIATION_METRICS = {
    "revenue": "Revenue",
    "gross_profit": "Gross Profit",
    "operating_income": "Operating Income",
    "net_income": "Net Income",
    "eps": "EPS",
    "operating_cash_flow": "Operating Cash Flow",
    "capital_expenditures": "Capex",
    "free_cash_flow": "Free Cash Flow",
    "cash": "Cash",
    "total_debt": "Total Debt",
    "total_assets": "Total Assets",
    "shareholders_equity": "Shareholders' Equity",
    "shares_outstanding": "Shares Outstanding",
}

INCOME_STATEMENT_METRICS = {"revenue", "gross_profit", "operating_income", "net_income", "eps"}
BALANCE_SHEET_METRICS = {"cash", "total_debt", "total_assets", "shareholders_equity", "shares_outstanding"}
CASH_FLOW_METRICS = {"operating_cash_flow", "capital_expenditures", "free_cash_flow"}
CHART_REQUIRED_METRICS = {"revenue": "Revenue", "eps": "EPS"}


def _label_list(values: list[str], limit: int = 5) -> str:
    cleaned = [str(value) for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return ", ".join(cleaned)
    return f"{len(cleaned)} items: " + ", ".join(cleaned[:limit])


CORE_FINANCIAL_FIELDS = [
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps",
    "cash",
    "total_debt",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "shares_outstanding",
    "total_assets",
    "shareholders_equity",
]

DERIVED_FINANCIAL_FIELDS = [
    "gross_margin",
    "operating_margin",
    "net_margin",
    "fcf_margin",
    "net_cash_or_debt",
    "cash_runway",
    "revenue_yoy_growth",
]

NOT_APPLICABLE_QUOTE_TYPES = {"ETF", "MUTUALFUND", "FUND", "INDEX", "CRYPTOCURRENCY"}


def _date_label(value) -> str | None:
    formatted = safe_format_date(value)
    return None if formatted == "N/A" else formatted


def _value_present(value) -> bool:
    return to_float(value) is not None


def _source_status_reason(source_status: str, values: dict, missing: list[str], source: str | None, note: str | None) -> str:
    if source_status == "OK":
        return "Core latest-quarter structured values are available and period-aligned."
    if source_status == "Stale structured values":
        return note or "Latest filing metadata is newer than the structured values currently available."
    if source_status == "Filing metadata only":
        return note or "Latest filing was detected, but structured values were unavailable."
    if source_status == "Partial":
        found = []
        for key in ("revenue", "eps", "net_income", "cash", "operating_cash_flow"):
            if _value_present(values.get(key)):
                found.append(RECONCILIATION_METRICS.get(key, key))
        missing_labels = [RECONCILIATION_METRICS.get(key, key) for key in missing or []]
        found_text = _label_list(found) or "Some values"
        missing_text = _label_list(missing_labels) or "some optional fields"
        source_text = source or "structured source"
        return f"{found_text} found from {source_text}; missing: {missing_text}."
    return note or "Source returned incomplete or unavailable latest-quarter data."


def _metric_label(key: str) -> str:
    return RECONCILIATION_METRICS.get(key, key.replace("_", " ").title())


def _metric_source_detail(
    *,
    value=None,
    source: str = "SEC XBRL/companyfacts",
    concept: str | None = None,
    status: str = "N/A",
    note: str = "",
    fallback_used: bool = False,
    fallback_attempted: bool = False,
    fallback_source: str | None = None,
    component_concepts_used: tuple[str, ...] | list[str] | None = None,
    calculation_formula: str | None = None,
    source_inputs: str | None = None,
    period: str | None = None,
    period_end_date=None,
) -> dict:
    return {
        "value": value,
        "source": source,
        "concept_used": concept,
        "concepts_attempted": (),
        "fallback_used": fallback_used,
        "fallback_attempted": fallback_attempted,
        "fallback_source": fallback_source,
        "component_concepts_used": tuple(component_concepts_used or ()),
        "calculation_formula": calculation_formula,
        "source_inputs": source_inputs,
        "status": status,
        "note": note,
        "period": period,
        "period_end_date": period_end_date,
    }


def _set_attempted_concepts(metric_sources: dict, key: str) -> None:
    if key in metric_sources:
        metric_sources[key]["concepts_attempted"] = SEC_ATTEMPTED_CONCEPTS.get(key, ())


def _drop_missing(missing: list[str], key: str) -> None:
    while key in missing:
        missing.remove(key)


def _derive_capex_from_fcf(
    values: dict,
    metric_sources: dict,
    missing: list[str],
    *,
    period_label: str | None,
    period_end_date,
    source: str,
) -> None:
    if values.get("capital_expenditures") is not None:
        return
    ocf = to_float(values.get("operating_cash_flow"))
    fcf = to_float(values.get("free_cash_flow"))
    if ocf is None or fcf is None:
        return
    values["capital_expenditures"] = ocf - fcf
    _drop_missing(missing, "capital_expenditures")
    metric_sources["capital_expenditures"] = _metric_source_detail(
        value=values["capital_expenditures"],
        source="Calculated",
        concept=None,
        status="Calculated",
        note="Capex derived from Operating Cash Flow less Free Cash Flow because a direct capex line was unavailable.",
        calculation_formula="Operating Cash Flow - Free Cash Flow",
        source_inputs=f"Operating Cash Flow, Free Cash Flow from {source}",
        period=period_label,
        period_end_date=period_end_date,
    )
    _set_attempted_concepts(metric_sources, "capital_expenditures")


def _derive_eps_from_net_income_and_shares(
    values: dict,
    metric_sources: dict,
    missing: list[str],
    *,
    period_label: str | None,
    period_end_date,
    source: str,
) -> None:
    if values.get("eps") is not None:
        return
    net_income = to_float(values.get("net_income"))
    shares = to_float(values.get("shares_outstanding"))
    if net_income is None or shares is None or shares == 0:
        return
    values["eps"] = net_income / shares
    _drop_missing(missing, "eps")
    metric_sources["eps"] = _metric_source_detail(
        value=values["eps"],
        source="Calculated",
        concept=None,
        status="Partial estimate",
        note="EPS estimated from Net Income divided by shares outstanding because a direct EPS line was unavailable.",
        calculation_formula="Net Income / Shares Outstanding",
        source_inputs=f"Net Income from {source}; shares outstanding from quote or SEC data",
        period=period_label,
        period_end_date=period_end_date,
    )
    _set_attempted_concepts(metric_sources, "eps")


def _missing_metric_note(key: str, fallback_attempted: bool = False) -> str:
    label = _metric_label(key)
    if key == "gross_profit":
        if fallback_attempted:
            return "Gross Profit was not found under mapped SEC concepts and no period-aligned Yahoo Finance fallback was available."
        return "No mapped gross profit concept found for this period. Period-aligned Yahoo Finance fallback will be used if available."
    if key == "total_debt":
        return "No mapped total debt or debt component concepts found for this period."
    if key == "free_cash_flow":
        return "Free Cash Flow could not be calculated because Operating Cash Flow or Capex is missing."
    if fallback_attempted:
        return f"{label} was not found under mapped SEC concepts and no period-aligned Yahoo Finance fallback was available."
    return f"No mapped SEC concept found for {label} in this filing period."


def _display_metric_status(status: str | None, value=None) -> str:
    raw = str(status or "").strip()
    if raw in {"SEC concept found", "OK", "Direct"} and _value_present(value):
        return "Direct"
    if raw in {"Fallback", "yfinance fallback"} and _value_present(value):
        return "Fallback"
    if raw == "Calculated":
        return "Calculated"
    if raw in {"Partial estimate", "Estimated"}:
        return "Partial estimate"
    if raw == "Not applicable":
        return "Not applicable"
    if raw in {"Missing concept", "Missing", "N/A"} or not _value_present(value):
        return "Missing"
    return raw or ("Direct" if _value_present(value) else "Missing")


def _completeness_status(score: float | int | None, ticker_type: str | None = None) -> str:
    if ticker_type in {"etf_fund", "crypto_proxy", "invalid_unknown"}:
        return "Not applicable" if ticker_type != "invalid_unknown" else "Insufficient"
    if score is None:
        return "Insufficient"
    if score >= 98:
        return "Complete"
    if score >= 95:
        return "Mostly Complete"
    if score >= 80:
        return "Partial"
    if score >= 25:
        return "Limited"
    return "Insufficient"


def _ticker_type(symbol: str, quote: dict | None) -> str:
    quote = quote or {}
    quote_type = str(quote.get("quote_type") or "").upper()
    if quote.get("status") == "Error" and not quote_type:
        return "invalid_unknown"
    if not quote_type and quote.get("price") is None and str(quote.get("company_name") or "").upper() == str(symbol).upper():
        return "invalid_unknown"
    if quote_type in {"ETF", "MUTUALFUND", "FUND", "INDEX"}:
        return "etf_fund"
    if quote_type == "CRYPTOCURRENCY" or str(symbol).upper().endswith("-USD"):
        return "crypto_proxy"
    if quote_type in {"EQUITY", "COMMONSTOCK", "ADR", "PREFERREDSTOCK"} or quote.get("company_name"):
        return "operating_company"
    return "unknown"


def _financial_quality_categories(metric_sources: dict, values: dict, missing: list[str] | None = None, not_applicable: list[str] | None = None, ticker_type: str | None = None) -> dict:
    missing_set = set(missing or [])
    not_applicable_set = set(not_applicable or [])
    categories = {"found_direct": [], "fallback": [], "calculated": [], "estimated": [], "missing": [], "not_applicable": []}
    credits = 0.0
    denominator = 0.0
    for key in CORE_FINANCIAL_FIELDS:
        label = _metric_label(key)
        if key in not_applicable_set:
            categories["not_applicable"].append(label)
            continue
        denominator += 1.0
        detail = metric_sources.get(key) or {}
        value = values.get(key)
        if not _value_present(value):
            value = detail.get("value")
        status = _display_metric_status(detail.get("status"), value)
        if key in missing_set or status == "Missing" or not _value_present(value):
            categories["missing"].append(label)
            continue
        if status == "Calculated":
            categories["calculated"].append(label)
            credits += 1.0
        elif status == "Fallback":
            categories["fallback"].append(label)
            credits += 1.0
        elif status in {"Partial estimate", "Estimated"}:
            categories["estimated"].append(label)
            credits += 0.5
        else:
            categories["found_direct"].append(label)
            credits += 1.0
    score = round(credits / denominator * 100) if denominator else None
    categories.update(
        {
            "required_count": int(denominator),
            "available_count": len(categories["found_direct"]) + len(categories["fallback"]) + len(categories["calculated"]) + len(categories["estimated"]),
            "direct_count": len(categories["found_direct"]),
            "fallback_count": len(categories["fallback"]),
            "calculated_count": len(categories["calculated"]),
            "estimated_count": len(categories["estimated"]),
            "missing_count": len(categories["missing"]),
            "not_applicable_count": len(categories["not_applicable"]),
            "completeness_score": score,
            "source_status": _completeness_status(score, ticker_type),
        }
    )
    return categories


def _compact_source_status_note(quality: dict) -> str:
    if not quality:
        return "Latest-period data quality unavailable. Review reconciliation."
    if quality.get("source_status") == "Not applicable":
        return "Corporate financial statements are not applicable for this ticker type."
    score = quality.get("completeness_score")
    score_text = "N/A" if score is None else f"{score}%"
    estimated_count = quality.get("estimated_count", 0)
    missing_count = quality.get("missing_count", 0)
    missing_label = "field" if missing_count == 1 else "fields"
    status = quality.get("source_status") or _completeness_status(score)
    missing_fields = quality.get("missing") or []
    missing_text = ", ".join(missing_fields) if missing_fields else "None"
    return (
        f"Completeness: {score_text} | {status} | "
        f"{quality.get('available_count', 0)} of {quality.get('required_count', 0)} core fields available. "
        f"Direct: {quality.get('direct_count', 0)}; fallback: {quality.get('fallback_count', 0)}; "
        f"calculated: {quality.get('calculated_count', 0)}; estimated: {estimated_count}. "
        f"Missing: {missing_text} ({missing_count} {missing_label}). "
        "Review reconciliation."
    )


def _calculated_metric_sentence(key: str, detail: dict) -> str:
    label = _metric_label(key)
    if key == "free_cash_flow":
        return "Free Cash Flow was calculated from Operating Cash Flow less Capex."
    formula = detail.get("calculation_formula")
    return f"{label} was calculated" + (f" as {formula}" if formula else "") + "."


def _estimated_metric_sentence(key: str, detail: dict) -> str:
    label = _metric_label(key)
    components = [str(item) for item in detail.get("component_concepts_used") or () if item]
    if key == "total_debt" and components:
        return f"Total Debt was partially estimated from available debt components: {' + '.join(components)}."
    return f"{label} was partially estimated; review the reconciliation row for component details."


def _latest_source_reason(release: dict, values: dict, missing: list[str]) -> str:
    metric_sources = release.get("metric_sources") or {}
    quality = _financial_quality_categories(metric_sources, values, missing)
    pieces = []
    if quality["found_direct"]:
        pieces.append("Found directly: " + ", ".join(quality["found_direct"]) + ".")
    if quality["fallback"]:
        pieces.append("Fallback: " + ", ".join(quality["fallback"]) + " sourced from period-aligned Yahoo Finance data.")
    if quality["calculated"]:
        calculated = []
        for label in quality["calculated"]:
            key = next((item for item, metric_label in RECONCILIATION_METRICS.items() if metric_label == label), "")
            calculated.append(_calculated_metric_sentence(key, metric_sources.get(key) or {}))
        pieces.extend(calculated)
    if quality["estimated"]:
        for label in quality["estimated"]:
            key = next((item for item, metric_label in RECONCILIATION_METRICS.items() if metric_label == label), "")
            pieces.append(_estimated_metric_sentence(key, metric_sources.get(key) or {}))
    if quality["missing"]:
        pieces.append("Missing: " + ", ".join(quality["missing"]) + ".")
        if "Gross Profit" in quality["missing"]:
            pieces.append("Gross Profit was not found under mapped SEC concepts and no period-aligned fallback was available.")
    if not pieces:
        return release.get("data_quality_note") or "Latest-quarter financial coverage is unavailable."
    return " ".join(pieces)


def _apply_quality_metadata(release: dict, values: dict | None = None, missing: list[str] | None = None, ticker_type: str | None = None) -> dict:
    values = values or {key: release.get(key) for key in CORE_FINANCIAL_FIELDS}
    missing = missing if missing is not None else list(release.get("missing_fields") or [])
    not_applicable = CORE_FINANCIAL_FIELDS if release.get("source_status") == "Not applicable" or ticker_type in {"etf_fund", "crypto_proxy"} else []
    quality = _financial_quality_categories(release.get("metric_sources") or {}, values, missing, not_applicable=not_applicable, ticker_type=ticker_type)
    release["financial_data_quality"] = quality
    release["data_completeness_score"] = quality.get("completeness_score")
    release["compact_source_status_note"] = _compact_source_status_note(quality)
    protected_statuses = {"Stale structured values", "Filing metadata only", "Structured values only", "Not applicable", "Insufficient data", "Source error"}
    if release.get("source_status") not in protected_statuses and quality.get("source_status"):
        release["source_status"] = quality.get("source_status")
    return release


def _safe_margin(numerator, revenue) -> float | None:
    revenue_value = to_float(revenue)
    numerator_value = to_float(numerator)
    if revenue_value is None or numerator_value is None or abs(revenue_value) < MIN_MEANINGFUL_REVENUE:
        return None
    margin = numerator_value / revenue_value * 100
    return margin if abs(margin) <= 300 else None


def _statement(obj: yf.Ticker, names: tuple[str, ...]) -> pd.DataFrame:
    for name in names:
        try:
            value = getattr(obj, name)
            if callable(value):
                value = value()
            if isinstance(value, pd.DataFrame) and not value.empty:
                return value
        except Exception:
            continue
    return pd.DataFrame()


def _periods(*frames: pd.DataFrame) -> list[pd.Timestamp]:
    out = set()
    for frame in frames:
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        for col in frame.columns:
            try:
                out.add(pd.Timestamp(col).tz_localize(None) if pd.Timestamp(col).tzinfo else pd.Timestamp(col))
            except Exception:
                pass
    return sorted(out)


def _line(frame: pd.DataFrame, period, aliases: tuple[str, ...]) -> float | None:
    if frame.empty or period is None:
        return None
    lookup = {str(idx).casefold().replace(" ", ""): idx for idx in frame.index}
    column = None
    for col in frame.columns:
        try:
            if pd.Timestamp(col).date() == pd.Timestamp(period).date():
                column = col
                break
        except Exception:
            pass
    if column is None:
        return None
    for alias in aliases:
        idx = lookup.get(alias.casefold().replace(" ", ""))
        if idx is not None:
            return to_float(frame.loc[idx, column])
    return None


def _line_nearest(frame: pd.DataFrame, period, aliases: tuple[str, ...], max_days: int = 120) -> float | None:
    if frame.empty or period is None:
        return None
    exact = _line(frame, period, aliases)
    if exact is not None:
        return exact
    try:
        target = pd.Timestamp(period)
        candidates = []
        for col in frame.columns:
            col_ts = pd.Timestamp(col)
            candidates.append((abs((col_ts - target).days), col_ts))
        if not candidates:
            return None
        distance, nearest = sorted(candidates)[0]
        if distance > max_days:
            return None
        return _line(frame, nearest, aliases)
    except Exception:
        return None


def _normalize_history(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame, quarterly: bool, limit: int = 8) -> pd.DataFrame:
    periods = _periods(income) or _periods(income, balance, cashflow)
    periods = periods[-limit:]
    rows = []
    for period in periods:
        row = {"period_date": period, "period": f"{period.year} Q{period.quarter}" if quarterly else f"FY {period.year}"}
        for key, aliases in FIELD_MAP.items():
            source = income if key in {"revenue", "cost_of_revenue", "gross_profit", "operating_income", "net_income", "eps"} else balance if key in {"cash", "current_assets", "total_assets", "current_liabilities", "total_liabilities", "total_debt", "shareholders_equity"} else cashflow
            row[key] = _line(source, period, aliases) if source is income else _line_nearest(source, period, aliases)
        if row.get("free_cash_flow") is None and row.get("operating_cash_flow") is not None and row.get("capital_expenditures") is not None:
            row["free_cash_flow"] = row["operating_cash_flow"] - abs(row["capital_expenditures"])
        row["gross_margin"] = _safe_margin(row.get("gross_profit"), row.get("revenue"))
        row["operating_margin"] = _safe_margin(row.get("operating_income"), row.get("revenue"))
        row["net_margin"] = _safe_margin(row.get("net_income"), row.get("revenue"))
        row["fcf_margin"] = _safe_margin(row.get("free_cash_flow"), row.get("revenue"))
        row["current_ratio"] = safe_div(row.get("current_assets"), row.get("current_liabilities"), 1)
        row["debt_to_equity"] = safe_div(row.get("total_debt"), row.get("shareholders_equity"), 1)
        row["net_debt"] = row["total_debt"] - row["cash"] if row.get("total_debt") is not None and row.get("cash") is not None else None
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values("period_date") if rows else pd.DataFrame()
    return _augment_history(frame, quarterly)


def _augment_history(frame: pd.DataFrame, quarterly: bool) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    frame = frame.copy()
    frame["period_date"] = pd.to_datetime(frame["period_date"], errors="coerce")
    frame = frame.dropna(subset=["period_date"]).sort_values("period_date")
    frame["period"] = frame.apply(
        lambda row: row.get("period") or (f"{row['period_date'].year} Q{row['period_date'].quarter}" if quarterly else f"FY {row['period_date'].year}"),
        axis=1,
    )
    for idx, row in frame.iterrows():
        if pd.isna(row.get("free_cash_flow")) and pd.notna(row.get("operating_cash_flow")) and pd.notna(row.get("capital_expenditures")):
            frame.at[idx, "free_cash_flow"] = row.get("operating_cash_flow") - abs(row.get("capital_expenditures"))
        frame.at[idx, "gross_margin"] = _safe_margin(frame.at[idx, "gross_profit"] if "gross_profit" in frame else None, frame.at[idx, "revenue"] if "revenue" in frame else None)
        frame.at[idx, "operating_margin"] = _safe_margin(frame.at[idx, "operating_income"] if "operating_income" in frame else None, frame.at[idx, "revenue"] if "revenue" in frame else None)
        frame.at[idx, "net_margin"] = _safe_margin(frame.at[idx, "net_income"] if "net_income" in frame else None, frame.at[idx, "revenue"] if "revenue" in frame else None)
        frame.at[idx, "fcf_margin"] = _safe_margin(frame.at[idx, "free_cash_flow"] if "free_cash_flow" in frame else None, frame.at[idx, "revenue"] if "revenue" in frame else None)
        frame.at[idx, "current_ratio"] = safe_div(row.get("current_assets"), row.get("current_liabilities"), 1)
        frame.at[idx, "debt_to_equity"] = safe_div(row.get("total_debt"), row.get("shareholders_equity"), 1)
        if row.get("total_debt") is not None and row.get("cash") is not None:
            frame.at[idx, "net_debt"] = row.get("total_debt") - row.get("cash")
    if not frame.empty:
        revenue_raw = frame["revenue"] if "revenue" in frame else pd.Series([pd.NA] * len(frame), index=frame.index)
        eps_raw = frame["eps"] if "eps" in frame else pd.Series([pd.NA] * len(frame), index=frame.index)
        revenue_series = pd.to_numeric(revenue_raw, errors="coerce")
        eps_series = pd.to_numeric(eps_raw, errors="coerce")
        frame["prior_revenue_for_yoy"] = revenue_series.shift(4 if quarterly else 1)
        frame["prior_revenue_for_qoq"] = revenue_series.shift(1)
        frame["revenue_yoy_growth"] = revenue_series.pct_change(4 if quarterly else 1, fill_method=None) * 100
        frame["revenue_qoq_growth"] = revenue_series.pct_change(1, fill_method=None) * 100
        frame["revenue_yoy_base_effect"] = (frame["prior_revenue_for_yoy"].abs() < MIN_MEANINGFUL_REVENUE) | (frame["revenue_yoy_growth"].abs() > 500)
        frame["revenue_qoq_base_effect"] = (frame["prior_revenue_for_qoq"].abs() < MIN_MEANINGFUL_REVENUE) | (frame["revenue_qoq_growth"].abs() > 500)
        frame["eps_yoy_growth"] = eps_series.pct_change(4 if quarterly else 1, fill_method=None) * 100
        frame["eps_qoq_growth"] = eps_series.pct_change(1, fill_method=None) * 100
    return frame


def _period_parts(period) -> tuple[int | None, int | None, str]:
    try:
        ts = pd.Timestamp(period)
        return ts.year, ts.quarter, f"{ts.year} Q{ts.quarter}"
    except Exception:
        return None, None, "N/A"


def normalize_fiscal_period_label(fiscal_year=None, fiscal_period=None, period_end_date=None, form_type: str | None = None) -> str | None:
    year = None
    try:
        year = int(fiscal_year) if fiscal_year not in ("", None) else None
    except Exception:
        year = None
    period = str(fiscal_period or "").strip().upper()
    if period in {"1", "QTR1"}:
        period = "Q1"
    elif period in {"2", "QTR2"}:
        period = "Q2"
    elif period in {"3", "QTR3"}:
        period = "Q3"
    elif period in {"4", "QTR4"}:
        period = "Q4"
    elif period in {"YEAR", "Y"}:
        period = "FY"
    if not period and period_end_date:
        try:
            ts = pd.Timestamp(period_end_date)
            year = year or ts.year
            period = "FY" if form_type in {"10-K", "20-F"} else f"Q{ts.quarter}"
        except Exception:
            period = ""
    if year is None or not period:
        return None
    return f"{year} FY" if period == "FY" else f"{year} {period}"


def infer_quarter_from_period_end(period_end_date) -> str | None:
    try:
        ts = pd.Timestamp(period_end_date)
        return f"{ts.year} Q{ts.quarter}"
    except Exception:
        return None


def _structured_period_label(period, annual: bool = False) -> tuple[int | None, int | None, str, object | None]:
    fiscal_year, fiscal_quarter, label = _period_parts(period)
    if annual:
        label = f"{fiscal_year} FY" if fiscal_year else "Latest annual filing"
        fiscal_quarter = None
    return fiscal_year, fiscal_quarter, label, period


def _sec_period_label(sec_filing: dict, fallback_annual: bool = False) -> tuple[str | None, int | None, str | None, object | None]:
    explicit_label = sec_filing.get("filing_period_label")
    fiscal_year = None
    try:
        fiscal_year = int(sec_filing.get("fiscal_year")) if sec_filing.get("fiscal_year") not in ("", None) else None
    except Exception:
        fiscal_year = None
    fiscal_period = sec_filing.get("fiscal_period")
    period_end = sec_filing.get("period_end_date") or sec_filing.get("report_date")
    if explicit_label:
        return explicit_label, fiscal_year, fiscal_period, period_end
    if period_end:
        year, quarter, label = _period_parts(period_end)
        form_type = sec_filing.get("form_type")
        if form_type in {"10-K", "20-F"} or fallback_annual:
            label = f"{year} FY" if year else "Latest annual filing"
            fiscal_period = fiscal_period or "FY"
        elif form_type == "10-Q":
            fiscal_period = fiscal_period or (f"Q{quarter}" if quarter else None)
        else:
            return None, fiscal_year, fiscal_period, period_end
        return label if label != "N/A" else None, fiscal_year or year, fiscal_period, period_end
    return None, fiscal_year, fiscal_period, None


def _period_sort_key(label: str | None) -> tuple[int, int] | None:
    if not label:
        return None
    parts = str(label).upper().split()
    if len(parts) < 2:
        return None
    try:
        year = int(parts[0])
    except Exception:
        return None
    if parts[1] == "FY":
        quarter = 5
    else:
        quarter_text = parts[1].replace("Q", "")
        try:
            quarter = int(quarter_text)
        except Exception:
            return None
    return year, quarter


def compare_periods(period_a: str | None, period_b: str | None) -> int | None:
    key_a = _period_sort_key(period_a)
    key_b = _period_sort_key(period_b)
    if key_a is None or key_b is None:
        return None
    return (key_a > key_b) - (key_a < key_b)


def _period_alignment(sec_label: str | None, structured_label: str | None) -> tuple[str, str]:
    if sec_label and structured_label:
        if sec_label == structured_label:
            return "Aligned", "OK"
        comparison = compare_periods(sec_label, structured_label)
        if comparison is not None and comparison > 0:
            return "Filing newer than structured values", "Stale structured values"
        if comparison is not None and comparison < 0:
            return "Structured values only", "Structured values only"
        return "Filing newer than structured values", "Partial"
    if sec_label:
        return "Filing metadata only", "Filing metadata only"
    if structured_label:
        return "Structured values only", "Partial"
    return "Insufficient data", "Insufficient data"


def _canonical_period(symbol: str, release: dict) -> dict:
    return {
        "ticker": symbol,
        "reported_period_label": release.get("reported_period_label") or release.get("period_label"),
        "reported_fiscal_year": release.get("fiscal_year"),
        "reported_fiscal_period": release.get("fiscal_period"),
        "period_end_date": release.get("period_end_date"),
        "filing_date": release.get("filing_date") or release.get("filing_or_release_date"),
        "form_type": release.get("form_type"),
        "accession_number": release.get("accession_number"),
        "filing_url": release.get("filing_url"),
        "filing_source": release.get("source"),
        "structured_values_period_label": release.get("structured_values_period_label"),
        "structured_values_period_end_date": release.get("structured_values_period_end_date") or release.get("structured_values_date"),
        "structured_values_source": release.get("structured_values_source"),
        "period_alignment_status": release.get("period_alignment_status"),
        "source_status": release.get("source_status"),
        "data_quality_note": release.get("data_quality_note"),
    }


def _with_latest_period(symbol: str, release: dict) -> dict:
    release["latest_period"] = _canonical_period(symbol, release)
    return release


def _structured_sec_filing(symbol: str) -> dict:
    latest = fetch_latest_sec_filing(symbol)
    periodic = fetch_latest_periodic_sec_filing(symbol)
    if periodic.get("source_status") != "OK":
        return latest
    if latest.get("source_status") != "OK":
        return periodic
    if latest.get("filing_period_label"):
        return latest
    latest_filed = pd.to_datetime(latest.get("filing_date"), errors="coerce")
    periodic_filed = pd.to_datetime(periodic.get("filing_date"), errors="coerce")
    if pd.notna(periodic_filed) and (pd.isna(latest_filed) or periodic_filed >= latest_filed - pd.Timedelta(days=14)):
        selected = periodic.copy()
        selected["latest_event_filing"] = latest
        selected["data_quality_note"] = (
            f"Using latest period-bearing {periodic.get('form_type')} for structured financial values; "
            f"latest event filing is {latest.get('form_type')} filed {latest.get('filing_date')}."
        )
        return selected
    return latest


def _extract_sec_total_debt(company_facts: dict, form_type: str, period_end, fiscal_year, fiscal_period, accession_number: str | None) -> tuple[float | None, dict]:
    broad = extract_sec_concept_value(
        company_facts,
        SEC_TOTAL_DEBT_BROAD_CONCEPTS,
        (form_type,),
        period_end,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        accession_number=accession_number,
    )
    broad_value = to_float(broad.get("value"))
    if broad_value is not None:
        return broad_value, _metric_source_detail(
            value=broad_value,
            concept=broad.get("concept"),
            status="Direct",
            note="Broad SEC debt concept found.",
            period_end_date=broad.get("period_end_date"),
        )

    components = []
    component_concepts = []
    missing_component_groups = []
    for component_name, concepts in SEC_DEBT_COMPONENT_CONCEPTS.items():
        result = extract_sec_concept_value(
            company_facts,
            concepts,
            (form_type,),
            period_end,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            accession_number=accession_number,
        )
        value = to_float(result.get("value"))
        if value is None:
            missing_component_groups.append(component_name)
            continue
        components.append(value)
        if result.get("concept"):
            component_concepts.append(str(result.get("concept")))
    if components:
        value = sum(components)
        formula = " + ".join(component_concepts) if component_concepts else " + ".join(SEC_DEBT_COMPONENT_CONCEPTS)
        note = f"Total Debt estimated from: {formula}."
        if missing_component_groups:
            note += " Debt estimate may be incomplete because " + ", ".join(missing_component_groups) + " were not found."
        return value, _metric_source_detail(
            value=value,
            concept=None,
            status="Partial estimate",
            note=note,
            component_concepts_used=tuple(component_concepts),
            calculation_formula=formula,
            period_end_date=period_end,
        )

    return None, _metric_source_detail(
        value=None,
        concept=None,
        status="Missing",
        note=_missing_metric_note("total_debt"),
        period_end_date=period_end,
    )


def _extract_sec_structured_values(sec_filing: dict, quote: dict | None = None) -> dict:
    updated = now_et()
    form_type = sec_filing.get("form_type")
    period_end = sec_filing.get("period_end_date") or sec_filing.get("report_date")
    filing_label, fiscal_year, fiscal_period, _ = _sec_period_label(sec_filing, form_type in {"10-K", "20-F"})
    if form_type not in {"10-Q", "10-K", "20-F"} or not period_end or not sec_filing.get("cik"):
        return {
            "has_values": False,
            "source_status": "Not applicable",
            "missing_fields": list(SEC_ATTEMPTED_CONCEPTS),
            "data_quality_note": "SEC structured extraction is only attempted for 10-Q, 10-K, and 20-F filings with a period end date.",
            "last_updated": updated,
        }
    company_facts, facts_status = get_sec_company_facts(sec_filing.get("cik"))
    if facts_status.get("Status") != "OK":
        return {
            "has_values": False,
            "source_status": facts_status.get("Status", "Source error"),
            "missing_fields": list(SEC_ATTEMPTED_CONCEPTS),
            "data_quality_note": facts_status.get("Error", "SEC companyfacts unavailable."),
            "last_updated": updated,
            "sec_companyfacts_status": facts_status,
        }
    forms = (form_type,)
    values = {}
    concept_sources = {}
    metric_sources = {}
    missing = []
    for key, concepts in SEC_CONCEPTS.items():
        result = extract_sec_concept_value(
            company_facts,
            concepts,
            forms,
            period_end,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            accession_number=sec_filing.get("accession_number"),
        )
        value = to_float(result.get("value"))
        values[key] = value
        if value is None:
            if key != "cost_of_revenue":
                missing.append(key)
            metric_sources[key] = _metric_source_detail(
                value=None,
                concept=None,
                status="Missing",
                note=_missing_metric_note(key),
                fallback_source="Yahoo Finance/yfinance quarterly statements",
                period=filing_label,
                period_end_date=period_end,
            )
        else:
            concept_sources[key] = result
            metric_sources[key] = _metric_source_detail(
                value=value,
                concept=result.get("concept"),
                status="SEC concept found",
                note=result.get("source_note") or "SEC concept found for matching period.",
                period=filing_label,
                period_end_date=result.get("period_end_date") or period_end,
            )
        _set_attempted_concepts(metric_sources, key)

    debt_value, debt_detail = _extract_sec_total_debt(company_facts, form_type, period_end, fiscal_year, fiscal_period, sec_filing.get("accession_number"))
    quote_debt = to_float((quote or {}).get("total_debt"))
    if debt_value is None and quote_debt is not None:
        debt_value = quote_debt
        debt_detail = _metric_source_detail(
            value=debt_value,
            source="Yahoo Finance quote metadata",
            concept=None,
            status="yfinance fallback",
            note="Total Debt sourced from Yahoo Finance quote metadata because SEC debt concepts were unavailable for the filing period.",
            fallback_used=True,
            fallback_source="Yahoo Finance quote metadata",
            period=filing_label,
            period_end_date=period_end,
        )
    values["total_debt"] = debt_value
    metric_sources["total_debt"] = debt_detail
    metric_sources["total_debt"]["period"] = filing_label
    metric_sources["total_debt"]["period_end_date"] = metric_sources["total_debt"].get("period_end_date") or period_end
    _set_attempted_concepts(metric_sources, "total_debt")
    if debt_value is None:
        if "total_debt" not in missing:
            missing.append("total_debt")
    else:
        concept_sources["total_debt"] = {
            "value": debt_value,
            "concept": debt_detail.get("concept_used"),
            "source_note": debt_detail.get("note"),
            "period_end_date": debt_detail.get("period_end_date") or period_end,
        }

    if values.get("gross_profit") is None and values.get("revenue") is not None and values.get("cost_of_revenue") is not None:
        values["gross_profit"] = values["revenue"] - abs(values["cost_of_revenue"])
        if "gross_profit" in missing:
            missing.remove("gross_profit")
        cost_detail = metric_sources.get("cost_of_revenue") or {}
        metric_sources["gross_profit"] = _metric_source_detail(
            value=values["gross_profit"],
            concept=cost_detail.get("concept_used"),
            status="Calculated",
            note="Gross Profit calculated as Revenue less Cost of Revenue because a direct gross profit concept was unavailable.",
            calculation_formula="Revenue - Cost of Revenue",
            source_inputs="Revenue, Cost of Revenue",
            period=filing_label,
            period_end_date=period_end,
        )
        metric_sources["gross_profit"]["concepts_attempted"] = SEC_ATTEMPTED_CONCEPTS.get("gross_profit", ())

    if values.get("free_cash_flow") is None and values.get("operating_cash_flow") is not None and values.get("capital_expenditures") is not None:
        values["free_cash_flow"] = values["operating_cash_flow"] - abs(values["capital_expenditures"])
        metric_sources["free_cash_flow"] = _metric_source_detail(
            value=values["free_cash_flow"],
            concept=None,
            status="Calculated",
            note="Free Cash Flow calculated as Operating Cash Flow less Capex. Capex normalized as cash outflow.",
            calculation_formula="Operating Cash Flow - Capex Outflow",
            source_inputs="Operating Cash Flow, Capex",
            period=filing_label,
            period_end_date=period_end,
        )
        _set_attempted_concepts(metric_sources, "free_cash_flow")
    has_values = any(values.get(key) is not None for key in ("revenue", "net_income", "eps", "cash", "operating_cash_flow"))
    if "free_cash_flow" not in missing and values.get("free_cash_flow") is None:
        missing.append("free_cash_flow")
        metric_sources["free_cash_flow"] = _metric_source_detail(
            value=None,
            concept=None,
            status="Missing",
            note=_missing_metric_note("free_cash_flow"),
            calculation_formula="Operating Cash Flow - Capex Outflow",
            period=filing_label,
            period_end_date=period_end,
        )
        _set_attempted_concepts(metric_sources, "free_cash_flow")
    if quote and values.get("shares_outstanding") is None:
        values["shares_outstanding"] = quote.get("shares_outstanding")
        if values.get("shares_outstanding") is not None:
            metric_sources["shares_outstanding"] = _metric_source_detail(
                value=values.get("shares_outstanding"),
                source="Quote metadata / latest provider",
                status="yfinance fallback",
                note="Shares outstanding sourced from quote metadata because SEC weighted shares were unavailable.",
                fallback_used=True,
                period="Latest quote",
            )
            _set_attempted_concepts(metric_sources, "shares_outstanding")
    _derive_capex_from_fcf(
        values,
        metric_sources,
        missing,
        period_label=filing_label,
        period_end_date=period_end,
        source="SEC XBRL/companyfacts",
    )
    _derive_eps_from_net_income_and_shares(
        values,
        metric_sources,
        missing,
        period_label=filing_label,
        period_end_date=period_end,
        source="SEC XBRL/companyfacts",
    )
    status = "OK" if has_values and not [key for key in ("revenue", "net_income", "cash") if values.get(key) is None] else "Partial" if has_values else "Missing"
    note = "SEC XBRL/companyfacts values matched to latest filing period." if has_values else "SEC companyfacts returned no matching values for the latest filing period."
    return {
        **values,
        "has_values": has_values,
        "reported_period_label": filing_label,
        "structured_values_period_label": filing_label if has_values else None,
        "structured_values_source": "SEC XBRL/companyfacts",
        "period_end_date": period_end,
        "structured_values_date": period_end if has_values else None,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "source_status": status,
        "missing_fields": missing,
        "concept_sources": concept_sources,
        "metric_sources": metric_sources,
        "data_quality_note": note,
        "sec_companyfacts_status": facts_status,
        "sec_value_extraction_status": status,
        "last_updated": updated,
    }


def _sec_row(sec_values: dict, sec_filing: dict) -> dict | None:
    if not sec_values.get("has_values") or not sec_values.get("period_end_date"):
        return None
    period_date = pd.Timestamp(sec_values["period_end_date"])
    row = {
        "period_date": period_date,
        "period": sec_values.get("reported_period_label") or f"{period_date.year} Q{period_date.quarter}",
        "structured_values_source": sec_values.get("structured_values_source"),
        "sec_missing_fields": sec_values.get("missing_fields", []),
        "sec_companyfacts_status": sec_values.get("sec_companyfacts_status"),
        "sec_value_extraction_status": sec_values.get("sec_value_extraction_status"),
        "sec_data_quality_note": sec_values.get("data_quality_note"),
        "metric_sources": sec_values.get("metric_sources", {}),
        "concept_sources": sec_values.get("concept_sources", {}),
    }
    for key in FIELD_MAP:
        row[key] = sec_values.get(key)
    row["shares_outstanding"] = sec_values.get("shares_outstanding")
    row["source_form_type"] = sec_filing.get("form_type")
    row["source_accession_number"] = sec_filing.get("accession_number")
    return row


def _merge_sec_quarterly_history(history: pd.DataFrame, sec_values: dict, sec_filing: dict) -> pd.DataFrame:
    row = _sec_row(sec_values, sec_filing)
    if row is None:
        return history
    frame = history.copy() if isinstance(history, pd.DataFrame) and not history.empty else pd.DataFrame()
    if not frame.empty and "period_date" in frame:
        try:
            target = pd.Timestamp(row["period_date"]).date()
            aligned = frame[pd.to_datetime(frame["period_date"], errors="coerce").dt.date == target]
        except Exception:
            aligned = pd.DataFrame()
        if not aligned.empty:
            fallback_row = aligned.iloc[-1].to_dict()
            metric_sources = dict(row.get("metric_sources") or {})
            missing_fields = list(row.get("sec_missing_fields") or [])
            for key in RECONCILIATION_METRICS:
                if key == "shares_outstanding":
                    continue
                if _value_present(row.get(key)):
                    continue
                fallback_value = fallback_row.get(key)
                if not _value_present(fallback_value):
                    continue
                row[key] = fallback_value
                if key in missing_fields:
                    missing_fields.remove(key)
                metric_sources[key] = _metric_source_detail(
                    value=fallback_value,
                    source="Yahoo Finance/yfinance quarterly statements",
                    concept=None,
                    status="yfinance fallback",
                    note=f"{_metric_label(key)} unavailable from SEC concepts; yfinance same-period value used.",
                    fallback_used=True,
                    fallback_attempted=True,
                    fallback_source="Yahoo Finance/yfinance quarterly statements",
                    period=row.get("period"),
                    period_end_date=row.get("period_date"),
                )
            for key in missing_fields:
                detail = metric_sources.get(key) or _metric_source_detail(value=None)
                detail["fallback_attempted"] = True
                detail["fallback_source"] = "Yahoo Finance/yfinance quarterly statements"
                detail["status"] = "Missing"
                detail["note"] = _missing_metric_note(key, fallback_attempted=True)
                metric_sources[key] = detail
                _set_attempted_concepts(metric_sources, key)
            row["metric_sources"] = metric_sources
            row["sec_missing_fields"] = missing_fields
            if missing_fields:
                row["sec_data_quality_note"] = _latest_source_reason({"metric_sources": metric_sources, "data_quality_note": row.get("sec_data_quality_note")}, row, missing_fields)
            else:
                row["sec_data_quality_note"] = "SEC XBRL/companyfacts plus same-period yfinance fallback supplied the latest structured values."
    row_frame = pd.DataFrame([row]).dropna(axis=1, how="all")
    frame = row_frame if frame.empty else pd.concat([frame, row_frame], ignore_index=True, sort=False)
    frame["period_date"] = pd.to_datetime(frame["period_date"], errors="coerce")
    frame = frame.dropna(subset=["period_date"]).sort_values("period_date")
    source_series = frame["structured_values_source"] if "structured_values_source" in frame else pd.Series([""] * len(frame), index=frame.index)
    frame["_sec_priority"] = source_series.eq("SEC XBRL/companyfacts").astype(int)
    frame = frame.sort_values(["period_date", "_sec_priority"]).drop_duplicates("period_date", keep="last").drop(columns=["_sec_priority"])
    return _augment_history(frame, True)


def _chart_source_status(history: pd.DataFrame, latest_release: dict) -> dict:
    if history is None or history.empty:
        return {"label": "No quarterly chart data", "status": "Insufficient data", "note": "Quarterly financial chart data unavailable."}
    sources = set()
    if "structured_values_source" in history:
        for value in history["structured_values_source"].dropna().astype(str):
            if value:
                sources.add(value)
    if sources and sources == {"SEC XBRL/companyfacts"}:
        label = "SEC XBRL/companyfacts"
    elif "SEC XBRL/companyfacts" in sources:
        label = "Mixed SEC + Yahoo Finance"
    else:
        label = "Yahoo Finance quarterly statements"
    alignment = latest_release.get("period_alignment_status")
    status = "Partial" if alignment in {"Filing newer than structured values", "Filing metadata only"} else "OK"
    note = latest_release.get("data_quality_note") or label
    if alignment == "Aligned":
        status = latest_release.get("source_status", "OK")
    return {"label": label, "status": status, "note": note}


def _financial_reconciliation(symbol: str, latest_release: dict, latest_row: dict, history: pd.DataFrame, chart_source: dict) -> dict:
    chart_latest_period = None
    chart_latest_period_end = None
    chart_latest_source = chart_source.get("label") if chart_source else None
    missing_chart_fields = []
    if isinstance(history, pd.DataFrame) and not history.empty:
        chart_row = history.iloc[-1].to_dict()
        chart_latest_period = chart_row.get("period")
        chart_latest_period_end = _date_label(chart_row.get("period_date"))
        chart_latest_source = chart_row.get("structured_values_source") or chart_latest_source
        for key, label in CHART_REQUIRED_METRICS.items():
            missing_periods = []
            if key in history:
                missing_periods = [
                    str(row.get("period") or _date_label(row.get("period_date")) or "Unknown period")
                    for _, row in history[history[key].isna()].iterrows()
                ]
            elif len(history):
                missing_periods = [str(row.get("period") or _date_label(row.get("period_date")) or "Unknown period") for _, row in history.iterrows()]
            if missing_periods:
                missing_chart_fields.append(f"{label}: {_label_list(missing_periods, 4)}")
    values_period = latest_release.get("structured_values_period_label")
    values_period_end = _date_label(latest_release.get("structured_values_period_end_date") or latest_release.get("structured_values_date") or latest_release.get("period_end_date"))
    reported_period = latest_release.get("reported_period_label") or latest_release.get("period_label")
    filing_period = latest_release.get("filing_period_label") or reported_period
    source = latest_release.get("structured_values_source") or latest_release.get("source")
    form = latest_release.get("form_type")
    filed_date = _date_label(latest_release.get("filing_date") or latest_release.get("filing_or_release_date"))
    accession = latest_release.get("accession_number")
    metric_sources = latest_release.get("metric_sources") or {}
    release_not_applicable = latest_release.get("source_status") == "Not applicable"
    rows = []
    for key, label in RECONCILIATION_METRICS.items():
        raw_value = latest_release.get(key)
        detail = metric_sources.get(key) or {}
        metric_source = source
        metric_period = values_period
        metric_period_end = values_period_end
        note = latest_release.get("source_status_reason") or latest_release.get("data_quality_note", "")
        concept_used = detail.get("concept_used")
        concepts_attempted = detail.get("concepts_attempted") or SEC_ATTEMPTED_CONCEPTS.get(key, ())
        component_concepts_used = detail.get("component_concepts_used") or ()
        calculation_formula = detail.get("calculation_formula")
        fallback_used = bool(detail.get("fallback_used"))
        fallback_attempted = bool(detail.get("fallback_attempted") or fallback_used)
        status = detail.get("status")
        if key == "shares_outstanding":
            raw_value = latest_release.get(key) if _value_present(latest_release.get(key)) else latest_row.get(key)
            if release_not_applicable:
                raw_value = None
                metric_source = "N/A"
                metric_period = "Not applicable"
                metric_period_end = None
                status = "Not applicable"
                note = "Corporate financial statement share metrics are not applicable for this ticker type."
            else:
                metric_source = detail.get("source") or "Quote metadata / latest provider"
                metric_period = "Latest quote"
                metric_period_end = None
                status = status or ("OK" if _value_present(raw_value) else "N/A")
                note = detail.get("note") or note
        elif release_not_applicable:
            metric_period = "Not applicable"
            metric_period_end = "N/A"
            metric_source = "N/A"
            note = "Corporate financial statements are not applicable for this ticker type."
            status = "Not applicable"
        elif not _value_present(raw_value):
            metric_period = values_period or latest_row.get("period")
            metric_period_end = values_period_end or _date_label(latest_row.get("period_date"))
            metric_source = detail.get("source") or metric_source
            note = detail.get("note") or f"{label} unavailable from {metric_source or 'structured source'}."
            status = status or ("Missing concept" if (metric_source or "").startswith("SEC") else "N/A")
        else:
            metric_source = detail.get("source") or metric_source
            metric_period = detail.get("period") or metric_period
            metric_period_end = _date_label(detail.get("period_end_date")) or metric_period_end
            note = detail.get("note") or note
            status = status or "OK"
        rows.append(
            {
                "metric": key,
                "Metric": label,
                "value": raw_value,
                "Value": raw_value,
                "Displayed Value": raw_value,
                "Period": metric_period or "N/A",
                "Period End Date": metric_period_end or "N/A",
                "Source": metric_source or "N/A",
                "Provider": _provider_from_source(metric_source, _display_metric_status(status, raw_value)),
                "Form": form or "N/A",
                "Filed Date": filed_date or "N/A",
                "Accession": accession or "N/A",
                "SEC Concept Used": concept_used or "N/A",
                "Component Concepts Used": " + ".join(component_concepts_used) if component_concepts_used else "N/A",
                "Calculation Formula": calculation_formula or "N/A",
                "Source Inputs": detail.get("source_inputs") or "N/A",
                "Concepts Attempted": ", ".join(concepts_attempted) if concepts_attempted else "N/A",
                "Fallback Used": "Yes" if fallback_used else "Attempted" if fallback_attempted else "No",
                "Fallback Source": detail.get("fallback_source") or "N/A",
                "Status": _display_metric_status(status, raw_value),
                "Missing / Note": note,
                "Note": note,
            }
        )

    checks = []

    def add_check(name: str, passed: bool | None, note: str) -> None:
        checks.append({"Check": name, "Status": "OK" if passed else "Warning" if passed is False else "N/A", "Note": note})

    cards_period = values_period or reported_period
    add_check(
        "Latest cards period equals chart latest period",
        None if not cards_period or not chart_latest_period else cards_period == chart_latest_period,
        f"Cards: {cards_period or 'N/A'} | Chart: {chart_latest_period or 'N/A'}",
    )
    revenue_period = next((row["Period"] for row in rows if row["metric"] == "revenue" and _value_present(row.get("value"))), None)
    eps_period = next((row["Period"] for row in rows if row["metric"] == "eps" and _value_present(row.get("value"))), None)
    add_check(
        "Revenue period equals EPS period",
        None if not revenue_period or not eps_period else revenue_period == eps_period,
        f"Revenue: {revenue_period or 'N/A'} | EPS: {eps_period or 'N/A'}",
    )
    income_periods = {row["Period"] for row in rows if row["metric"] in INCOME_STATEMENT_METRICS and _value_present(row.get("value"))}
    balance_periods = {row["Period"] for row in rows if row["metric"] in BALANCE_SHEET_METRICS and _value_present(row.get("value")) and row["metric"] != "shares_outstanding"}
    if income_periods and balance_periods:
        add_check(
            "Income statement period equals balance sheet period",
            len(income_periods | balance_periods) == 1,
            f"Income: {_label_list(sorted(income_periods))} | Balance sheet: {_label_list(sorted(balance_periods))}",
        )
    else:
        add_check("Income statement period equals balance sheet period", None, "Insufficient income statement or balance sheet fields.")
    comparison = compare_periods(filing_period, values_period)
    add_check(
        "Filing period is not older than structured values period",
        None if comparison is None else comparison >= 0,
        f"Filing/reported: {filing_period or 'N/A'} | Structured: {values_period or 'N/A'}",
    )
    period_end = _date_label(latest_release.get("period_end_date"))
    add_check(
        "Period end date is not filing date",
        None if not period_end or not filed_date else period_end != filed_date,
        f"Period end: {period_end or 'N/A'} | Filed: {filed_date or 'N/A'}",
    )
    margin_notes = []
    revenue = to_float(latest_row.get("revenue"))
    for metric, label in (("gross_profit", "Gross margin"), ("operating_income", "Operating margin"), ("net_income", "Net margin"), ("free_cash_flow", "FCF margin")):
        numerator = to_float(latest_row.get(metric))
        if revenue is None or abs(revenue) < MIN_MEANINGFUL_REVENUE:
            margin_notes.append(f"{label}: N/A because revenue denominator is missing or too small.")
        elif numerator is None:
            margin_notes.append(f"{label}: N/A because numerator is missing.")
        else:
            margin = numerator / revenue * 100
            if abs(margin) > 300:
                margin_notes.append(f"{label}: NM because calculated margin is {margin:.1f}%.")
    add_check(
        "Margin calculations use same-period values",
        True,
        "Margins are calculated from the latest normalized row; extreme or unsupported margins are suppressed as NM/N/A.",
    )
    check_warnings = [check["Note"] for check in checks if check["Status"] == "Warning"]
    warnings = list(check_warnings)
    if missing_chart_fields:
        warnings.append("Missing chart fields: " + "; ".join(missing_chart_fields))
    quality = _financial_quality_categories(
        metric_sources,
        latest_release,
        latest_release.get("missing_fields") or [],
        not_applicable=CORE_FINANCIAL_FIELDS if release_not_applicable else [],
        ticker_type="etf_fund" if release_not_applicable else None,
    )
    return {
        "ticker": symbol,
        "rows": rows,
        "checks": checks,
        "has_mismatch": bool(check_warnings),
        "warnings": warnings,
        "data_quality": quality,
        "data_completeness_score": quality.get("completeness_score"),
        "compact_source_status_note": _compact_source_status_note(quality),
        "missing_chart_fields": missing_chart_fields,
        "missing_metric_periods": [row["Metric"] for row in rows if not _value_present(row.get("value"))],
        "margin_notes": margin_notes,
        "chart_latest_period": chart_latest_period,
        "chart_latest_period_end": chart_latest_period_end,
        "chart_latest_source": chart_latest_source,
    }


def _provider_from_source(source: str | None, status: str | None = None) -> str:
    source_text = str(source or "")
    status_text = str(status or "")
    if status_text == "Calculated":
        return "Calculated"
    if "SEC" in source_text:
        return "SEC XBRL/companyfacts"
    if "Yahoo" in source_text or "yfinance" in source_text or "Quote" in source_text:
        return "Yahoo Finance/yfinance"
    if source_text in {"", "N/A"}:
        return "N/A"
    return source_text


def _packet_field_from_row(row: dict, latest_release: dict) -> dict:
    status = row.get("Status") or "Missing"
    return {
        "value": row.get("value"),
        "source": row.get("Source"),
        "provider": _provider_from_source(row.get("Source"), status),
        "period_label": row.get("Period"),
        "period_end_date": row.get("Period End Date"),
        "filing_date": row.get("Filed Date"),
        "form_type": row.get("Form"),
        "accession_number": row.get("Accession"),
        "concept_used": row.get("SEC Concept Used"),
        "concepts_attempted": row.get("Concepts Attempted"),
        "component_concepts_used": row.get("Component Concepts Used"),
        "fallback_used": row.get("Fallback Used") in {"Yes", "Attempted"},
        "fallback_source": row.get("Fallback Source"),
        "calculation_formula": row.get("Calculation Formula"),
        "status": status,
        "confidence": 1.0 if status == "Direct" else 0.9 if status in {"Fallback", "Calculated"} else 0.5 if status in {"Estimated", "Partial estimate"} else 0.0,
        "note": row.get("Note") or row.get("Missing / Note"),
    }


def _packet_calculated_field(value, formula: str, note: str, period_label: str | None, period_end_date) -> dict:
    present = _value_present(value)
    return {
        "value": value if present else None,
        "source": "Calculated",
        "provider": "Calculated",
        "period_label": period_label or "N/A",
        "period_end_date": _date_label(period_end_date) or period_end_date or "N/A",
        "filing_date": "N/A",
        "form_type": "N/A",
        "accession_number": "N/A",
        "concept_used": "N/A",
        "concepts_attempted": "N/A",
        "component_concepts_used": "N/A",
        "fallback_used": False,
        "fallback_source": "N/A",
        "calculation_formula": formula,
        "status": "Calculated" if present else "Missing",
        "confidence": 0.9 if present else 0.0,
        "note": note if present else f"{note} Inputs unavailable or not period-aligned.",
    }


def _build_financial_data_packet(symbol: str, quote: dict, latest_release: dict, reconciliation: dict) -> dict:
    ticker_type = _ticker_type(symbol, quote)
    rows = reconciliation.get("rows") or []
    fields = {row.get("metric"): _packet_field_from_row(row, latest_release) for row in rows if row.get("metric")}
    if ticker_type in {"etf_fund", "crypto_proxy"}:
        for key in CORE_FINANCIAL_FIELDS + DERIVED_FINANCIAL_FIELDS:
            fields[key] = {
                "value": None,
                "source": "N/A",
                "provider": "N/A",
                "period_label": "Not applicable",
                "period_end_date": "N/A",
                "filing_date": "N/A",
                "form_type": "N/A",
                "accession_number": "N/A",
                "concept_used": "N/A",
                "concepts_attempted": "N/A",
                "component_concepts_used": "N/A",
                "fallback_used": False,
                "fallback_source": "N/A",
                "calculation_formula": "N/A",
                "status": "Not applicable",
                "confidence": 0.0,
                "note": "Corporate financial statements are not applicable for ETFs, funds, indexes, or crypto tickers.",
            }
    quality = reconciliation.get("data_quality") or latest_release.get("financial_data_quality") or _financial_quality_categories(
        {},
        {key: latest_release.get(key) for key in CORE_FINANCIAL_FIELDS},
        latest_release.get("missing_fields") or [],
        not_applicable=CORE_FINANCIAL_FIELDS if ticker_type in {"etf_fund", "crypto_proxy"} else [],
        ticker_type=ticker_type,
    )
    warnings = list(reconciliation.get("warnings") or [])
    if ticker_type in {"etf_fund", "crypto_proxy"}:
        warnings = ["Corporate financial statements are not applicable for this ticker type."]
    else:
        period_label = latest_release.get("structured_values_period_label") or latest_release.get("reported_period_label")
        period_end = latest_release.get("structured_values_period_end_date") or latest_release.get("period_end_date")
        revenue = to_float(latest_release.get("revenue"))
        gross_profit = to_float(latest_release.get("gross_profit"))
        operating_income = to_float(latest_release.get("operating_income"))
        net_income = to_float(latest_release.get("net_income"))
        fcf = to_float(latest_release.get("free_cash_flow"))
        cash = to_float(latest_release.get("cash"))
        debt = to_float(latest_release.get("total_debt"))
        fields["gross_margin"] = _packet_calculated_field(_safe_margin(gross_profit, revenue), "Gross Profit / Revenue", "Gross margin calculated from same-period gross profit and revenue.", period_label, period_end)
        fields["operating_margin"] = _packet_calculated_field(_safe_margin(operating_income, revenue), "Operating Income / Revenue", "Operating margin calculated from same-period operating income and revenue.", period_label, period_end)
        fields["net_margin"] = _packet_calculated_field(_safe_margin(net_income, revenue), "Net Income / Revenue", "Net margin calculated from same-period net income and revenue.", period_label, period_end)
        fields["fcf_margin"] = _packet_calculated_field(_safe_margin(fcf, revenue), "Free Cash Flow / Revenue", "FCF margin calculated from same-period free cash flow and revenue.", period_label, period_end)
        fields["net_cash_or_debt"] = _packet_calculated_field(cash - debt if cash is not None and debt is not None else None, "Cash - Total Debt", "Net cash/debt calculated from same-period cash and debt.", period_label, period_end)
        fields["cash_runway"] = _packet_calculated_field(_cash_runway({"cash": cash, "free_cash_flow": fcf}), "Cash / abs(Free Cash Flow)", "Cash runway calculated from latest cash and quarterly FCF burn.", period_label, period_end)
        fields["revenue_yoy_growth"] = _packet_calculated_field(latest_release.get("revenue_yoy_growth"), "Revenue YoY Growth", "Revenue YoY growth, when available from normalized history.", period_label, period_end)
    source_status = quality.get("source_status") or _completeness_status(quality.get("completeness_score"), ticker_type)
    return {
        "ticker": symbol,
        "ticker_type": ticker_type,
        "reported_period_label": latest_release.get("reported_period_label") or latest_release.get("period_label") or "N/A",
        "reported_period_end_date": latest_release.get("period_end_date"),
        "period_end_date": latest_release.get("period_end_date"),
        "filing_date": latest_release.get("filing_date") or latest_release.get("filing_or_release_date"),
        "form_type": latest_release.get("form_type"),
        "accession_number": latest_release.get("accession_number"),
        "filing_url": latest_release.get("filing_url"),
        "source_used": latest_release.get("structured_values_source") or latest_release.get("source") or "N/A",
        "source_status": source_status,
        "completeness_score": quality.get("completeness_score"),
        "fields": fields,
        "found_direct": quality.get("found_direct", []),
        "fallback_used": quality.get("fallback", []),
        "calculated": quality.get("calculated", []),
        "estimated": quality.get("estimated", []),
        "missing": quality.get("missing", []),
        "not_applicable": quality.get("not_applicable", []),
        "warnings": warnings,
        "period_alignment_status": latest_release.get("period_alignment_status"),
        "structured_values_period_label": latest_release.get("structured_values_period_label"),
        "structured_values_period_end_date": latest_release.get("structured_values_period_end_date") or latest_release.get("structured_values_date"),
        "data_quality_note": _compact_source_status_note(quality),
        "coverage_summary": quality,
        "reconciliation": reconciliation,
    }


def _release_from_history(symbol: str, history: pd.DataFrame, quote: dict, sec_filing: dict, annual: bool = False) -> dict:
    updated = now_et()
    ticker_type = _ticker_type(symbol, quote)
    if ticker_type in {"etf_fund", "crypto_proxy"}:
        release = {
            "ticker": symbol,
            "period_label": "Not applicable",
            "reported_period_label": "Not applicable",
            "filing_period_label": None,
            "structured_values_period_label": None,
            "structured_values_date": None,
            "structured_values_period_end_date": None,
            "period_alignment_status": "Not applicable",
            "source": "Quote metadata",
            "structured_values_source": None,
            "source_status": "Not applicable",
            "filing_or_release_date": None,
            "filing_date": None,
            "form_type": quote.get("quote_type") or "Fund",
            "filing_url": None,
            "accession_number": None,
            "period_end_date": None,
            "missing_fields": [],
            "metric_sources": {},
            "data_quality_note": "Corporate financial statements are not applicable for ETFs, funds, indexes, or crypto tickers.",
            "source_status_reason": "Corporate financial statements are not applicable for this ticker type.",
            "last_updated": updated,
        }
        return _with_latest_period(symbol, _apply_quality_metadata(release, ticker_type=ticker_type))
    filing_label, sec_fiscal_year, sec_fiscal_period, period_end = _sec_period_label(sec_filing, annual)
    if history is None or history.empty:
        quote_type = str(quote.get("quote_type") or "").upper()
        status = "Not applicable" if quote_type in {"ETF", "MUTUALFUND", "CRYPTOCURRENCY", "INDEX"} else "Insufficient data"
        if filing_label and status != "Not applicable":
            status = "Filing metadata only"
        note = "Latest filing metadata may be available, but structured quarterly values were not returned."
        if filing_label:
            note = f"Latest filing detected for {filing_label}; structured financial values were not returned."
        release_period_end = period_end if filing_label else None
        release = {
            "ticker": symbol,
            "period_label": filing_label or "N/A",
            "reported_period_label": filing_label or "N/A",
            "filing_period_label": filing_label,
            "structured_values_period_label": None,
            "structured_values_date": None,
            "structured_values_period_end_date": None,
            "structured_values_source": None,
            "period_alignment_status": "Filing metadata only" if filing_label else "Insufficient data",
            "source": sec_filing.get("source", "Yahoo Finance/yfinance quarterly statements"),
            "source_status": status,
            "filing_or_release_date": sec_filing.get("filing_date"),
            "filing_date": sec_filing.get("filing_date"),
            "form_type": sec_filing.get("form_type"),
            "filing_url": sec_filing.get("filing_url"),
            "accession_number": sec_filing.get("accession_number"),
            "fiscal_year": sec_fiscal_year,
            "fiscal_period": sec_fiscal_period,
            "period_end_date": release_period_end,
            "missing_fields": ["quarterly financial statements"],
            "data_quality_note": note,
            "source_status_reason": note,
            "last_updated": updated,
        }
        release = _apply_quality_metadata(release, ticker_type=_ticker_type(symbol, quote))
        release["source_status_reason"] = release.get("source_status_reason") or release.get("data_quality_note")
        return _with_latest_period(symbol, release)
    row = history.iloc[-1].to_dict()
    fiscal_year, fiscal_quarter, structured_label, structured_date = _structured_period_label(row.get("period_date"), annual)
    structured_source = row.get("structured_values_source") or ("Yahoo Finance annual statements" if annual else "Yahoo Finance quarterly statements")
    sec_structured = structured_source == "SEC XBRL/companyfacts"
    if sec_structured:
        filing_label = filing_label or structured_label
    alignment_status, alignment_source_status = ("Aligned", "OK") if sec_structured and filing_label == structured_label else _period_alignment(filing_label, structured_label)
    reported_label = structured_label if alignment_status == "Structured values only" and structured_label else filing_label or structured_label
    values = {
        "revenue": to_float(row.get("revenue")),
        "gross_profit": to_float(row.get("gross_profit")),
        "operating_income": to_float(row.get("operating_income")),
        "net_income": to_float(row.get("net_income")),
        "eps": to_float(row.get("eps")),
        "operating_cash_flow": to_float(row.get("operating_cash_flow")),
        "capital_expenditures": to_float(row.get("capital_expenditures")),
        "free_cash_flow": to_float(row.get("free_cash_flow")),
        "cash": to_float(row.get("cash")),
        "total_debt": to_float(row.get("total_debt")),
        "total_assets": to_float(row.get("total_assets")),
        "shareholders_equity": to_float(row.get("shareholders_equity")),
        "shares_outstanding": to_float(quote.get("shares_outstanding")),
    }
    if values.get("total_debt") is None and to_float(quote.get("total_debt")) is not None:
        values["total_debt"] = to_float(quote.get("total_debt"))
    missing = row.get("sec_missing_fields") if sec_structured and isinstance(row.get("sec_missing_fields"), list) else [key for key, value in values.items() if value is None and key not in {"eps", "shares_outstanding"}]
    metric_sources = dict(row.get("metric_sources") or {})
    if values.get("total_debt") is not None and to_float(row.get("total_debt")) is None:
        metric_sources["total_debt"] = _metric_source_detail(
            value=values.get("total_debt"),
            source="Yahoo Finance quote metadata",
            status="yfinance fallback",
            note="Total Debt sourced from Yahoo Finance quote metadata because statement debt line was unavailable.",
            fallback_used=True,
            fallback_source="Yahoo Finance quote metadata",
            period=structured_label,
            period_end_date=structured_date,
        )
        _set_attempted_concepts(metric_sources, "total_debt")
    if sec_structured:
        for key in RECONCILIATION_METRICS:
            if key in metric_sources:
                continue
            if _value_present(values.get(key)):
                metric_sources[key] = _metric_source_detail(
                    value=values.get(key),
                    source=structured_source,
                    status="OK",
                    note=f"{_metric_label(key)} available from latest structured row.",
                    period=structured_label,
                    period_end_date=structured_date,
                )
            elif key in missing:
                metric_sources[key] = _metric_source_detail(
                    value=None,
                    source=structured_source,
                    status="N/A",
                    note=f"{_metric_label(key)} unavailable from latest structured row.",
                    period=structured_label,
                    period_end_date=structured_date,
                )
            _set_attempted_concepts(metric_sources, key)
    else:
        for key in RECONCILIATION_METRICS:
            if key == "shares_outstanding":
                continue
            metric_sources[key] = _metric_source_detail(
                value=values.get(key),
                source=structured_source,
                status="yfinance fallback" if _value_present(values.get(key)) else "N/A",
                note="Yahoo Finance quarterly statement value." if _value_present(values.get(key)) else "Unavailable from Yahoo Finance quarterly statements.",
                fallback_used=True,
                period=structured_label,
                period_end_date=structured_date,
            )
    _derive_capex_from_fcf(
        values,
        metric_sources,
        missing,
        period_label=structured_label,
        period_end_date=structured_date,
        source=structured_source,
    )
    _derive_eps_from_net_income_and_shares(
        values,
        metric_sources,
        missing,
        period_label=structured_label,
        period_end_date=structured_date,
        source=structured_source,
    )
    source_status = alignment_source_status if alignment_source_status != "OK" else ("OK" if not missing else "Partial")
    if source_status == "OK" and any((detail or {}).get("status") == "Partial estimate" for detail in metric_sources.values()):
        source_status = "Partial"
    note = row.get("sec_data_quality_note") if sec_structured else "Latest quarterly statements from Yahoo Finance/yfinance."
    if annual:
        source_status = "Partial"
        note = "Quarterly statements unavailable; showing latest annual filing data instead."
    if alignment_status == "Filing newer than structured values":
        source_status = "Stale structured values" if alignment_source_status == "Stale structured values" else "Partial"
        note = f"Latest filing detected for {reported_label}; structured financial values may still reflect {structured_label}."
    elif alignment_status == "Filing metadata only":
        source_status = "Filing metadata only"
        note = f"Latest filing detected for {reported_label}; structured financial values were not returned."
    elif alignment_status == "Structured values only":
        note = "Structured financial values are available, but SEC filing period metadata was not returned."
    filing_date = sec_filing.get("filing_date")
    period_date = row.get("period_date")
    release_period_end = period_end if filing_label else structured_date
    if alignment_status == "Structured values only":
        release_period_end = structured_date
    try:
        if alignment_status == "Aligned" and filing_date and period_date and pd.Timestamp(filing_date) > pd.Timestamp(period_date) + pd.Timedelta(days=120):
            note = "Latest filing detected; structured financial values may lag the filing metadata."
            if source_status == "OK":
                source_status = "Partial"
    except Exception:
        pass
    release = {
        "ticker": symbol,
        "period_label": reported_label,
        "reported_period_label": reported_label,
        "filing_period_label": filing_label,
        "structured_values_period_label": structured_label,
        "structured_values_date": structured_date,
        "structured_values_period_end_date": structured_date,
        "period_alignment_status": alignment_status,
        "fiscal_year": sec_fiscal_year or fiscal_year,
        "fiscal_quarter": fiscal_quarter if not annual else None,
        "fiscal_period": sec_fiscal_period or ("FY" if annual else (f"Q{fiscal_quarter}" if fiscal_quarter else None)),
        "period_end_date": release_period_end,
        "filing_or_release_date": filing_date or row.get("period_date"),
        "filing_date": filing_date,
        "form_type": sec_filing.get("form_type") or ("Annual" if annual else "Quarterly"),
        "source": (f"SEC XBRL/companyfacts, latest {sec_filing.get('form_type')}" if sec_structured else "Yahoo Finance quarterly statements + " + sec_filing.get("source", "SEC metadata")),
        "structured_values_source": structured_source,
        "sec_companyfacts_status": row.get("sec_companyfacts_status"),
        "sec_value_extraction_status": row.get("sec_value_extraction_status"),
        "source_status": source_status,
        **values,
        "filing_url": sec_filing.get("filing_url"),
        "accession_number": sec_filing.get("accession_number"),
        "missing_fields": missing,
        "metric_sources": metric_sources,
        "concept_sources": row.get("concept_sources") or {},
        "data_quality_note": note,
        "last_updated": updated,
    }
    release = _apply_quality_metadata(release, values, missing, ticker_type=_ticker_type(symbol, quote))
    release["source_status_reason"] = _latest_source_reason(release, values, missing) if source_status == "Partial" else _source_status_reason(source_status, values, missing, structured_source, note)
    return _with_latest_period(symbol, release)


@st.cache_data(ttl=86_400, show_spinner=False)
def get_latest_quarterly_release(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    if not symbol:
        return _with_latest_period("", {
            "ticker": "",
            "period_label": "N/A",
            "reported_period_label": "N/A",
            "filing_period_label": None,
            "structured_values_period_label": None,
            "period_alignment_status": "Insufficient data",
            "source_status": "Invalid ticker",
            "missing_fields": ["ticker"],
            "data_quality_note": "Invalid ticker.",
            "last_updated": now_et(),
        })
    try:
        obj = yf.Ticker(symbol)
        quote = fetch_quote(symbol)
        sec_filing = _structured_sec_filing(symbol)
        sec_values = _extract_sec_structured_values(sec_filing, quote)
        quarterly_income = _statement(obj, ("quarterly_income_stmt", "quarterly_financials"))
        quarterly_balance = _statement(obj, ("quarterly_balance_sheet",))
        quarterly_cash = _statement(obj, ("quarterly_cashflow", "quarterly_cash_flow"))
        quarterly_history = _normalize_history(quarterly_income, quarterly_balance, quarterly_cash, True, 12)
        quarterly_history = _merge_sec_quarterly_history(quarterly_history, sec_values, sec_filing)
        if not quarterly_history.empty:
            return _release_from_history(symbol, quarterly_history, quote, sec_filing, annual=False)
        annual_income = _statement(obj, ("income_stmt", "financials"))
        annual_balance = _statement(obj, ("balance_sheet",))
        annual_cash = _statement(obj, ("cashflow", "cash_flow"))
        annual_history = _normalize_history(annual_income, annual_balance, annual_cash, False, 4)
        return _release_from_history(symbol, annual_history, quote, sec_filing, annual=True)
    except Exception as exc:
        return _with_latest_period(symbol, {
            "ticker": symbol,
            "period_label": "N/A",
            "reported_period_label": "N/A",
            "filing_period_label": None,
            "structured_values_period_label": None,
            "structured_values_date": None,
            "period_alignment_status": "Insufficient data",
            "source": "Yahoo Finance/yfinance + SEC EDGAR",
            "source_status": "Source error",
            "missing_fields": ["latest quarterly release"],
            "data_quality_note": str(exc),
            "last_updated": now_et(),
        })


def _latest_earnings(obj: yf.Ticker, financial_history: pd.DataFrame) -> dict:
    try:
        dates = obj.get_earnings_dates(limit=24)
    except Exception:
        dates = pd.DataFrame()
    latest = {}
    if isinstance(dates, pd.DataFrame) and not dates.empty:
        frame = dates.reset_index()
        date_column = None
        for column in frame.columns:
            normalized = str(column).strip().casefold().replace(" ", "_")
            if normalized in {"earnings_date", "date"}:
                date_column = column
                break
        date_column = date_column or frame.columns[0]
        frame["earnings_date"] = pd.to_datetime(frame[date_column], errors="coerce")
        for _, row in frame.sort_values("earnings_date", ascending=False).iterrows():
            actual_eps = to_float(row.get("Reported EPS"))
            if actual_eps is not None:
                latest = {
                    "earnings_date": row["earnings_date"].date() if not pd.isna(row["earnings_date"]) else None,
                    "eps_actual": actual_eps,
                    "eps_estimate": to_float(row.get("EPS Estimate")),
                    "eps_surprise_pct": to_float(row.get("Surprise(%)")),
                    "source": "Yahoo Finance/yfinance earnings dates",
                }
                break
    if not financial_history.empty:
        row = financial_history.iloc[-1].to_dict()
        latest.update(
            {
                "fiscal_period": row.get("period"),
                "period_date": row.get("period_date"),
                "revenue_actual": row.get("revenue"),
                "net_income": row.get("net_income"),
                "eps_actual": latest.get("eps_actual", row.get("eps")),
            }
        )
    return latest


@st.cache_data(ttl=86_400, show_spinner=False)
def load_latest_company_financials(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return {"ticker": "", "status": "Error", "error": "Invalid ticker", "last_updated": updated}
    warnings = []
    try:
        obj = yf.Ticker(symbol)
        quote = fetch_quote(symbol)
        info = {}
        try:
            info = obj.get_info() or {}
        except Exception as exc:
            warnings.append(f"Profile unavailable: {exc}")
        quarterly_income = _statement(obj, ("quarterly_income_stmt", "quarterly_financials"))
        quarterly_balance = _statement(obj, ("quarterly_balance_sheet",))
        quarterly_cash = _statement(obj, ("quarterly_cashflow", "quarterly_cash_flow"))
        sec_filing = _structured_sec_filing(symbol)
        sec_values = _extract_sec_structured_values(sec_filing, quote)
        annual_income = _statement(obj, ("income_stmt", "financials"))
        annual_balance = _statement(obj, ("balance_sheet",))
        annual_cash = _statement(obj, ("cashflow", "cash_flow"))
        quarterly_history = _normalize_history(quarterly_income, quarterly_balance, quarterly_cash, True, 12)
        quarterly_history = _merge_sec_quarterly_history(quarterly_history, sec_values, sec_filing)
        annual_history = _normalize_history(annual_income, annual_balance, annual_cash, False, 8)
        latest = quarterly_history.iloc[-1].to_dict() if not quarterly_history.empty else {}
        latest_release = _release_from_history(symbol, quarterly_history, quote, sec_filing, annual=False) if not quarterly_history.empty else get_latest_quarterly_release(symbol)
        earnings = _latest_earnings(obj, quarterly_history)
        try:
            earnings_estimate = obj.get_earnings_estimate()
        except Exception:
            earnings_estimate = pd.DataFrame()
        try:
            revenue_estimate = obj.get_revenue_estimate()
        except Exception:
            revenue_estimate = pd.DataFrame()
        missing = []
        for key in ("revenue", "gross_profit", "gross_margin", "operating_income", "net_income", "cash", "total_debt", "operating_cash_flow"):
            if to_float(latest.get(key)) is None:
                missing.append(key)
        if missing:
            warnings.append("Missing latest quarterly fields: " + ", ".join(missing))
        if latest.get("revenue_yoy_base_effect"):
            warnings.append("Latest revenue growth may be not meaningful due to small-base effect.")
        chart_source = _chart_source_status(quarterly_history, latest_release)
        reconciliation = _financial_reconciliation(symbol, latest_release, latest, quarterly_history, chart_source)
        financial_packet = _build_financial_data_packet(symbol, quote, latest_release, reconciliation)
        metric_sources = latest_release.get("metric_sources") or {}
        fallback_metrics = [_metric_label(key) for key, detail in metric_sources.items() if detail.get("fallback_used")]
        concept_failures = [_metric_label(key) for key, detail in metric_sources.items() if detail.get("status") in {"Missing concept", "Missing", "N/A"} and key != "shares_outstanding"]
        debt_detail = metric_sources.get("total_debt") or {}
        quality = financial_packet.get("coverage_summary") or latest_release.get("financial_data_quality") or reconciliation.get("data_quality") or {}
        fcf_detail = metric_sources.get("free_cash_flow") or {}
        if reconciliation.get("warnings"):
            warnings.extend(reconciliation.get("warnings", []))
        if reconciliation.get("margin_notes"):
            warnings.extend(reconciliation.get("margin_notes", []))
        status = status_from_warnings(warnings, required_ok=bool(not quarterly_history.empty or not annual_history.empty))
        return {
            "ticker": symbol,
            "status": status,
            "company_profile": {
                "company_name": quote.get("company_name") or info.get("shortName") or symbol,
                "sector": quote.get("sector") or info.get("sector"),
                "industry": quote.get("industry") or info.get("industry"),
                "business_summary": quote.get("business_summary") or info.get("longBusinessSummary"),
                "shares_outstanding": quote.get("shares_outstanding") or to_float(info.get("sharesOutstanding")),
                "logo_url": quote.get("logo_url"),
            },
            "latest_quote": quote,
            "latest_reported_earnings": earnings,
            "latest_quarterly_release": latest_release,
            "financial_data_packet": financial_packet,
            "quarterly_income_statement": quarterly_income,
            "quarterly_balance_sheet": quarterly_balance,
            "quarterly_cash_flow": quarterly_cash,
            "annual_income_statement": annual_income,
            "annual_balance_sheet": annual_balance,
            "annual_cash_flow": annual_cash,
            "quarterly_history": quarterly_history,
            "annual_history": annual_history,
            "latest_financials": latest,
            "analyst_estimates": earnings_estimate if isinstance(earnings_estimate, pd.DataFrame) else pd.DataFrame(),
            "consensus_revenue": revenue_estimate if isinstance(revenue_estimate, pd.DataFrame) else pd.DataFrame(),
            "consensus_eps": earnings_estimate if isinstance(earnings_estimate, pd.DataFrame) else pd.DataFrame(),
            "source_metadata": {
                "financials": "Mixed SEC XBRL/companyfacts + Yahoo Finance/yfinance quarterly and annual statements" if sec_values.get("has_values") else "Yahoo Finance/yfinance quarterly and annual statements",
                "latest_release": latest_release.get("source"),
                "latest_cards_source": latest_release.get("structured_values_source"),
                "latest_cards_period": latest_release.get("structured_values_period_label"),
                "financial_packet_status": financial_packet.get("source_status"),
                "financial_packet_note": financial_packet.get("data_quality_note"),
                "ticker_type": financial_packet.get("ticker_type"),
                "sec_companyfacts": (sec_values.get("sec_companyfacts_status") or {}).get("Status"),
                "sec_value_extraction": sec_values.get("sec_value_extraction_status"),
                "chart_source": chart_source.get("label"),
                "chart_source_status": chart_source.get("status"),
                "chart_source_note": chart_source.get("note"),
                "chart_latest_period": reconciliation.get("chart_latest_period"),
                "chart_latest_period_end": reconciliation.get("chart_latest_period_end"),
                "missing_chart_fields": reconciliation.get("missing_chart_fields", []),
                "missing_metric_periods": reconciliation.get("missing_metric_periods", []),
                "margin_validity": "Partial" if reconciliation.get("margin_notes") else "OK",
                "sec_concept_coverage": "Partial" if concept_failures else "OK",
                "yfinance_fallback_metrics": fallback_metrics,
                "missing_financial_concepts": concept_failures,
                "debt_calculation_quality": debt_detail.get("status", "N/A"),
                "debt_calculation_note": debt_detail.get("note", ""),
                "debt_components_used": list(debt_detail.get("component_concepts_used") or []),
                "found_financial_fields": quality.get("found_direct", []),
                "calculated_financial_fields": quality.get("calculated", []),
                "estimated_financial_fields": quality.get("estimated", []),
                "missing_financial_fields": quality.get("missing", []),
                "financial_data_completeness": quality.get("completeness_score"),
                "financial_data_completeness_note": latest_release.get("compact_source_status_note") or reconciliation.get("compact_source_status_note"),
                "fcf_calculation_status": fcf_detail.get("status", "N/A"),
                "fcf_calculation_note": fcf_detail.get("note", ""),
                "earnings": earnings.get("source", "Yahoo Finance/yfinance financial statement fallback"),
                "estimates": "Yahoo Finance/yfinance analyst estimate tables",
            },
            "reconciliation": reconciliation,
            "validation_warnings": warnings,
            "missing_fields": missing,
            "last_updated": updated,
        }
    except Exception as exc:
        return {"ticker": symbol, "status": "Error", "error": str(exc), "validation_warnings": [str(exc)], "last_updated": updated}


def _cash_runway(latest: dict) -> float | None:
    cash = to_float(latest.get("cash"))
    fcf = to_float(latest.get("free_cash_flow"))
    if cash is None or fcf is None or fcf >= 0:
        return None
    return cash / abs(fcf) if fcf else None


def resolve_financial_data_packet(ticker: str) -> dict:
    """Return the canonical latest-period financial data packet used by Company Analysis."""
    symbol = clean_ticker(ticker)
    if not symbol:
        return {
            "ticker": "",
            "ticker_type": "invalid_unknown",
            "source_status": "Insufficient",
            "completeness_score": None,
            "fields": {},
            "missing": CORE_FINANCIAL_FIELDS,
            "data_quality_note": "Invalid ticker.",
        }
    data = load_latest_company_financials(symbol)
    packet = data.get("financial_data_packet")
    if packet:
        return packet
    quote = data.get("latest_quote") or fetch_quote(symbol)
    release = data.get("latest_quarterly_release") or get_latest_quarterly_release(symbol)
    reconciliation = data.get("reconciliation") or {}
    return _build_financial_data_packet(symbol, quote, release, reconciliation)


def _metric_meta(reconciliation: dict, metric: str) -> dict:
    for row in reconciliation.get("rows") or []:
        if row.get("metric") == metric:
            return row
    return {}


def _metric_period(reconciliation: dict, metric: str, fallback: str | None = None) -> str | None:
    row = _metric_meta(reconciliation, metric)
    return row.get("Period") or fallback


def _metric_source(reconciliation: dict, metric: str, fallback: str | None = None) -> str | None:
    row = _metric_meta(reconciliation, metric)
    return row.get("Source") or fallback


def _metric_status_note(reconciliation: dict, metric: str) -> tuple[str, str]:
    row = _metric_meta(reconciliation, metric)
    return row.get("Status") or "OK", row.get("Missing / Note") or ""


def _same_period_margin(numerator, revenue, numerator_period: str | None, revenue_period: str | None) -> tuple[float | None, str]:
    if numerator_period and revenue_period and numerator_period != revenue_period:
        return None, "Period mismatch"
    margin = _safe_margin(numerator, revenue)
    if margin is None:
        revenue_value = to_float(revenue)
        numerator_value = to_float(numerator)
        if revenue_value is None or numerator_value is None:
            return None, "N/A"
        if abs(revenue_value) < MIN_MEANINGFUL_REVENUE:
            return None, "NM: small revenue denominator"
        calculated = numerator_value / revenue_value * 100
        if abs(calculated) > 300:
            return None, "NM: extreme margin"
    return margin, "OK"


def _liquidity_status(cash_runway: float | None, cash, debt) -> str:
    if cash_runway is not None:
        if cash_runway > 8:
            return "Strong liquidity"
        if cash_runway >= 4:
            return "Moderate liquidity"
        if cash_runway >= 1:
            return "Tight liquidity"
        return "High liquidity risk"
    if cash is None:
        return "Insufficient data"
    if debt is None:
        return "Insufficient data"
    return "Strong liquidity" if cash > debt else "Net debt"


def _cash_burn_status(fcf, cash_runway: float | None) -> str:
    fcf_value = to_float(fcf)
    if fcf_value is None:
        return "N/A"
    if fcf_value >= 0:
        return "FCF positive"
    if cash_runway is not None and cash_runway < 4:
        return "Elevated burn"
    return "Burning cash"


def _profitability_status(operating_income, net_income) -> str:
    net = to_float(net_income)
    operating = to_float(operating_income)
    if net is not None and net > 0:
        return "Profitable"
    if operating is not None and operating > 0:
        return "Operating profitable"
    if net is not None and net < 0:
        return "Unprofitable"
    return "N/A"


def _data_quality_status(source_status: str, missing_fields: list[str], reconciliation: dict) -> str:
    if source_status == "Not applicable":
        return "Not applicable"
    if source_status in {"Complete", "Mostly Complete"}:
        return source_status
    if source_status == "Limited":
        return "Limited"
    if source_status == "Stale structured values":
        return "Stale"
    if source_status in {"Insufficient data", "Source error", "Not applicable"}:
        return "Insufficient"
    if reconciliation.get("has_mismatch") or source_status == "Partial" or missing_fields:
        return "Partial"
    return "OK"


def _analyst_takeaway(symbol: str, income: dict, balance: dict, cash_flow: dict, health: dict, missing_fields: list[str]) -> str:
    pieces = []
    revenue = to_float(income.get("revenue"))
    gross_profit = to_float(income.get("gross_profit"))
    net_income = to_float(income.get("net_income"))
    fcf = to_float(cash_flow.get("free_cash_flow"))
    runway = cash_flow.get("cash_runway")
    if revenue is not None and gross_profit is not None:
        pieces.append("gross profit is positive" if gross_profit > 0 else "gross profit is negative")
    elif revenue is not None:
        pieces.append("revenue is available, but gross profit is not")
    else:
        pieces.append("latest revenue is unavailable")
    if net_income is not None:
        pieces.append(f"{symbol} is profitable on net income" if net_income > 0 else f"{symbol} remains unprofitable")
    else:
        pieces.append("net income is unavailable")
    if fcf is not None:
        if fcf >= 0:
            pieces.append("free cash flow is positive")
        elif runway is not None:
            pieces.append(f"cash runway is approximately {runway:.1f} quarters based on latest quarterly free cash flow")
        else:
            pieces.append("free cash flow is negative, but runway cannot be estimated from available cash data")
    else:
        pieces.append("free cash flow is unavailable")
    if missing_fields:
        pieces.append("data is partial")
    return ". ".join(piece[:1].upper() + piece[1:] for piece in pieces if piece) + "."


def build_three_statement_visual_data(ticker: str, financials: dict | None = None) -> dict:
    symbol = clean_ticker(ticker)
    data = financials or load_latest_company_financials(symbol)
    latest = data.get("latest_financials") or {}
    release = data.get("latest_quarterly_release") or {}
    packet = data.get("financial_data_packet") or {}
    reconciliation = data.get("reconciliation") or {}
    source_metadata = data.get("source_metadata") or {}
    reported_period = release.get("reported_period_label") or latest.get("period") or "N/A"
    period_end = _date_label(release.get("period_end_date") or latest.get("period_date"))
    source = release.get("structured_values_source") or release.get("source") or source_metadata.get("financials") or "N/A"
    source_status = packet.get("source_status") or release.get("source_status") or data.get("status") or "N/A"
    income_statement = {
        "revenue": to_float(release.get("revenue")) if _value_present(release.get("revenue")) else to_float(latest.get("revenue")),
        "gross_profit": to_float(release.get("gross_profit")) if _value_present(release.get("gross_profit")) else to_float(latest.get("gross_profit")),
        "operating_income": to_float(release.get("operating_income")) if _value_present(release.get("operating_income")) else to_float(latest.get("operating_income")),
        "net_income": to_float(release.get("net_income")) if _value_present(release.get("net_income")) else to_float(latest.get("net_income")),
        "eps": to_float(release.get("eps")) if _value_present(release.get("eps")) else to_float(latest.get("eps")),
    }
    total_debt = to_float(release.get("total_debt")) if _value_present(release.get("total_debt")) else to_float(latest.get("total_debt"))
    cash = to_float(release.get("cash")) if _value_present(release.get("cash")) else to_float(latest.get("cash"))
    balance_sheet = {
        "cash": cash,
        "total_debt": total_debt,
        "net_cash_or_debt": cash - total_debt if cash is not None and total_debt is not None else None,
        "total_assets": to_float(latest.get("total_assets")),
        "shareholders_equity": to_float(latest.get("shareholders_equity")),
    }
    operating_cash_flow = to_float(release.get("operating_cash_flow")) if _value_present(release.get("operating_cash_flow")) else to_float(latest.get("operating_cash_flow"))
    capex_raw = to_float(release.get("capital_expenditures")) if _value_present(release.get("capital_expenditures")) else to_float(latest.get("capital_expenditures"))
    capex_outflow = -abs(capex_raw) if capex_raw is not None else None
    free_cash_flow = (
        operating_cash_flow + capex_outflow
        if operating_cash_flow is not None and capex_outflow is not None
        else to_float(release.get("free_cash_flow")) if _value_present(release.get("free_cash_flow")) else to_float(latest.get("free_cash_flow"))
    )
    cash_flow = {
        "operating_cash_flow": operating_cash_flow,
        "capex": capex_outflow,
        "free_cash_flow": free_cash_flow,
        "cash_runway": _cash_runway({"cash": cash, "free_cash_flow": free_cash_flow}),
    }
    missing_fields = []
    for group in (income_statement, balance_sheet, cash_flow):
        for key, value in group.items():
            if key == "cash_runway" and free_cash_flow is not None and free_cash_flow >= 0:
                continue
            if value is None:
                missing_fields.append(key)
    revenue_period = _metric_period(reconciliation, "revenue", reported_period)
    margins = {}
    margin_notes = []
    for metric, label, numerator in (
        ("gross_margin", "Gross Margin", income_statement.get("gross_profit")),
        ("operating_margin", "Operating Margin", income_statement.get("operating_income")),
        ("net_margin", "Net Margin", income_statement.get("net_income")),
        ("fcf_margin", "FCF Margin", cash_flow.get("free_cash_flow")),
    ):
        source_metric = {
            "gross_margin": "gross_profit",
            "operating_margin": "operating_income",
            "net_margin": "net_income",
            "fcf_margin": "free_cash_flow",
        }[metric]
        metric_period = _metric_period(reconciliation, source_metric, reported_period)
        value, note = _same_period_margin(numerator, income_statement.get("revenue"), metric_period, revenue_period)
        margins[metric] = {"value": value, "status": note}
        if note != "OK":
            margin_notes.append(f"{label}: {note}.")
    health_summary = {
        "profitability_status": _profitability_status(income_statement.get("operating_income"), income_statement.get("net_income")),
        "liquidity_status": _liquidity_status(cash_flow.get("cash_runway"), cash, total_debt),
        "cash_burn_status": _cash_burn_status(cash_flow.get("free_cash_flow"), cash_flow.get("cash_runway")),
        "data_completeness_status": _data_quality_status(source_status, missing_fields, reconciliation),
    }
    detailed_specs = [
        ("Income Statement", "revenue", "Revenue", income_statement.get("revenue")),
        ("Income Statement", "gross_profit", "Gross Profit", income_statement.get("gross_profit")),
        ("Income Statement", "operating_income", "Operating Income / Loss", income_statement.get("operating_income")),
        ("Income Statement", "net_income", "Net Income / Loss", income_statement.get("net_income")),
        ("Income Statement", "eps", "EPS", income_statement.get("eps")),
        ("Balance Sheet", "cash", "Cash & Equivalents", balance_sheet.get("cash")),
        ("Balance Sheet", "total_debt", "Total Debt", balance_sheet.get("total_debt")),
        ("Balance Sheet", "net_cash_or_debt", "Net Cash / Net Debt", balance_sheet.get("net_cash_or_debt")),
        ("Balance Sheet", "total_assets", "Total Assets", balance_sheet.get("total_assets")),
        ("Balance Sheet", "shareholders_equity", "Shareholders' Equity", balance_sheet.get("shareholders_equity")),
        ("Cash Flow", "operating_cash_flow", "Operating Cash Flow", cash_flow.get("operating_cash_flow")),
        ("Cash Flow", "capital_expenditures", "Capital Expenditures", cash_flow.get("capex")),
        ("Cash Flow", "free_cash_flow", "Free Cash Flow", cash_flow.get("free_cash_flow")),
        ("Cash Flow", "cash_runway", "Cash Runway", cash_flow.get("cash_runway")),
    ]
    detailed_rows = []
    for statement, key, label, value in detailed_specs:
        lookup_key = "capital_expenditures" if key == "capital_expenditures" else key
        status, note = _metric_status_note(reconciliation, lookup_key)
        if value is None:
            status = "Missing"
        detailed_rows.append(
            {
                "statement": statement,
                "metric": key,
                "label": label,
                "value": value,
                "period": _metric_period(reconciliation, lookup_key, reported_period) or reported_period,
                "source": _metric_source(reconciliation, lookup_key, source) or source,
                "status": status,
                "note": note or ("Unavailable from latest structured source." if value is None else ""),
            }
        )
    reconciliation_notes = list(reconciliation.get("warnings") or [])
    if margin_notes:
        reconciliation_notes.extend(margin_notes)
    if reconciliation.get("has_mismatch"):
        reconciliation_notes.append("Financial statement values are partially sourced or period-mismatched. Review detailed table before relying on this view.")
    data_quality_note = packet.get("data_quality_note") or release.get("compact_source_status_note") or source_metadata.get("chart_source_note") or release.get("data_quality_note")
    return {
        "ticker": symbol,
        "reported_period": reported_period,
        "period_end_date": period_end,
        "source": source,
        "source_status": source_status,
        "data_quality_note": data_quality_note,
        "analyst_takeaway": _analyst_takeaway(symbol, income_statement, balance_sheet, cash_flow, health_summary, missing_fields),
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "margins": margins,
        "health_summary": health_summary,
        "missing_fields": missing_fields,
        "reconciliation_notes": reconciliation_notes,
        "detailed_rows": detailed_rows,
        "reconciliation": reconciliation,
    }


def view_history(financials: dict, view: str) -> pd.DataFrame:
    return financials.get("annual_history" if view == "Annual" else "quarterly_history", pd.DataFrame())
