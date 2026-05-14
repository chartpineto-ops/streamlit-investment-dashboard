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
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
    "cash": (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    "total_debt": (
        "LongTermDebt",
        "LongTermDebtCurrent",
        "ShortTermBorrowings",
        "DebtCurrent",
        "LongTermDebtAndFinanceLeaseObligations",
        "LongTermDebtAndFinanceLeaseObligationsCurrent",
    ),
    "operating_cash_flow": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    "capital_expenditures": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForProceedsFromProductiveAssets",
    ),
    "shares_outstanding": (
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ),
}

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
    "shares_outstanding": "Shares Outstanding",
}

INCOME_STATEMENT_METRICS = {"revenue", "gross_profit", "operating_income", "net_income", "eps"}
BALANCE_SHEET_METRICS = {"cash", "total_debt", "shares_outstanding"}
CASH_FLOW_METRICS = {"operating_cash_flow", "capital_expenditures", "free_cash_flow"}
CHART_REQUIRED_METRICS = {"revenue": "Revenue", "eps": "EPS"}


def _label_list(values: list[str], limit: int = 5) -> str:
    cleaned = [str(value) for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return ", ".join(cleaned)
    return ", ".join(cleaned[:limit]) + f", +{len(cleaned) - limit} more"


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


def _extract_sec_structured_values(sec_filing: dict, quote: dict | None = None) -> dict:
    updated = now_et()
    form_type = sec_filing.get("form_type")
    period_end = sec_filing.get("period_end_date") or sec_filing.get("report_date")
    filing_label, fiscal_year, fiscal_period, _ = _sec_period_label(sec_filing, form_type in {"10-K", "20-F"})
    if form_type not in {"10-Q", "10-K", "20-F"} or not period_end or not sec_filing.get("cik"):
        return {
            "has_values": False,
            "source_status": "Not applicable",
            "missing_fields": list(SEC_CONCEPTS),
            "data_quality_note": "SEC structured extraction is only attempted for 10-Q, 10-K, and 20-F filings with a period end date.",
            "last_updated": updated,
        }
    company_facts, facts_status = get_sec_company_facts(sec_filing.get("cik"))
    if facts_status.get("Status") != "OK":
        return {
            "has_values": False,
            "source_status": facts_status.get("Status", "Source error"),
            "missing_fields": list(SEC_CONCEPTS),
            "data_quality_note": facts_status.get("Error", "SEC companyfacts unavailable."),
            "last_updated": updated,
            "sec_companyfacts_status": facts_status,
        }
    forms = (form_type,)
    values = {}
    concept_sources = {}
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
            missing.append(key)
        else:
            concept_sources[key] = result
    if values.get("free_cash_flow") is None and values.get("operating_cash_flow") is not None and values.get("capital_expenditures") is not None:
        values["free_cash_flow"] = values["operating_cash_flow"] - abs(values["capital_expenditures"])
    has_values = any(values.get(key) is not None for key in ("revenue", "net_income", "eps", "cash", "operating_cash_flow"))
    if "free_cash_flow" not in missing and values.get("free_cash_flow") is None:
        missing.append("free_cash_flow")
    if quote and values.get("shares_outstanding") is None:
        values["shares_outstanding"] = quote.get("shares_outstanding")
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
    rows = []
    for key, label in RECONCILIATION_METRICS.items():
        raw_value = latest_release.get(key)
        metric_source = source
        metric_period = values_period
        metric_period_end = values_period_end
        note = latest_release.get("source_status_reason") or latest_release.get("data_quality_note", "")
        if key == "shares_outstanding":
            raw_value = latest_release.get(key) if _value_present(latest_release.get(key)) else latest_row.get(key)
            metric_source = "Quote metadata / latest provider"
            metric_period = "Latest quote"
            metric_period_end = None
        elif not _value_present(raw_value):
            metric_period = values_period or latest_row.get("period")
            metric_period_end = values_period_end or _date_label(latest_row.get("period_date"))
            note = f"{label} unavailable from {metric_source or 'structured source'}."
        rows.append(
            {
                "metric": key,
                "Metric": label,
                "value": raw_value,
                "Period": metric_period or "N/A",
                "Period End Date": metric_period_end or "N/A",
                "Source": metric_source or "N/A",
                "Form": form or "N/A",
                "Filed Date": filed_date or "N/A",
                "Accession": accession or "N/A",
                "Status": "OK" if _value_present(raw_value) else "Missing",
                "Missing / Note": note,
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
    revenue_period = next((row["Period"] for row in rows if row["metric"] == "revenue" and row["Status"] == "OK"), None)
    eps_period = next((row["Period"] for row in rows if row["metric"] == "eps" and row["Status"] == "OK"), None)
    add_check(
        "Revenue period equals EPS period",
        None if not revenue_period or not eps_period else revenue_period == eps_period,
        f"Revenue: {revenue_period or 'N/A'} | EPS: {eps_period or 'N/A'}",
    )
    income_periods = {row["Period"] for row in rows if row["metric"] in INCOME_STATEMENT_METRICS and row["Status"] == "OK"}
    balance_periods = {row["Period"] for row in rows if row["metric"] in BALANCE_SHEET_METRICS and row["Status"] == "OK" and row["metric"] != "shares_outstanding"}
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
    return {
        "ticker": symbol,
        "rows": rows,
        "checks": checks,
        "has_mismatch": bool(check_warnings),
        "warnings": warnings,
        "missing_chart_fields": missing_chart_fields,
        "missing_metric_periods": [row["Metric"] for row in rows if row["Status"] == "Missing"],
        "margin_notes": margin_notes,
        "chart_latest_period": chart_latest_period,
        "chart_latest_period_end": chart_latest_period_end,
        "chart_latest_source": chart_latest_source,
    }


def _release_from_history(symbol: str, history: pd.DataFrame, quote: dict, sec_filing: dict, annual: bool = False) -> dict:
    updated = now_et()
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
        "shares_outstanding": to_float(quote.get("shares_outstanding")),
    }
    missing = row.get("sec_missing_fields") if sec_structured and isinstance(row.get("sec_missing_fields"), list) else [key for key, value in values.items() if value is None and key not in {"eps", "shares_outstanding"}]
    source_status = alignment_source_status if alignment_source_status != "OK" else ("OK" if not missing else "Partial")
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
        "data_quality_note": note,
        "source_status_reason": _source_status_reason(source_status, values, missing, structured_source, note),
        "last_updated": updated,
    }
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


def build_three_statement_visual_data(ticker: str, financials: dict | None = None) -> dict:
    symbol = clean_ticker(ticker)
    data = financials or load_latest_company_financials(symbol)
    latest = data.get("latest_financials") or {}
    release = data.get("latest_quarterly_release") or {}
    reconciliation = data.get("reconciliation") or {}
    source_metadata = data.get("source_metadata") or {}
    reported_period = release.get("reported_period_label") or latest.get("period") or "N/A"
    period_end = _date_label(release.get("period_end_date") or latest.get("period_date"))
    source = release.get("structured_values_source") or release.get("source") or source_metadata.get("financials") or "N/A"
    source_status = release.get("source_status") or data.get("status") or "N/A"
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
    net_income = income_statement.get("net_income")
    fcf = cash_flow.get("free_cash_flow")
    health_summary = {
        "profitability_status": "Profitable" if net_income is not None and net_income > 0 else "Unprofitable" if net_income is not None and net_income < 0 else "Insufficient data",
        "liquidity_status": "Cash-rich" if cash is not None and total_debt is not None and cash >= total_debt else "Net debt" if cash is not None and total_debt is not None else "Debt data unavailable",
        "cash_burn_status": "FCF positive" if fcf is not None and fcf >= 0 else "Burning cash" if fcf is not None else "Insufficient data",
        "data_completeness_status": "Complete" if not missing_fields else "Partial data" if len(missing_fields) <= 5 else "Insufficient data",
    }
    return {
        "ticker": symbol,
        "reported_period": reported_period,
        "period_end_date": period_end,
        "source": source,
        "source_status": source_status,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "health_summary": health_summary,
        "missing_fields": missing_fields,
        "data_quality_note": release.get("source_status_reason") or release.get("data_quality_note") or source_metadata.get("chart_source_note"),
        "reconciliation": reconciliation,
    }


def view_history(financials: dict, view: str) -> pd.DataFrame:
    return financials.get("annual_history" if view == "Annual" else "quarterly_history", pd.DataFrame())
