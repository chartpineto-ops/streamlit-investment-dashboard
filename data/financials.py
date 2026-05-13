from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

from data.filings import extract_sec_concept_value, fetch_latest_periodic_sec_filing, fetch_latest_sec_filing, get_sec_company_facts
from data.market_data import fetch_quote
from utils.formatting import clean_ticker, now_et, safe_div, to_float
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
    parts = str(label).upper().replace("FY", "Q4").split()
    if len(parts) < 2:
        return None
    try:
        year = int(parts[0])
    except Exception:
        return None
    quarter_text = parts[1].replace("Q", "")
    try:
        quarter = int(quarter_text)
    except Exception:
        quarter = 4
    return year, quarter


def _period_alignment(sec_label: str | None, structured_label: str | None) -> tuple[str, str]:
    if sec_label and structured_label:
        if sec_label == structured_label:
            return "Aligned", "OK"
        sec_key = _period_sort_key(sec_label)
        structured_key = _period_sort_key(structured_label)
        if sec_key and structured_key and sec_key > structured_key:
            return "Filing newer than structured values", "Stale structured values"
        return "Filing newer than structured values", "Partial"
    if sec_label:
        return "Filing metadata only", "Filing metadata only"
    if structured_label:
        return "Structured values only", "Partial"
    return "Insufficient data", "Insufficient data"


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
        return {
            "ticker": symbol,
            "period_label": filing_label or "N/A",
            "reported_period_label": filing_label or "N/A",
            "filing_period_label": filing_label,
            "structured_values_period_label": None,
            "structured_values_date": None,
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
            "period_end_date": period_end,
            "missing_fields": ["quarterly financial statements"],
            "data_quality_note": note,
            "last_updated": updated,
        }
    row = history.iloc[-1].to_dict()
    fiscal_year, fiscal_quarter, structured_label, structured_date = _structured_period_label(row.get("period_date"), annual)
    structured_source = row.get("structured_values_source") or ("Yahoo Finance annual statements" if annual else "Yahoo Finance quarterly statements")
    sec_structured = structured_source == "SEC XBRL/companyfacts"
    if sec_structured:
        filing_label = filing_label or structured_label
    reported_label = filing_label or structured_label
    alignment_status, alignment_source_status = ("Aligned", "OK") if sec_structured and filing_label == structured_label else _period_alignment(filing_label, structured_label)
    values = {
        "revenue": row.get("revenue"),
        "gross_profit": row.get("gross_profit"),
        "operating_income": row.get("operating_income"),
        "net_income": row.get("net_income"),
        "eps": row.get("eps"),
        "operating_cash_flow": row.get("operating_cash_flow"),
        "capital_expenditures": row.get("capital_expenditures"),
        "free_cash_flow": row.get("free_cash_flow"),
        "cash": row.get("cash"),
        "total_debt": row.get("total_debt"),
        "shares_outstanding": quote.get("shares_outstanding"),
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
    try:
        if alignment_status == "Aligned" and filing_date and period_date and pd.Timestamp(filing_date) > pd.Timestamp(period_date) + pd.Timedelta(days=120):
            note = "Latest filing detected; structured financial values may lag the filing metadata."
            if source_status == "OK":
                source_status = "Partial"
    except Exception:
        pass
    return {
        "ticker": symbol,
        "period_label": reported_label,
        "reported_period_label": reported_label,
        "filing_period_label": filing_label,
        "structured_values_period_label": structured_label,
        "structured_values_date": structured_date,
        "period_alignment_status": alignment_status,
        "fiscal_year": sec_fiscal_year or fiscal_year,
        "fiscal_quarter": fiscal_quarter if not annual else None,
        "fiscal_period": sec_fiscal_period or ("FY" if annual else (f"Q{fiscal_quarter}" if fiscal_quarter else None)),
        "period_end_date": period_end,
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
        "last_updated": updated,
    }


@st.cache_data(ttl=86_400, show_spinner=False)
def get_latest_quarterly_release(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    if not symbol:
        return {
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
        }
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
        return {
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
        }


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
            if latest.get(key) is None:
                missing.append(key)
        if missing:
            warnings.append("Missing latest quarterly fields: " + ", ".join(missing))
        if latest.get("revenue_yoy_base_effect"):
            warnings.append("Latest revenue growth may be not meaningful due to small-base effect.")
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
                "sec_companyfacts": (sec_values.get("sec_companyfacts_status") or {}).get("Status"),
                "sec_value_extraction": sec_values.get("sec_value_extraction_status"),
                "earnings": earnings.get("source", "Yahoo Finance/yfinance financial statement fallback"),
                "estimates": "Yahoo Finance/yfinance analyst estimate tables",
            },
            "validation_warnings": warnings,
            "missing_fields": missing,
            "last_updated": updated,
        }
    except Exception as exc:
        return {"ticker": symbol, "status": "Error", "error": str(exc), "validation_warnings": [str(exc)], "last_updated": updated}


def view_history(financials: dict, view: str) -> pd.DataFrame:
    return financials.get("annual_history" if view == "Annual" else "quarterly_history", pd.DataFrame())
