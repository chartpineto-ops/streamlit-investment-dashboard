from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

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


def _normalize_history(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame, quarterly: bool, limit: int = 8) -> pd.DataFrame:
    common = set(_periods(income)) & set(_periods(balance)) & set(_periods(cashflow))
    periods = sorted(common)[-limit:] if common else _periods(income, balance, cashflow)[-limit:]
    rows = []
    for period in periods:
        row = {"period_date": period, "period": f"{period.year} Q{period.quarter}" if quarterly else f"FY {period.year}"}
        for key, aliases in FIELD_MAP.items():
            source = income if key in {"revenue", "cost_of_revenue", "gross_profit", "operating_income", "net_income", "eps"} else balance if key in {"cash", "current_assets", "total_assets", "current_liabilities", "total_liabilities", "total_debt", "shareholders_equity"} else cashflow
            row[key] = _line(source, period, aliases)
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
    if not frame.empty:
        frame["prior_revenue_for_yoy"] = frame["revenue"].shift(4 if quarterly else 1)
        frame["prior_revenue_for_qoq"] = frame["revenue"].shift(1)
        frame["revenue_yoy_growth"] = frame["revenue"].pct_change(4 if quarterly else 1, fill_method=None) * 100
        frame["revenue_qoq_growth"] = frame["revenue"].pct_change(1, fill_method=None) * 100
        frame["revenue_yoy_base_effect"] = (frame["prior_revenue_for_yoy"].abs() < MIN_MEANINGFUL_REVENUE) | (frame["revenue_yoy_growth"].abs() > 500)
        frame["revenue_qoq_base_effect"] = (frame["prior_revenue_for_qoq"].abs() < MIN_MEANINGFUL_REVENUE) | (frame["revenue_qoq_growth"].abs() > 500)
        frame["eps_yoy_growth"] = frame["eps"].pct_change(4 if quarterly else 1, fill_method=None) * 100
        frame["eps_qoq_growth"] = frame["eps"].pct_change(1, fill_method=None) * 100
    return frame


def _latest_earnings(obj: yf.Ticker, financial_history: pd.DataFrame) -> dict:
    try:
        dates = obj.get_earnings_dates(limit=24)
    except Exception:
        dates = pd.DataFrame()
    latest = {}
    if isinstance(dates, pd.DataFrame) and not dates.empty:
        frame = dates.reset_index().rename(columns={"index": "earnings_date"})
        frame["earnings_date"] = pd.to_datetime(frame["earnings_date"], errors="coerce")
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
        annual_income = _statement(obj, ("income_stmt", "financials"))
        annual_balance = _statement(obj, ("balance_sheet",))
        annual_cash = _statement(obj, ("cashflow", "cash_flow"))
        quarterly_history = _normalize_history(quarterly_income, quarterly_balance, quarterly_cash, True, 12)
        annual_history = _normalize_history(annual_income, annual_balance, annual_cash, False, 8)
        latest = quarterly_history.iloc[-1].to_dict() if not quarterly_history.empty else {}
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
                "financials": "Yahoo Finance/yfinance quarterly and annual statements",
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
