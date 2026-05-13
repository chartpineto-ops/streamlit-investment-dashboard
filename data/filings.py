from __future__ import annotations

import requests
import pandas as pd
import streamlit as st

from utils.formatting import clean_ticker, now_et

HEADERS = {"User-Agent": "Research Terminal 2.0 V1 contact@example.com"}
RELEVANT_FORMS = {"10-Q", "10-K", "8-K", "6-K", "20-F"}


def _value_at(values, index: int):
    try:
        value = values[index]
        if value in ("", None):
            return None
        return value
    except Exception:
        return None


def _quarter_from_report_date(report_date: str | None, form_type: str | None) -> str | None:
    if not report_date:
        return None
    try:
        ts = pd.Timestamp(report_date)
    except Exception:
        return None
    if form_type in {"10-K", "20-F"}:
        return "FY"
    if form_type == "10-Q":
        return f"Q{ts.quarter}"
    return None


def _filing_period_label(fiscal_year, fiscal_period, report_date, form_type: str | None) -> str | None:
    year = None
    try:
        year = int(fiscal_year) if fiscal_year not in ("", None) else None
    except Exception:
        year = None
    period = str(fiscal_period or "").strip().upper() or _quarter_from_report_date(report_date, form_type)
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
    if year is None and report_date:
        try:
            year = pd.Timestamp(report_date).year
        except Exception:
            year = None
    if year is None or not period:
        return None
    return f"{year} FY" if period == "FY" else f"{year} {period}"


@st.cache_data(ttl=86_400, show_spinner=False)
def ticker_to_cik(ticker: str) -> tuple[str | None, dict]:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return None, {"Source": "SEC ticker-to-CIK", "Status": "Invalid ticker", "Last Updated": updated, "Error": "Invalid ticker"}
    try:
        tickers = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=12).json()
        for item in tickers.values():
            if str(item.get("ticker", "")).upper() == symbol:
                return str(item.get("cik_str")).zfill(10), {"Source": "SEC ticker-to-CIK", "Status": "OK", "Last Updated": updated, "Error": ""}
        return None, {"Source": "SEC ticker-to-CIK", "Status": "Missing", "Last Updated": updated, "Error": "CIK not found"}
    except Exception as exc:
        return None, {"Source": "SEC ticker-to-CIK", "Status": "Source error", "Last Updated": updated, "Error": str(exc)}


def _filing_url(cik: str, accession: str, doc: str) -> str | None:
    if not cik or not accession or not doc:
        return None
    accession_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{doc}"


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_latest_sec_filing(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    updated = now_et()
    cik, cik_status = ticker_to_cik(symbol)
    if not cik:
        return {
            "ticker": symbol,
            "source": "SEC EDGAR submissions",
            "source_status": cik_status.get("Status", "Missing"),
            "last_updated": updated,
            "error": cik_status.get("Error", "CIK not found"),
        }
    try:
        payload = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS, timeout=12).json()
        recent = payload.get("filings", {}).get("recent", {})
        rows = []
        forms = recent.get("form", [])
        for index, form in enumerate(forms):
            filed = _value_at(recent.get("filingDate", []), index)
            report = _value_at(recent.get("reportDate", []), index)
            accession = _value_at(recent.get("accessionNumber", []), index)
            doc = _value_at(recent.get("primaryDocument", []), index)
            fiscal_year = _value_at(recent.get("fiscalYear", []), index)
            fiscal_period = _value_at(recent.get("fiscalPeriod", []), index)
            if form in RELEVANT_FORMS:
                rows.append(
                    {
                        "ticker": symbol,
                        "cik": cik,
                        "form_type": form,
                        "filing_date": filed,
                        "report_date": report,
                        "period_end_date": report,
                        "fiscal_year": fiscal_year,
                        "fiscal_period": fiscal_period or _quarter_from_report_date(report, form),
                        "filing_period_label": _filing_period_label(fiscal_year, fiscal_period, report, form),
                        "accession_number": accession,
                        "primary_document": doc,
                        "filing_url": _filing_url(cik, accession, doc),
                    }
                )
        if not rows:
            return {"ticker": symbol, "source": "SEC EDGAR submissions", "source_status": "Missing", "last_updated": updated, "error": "No relevant filings found"}
        row = rows[0]
        row.update({"source": f"SEC EDGAR latest {row['form_type']}", "source_status": "OK", "last_updated": updated, "error": ""})
        return row
    except Exception as exc:
        return {"ticker": symbol, "source": "SEC EDGAR submissions", "source_status": "Source error", "last_updated": updated, "error": str(exc)}


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_sec_filings(ticker: str) -> tuple[pd.DataFrame, dict]:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": "Error", "Last Updated": updated, "Error": "Invalid ticker"}
    try:
        cik, cik_status = ticker_to_cik(symbol)
        if not cik:
            return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": cik_status.get("Status", "Unavailable"), "Last Updated": updated, "Error": cik_status.get("Error", "CIK not found")}
        payload = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS, timeout=12).json()
        recent = payload.get("filings", {}).get("recent", {})
        rows = []
        for form, date_filed, accession, doc in zip(recent.get("form", []), recent.get("filingDate", []), recent.get("accessionNumber", []), recent.get("primaryDocument", [])):
            if form in RELEVANT_FORMS:
                url = _filing_url(cik, accession, doc)
                rows.append({"Form": form, "Filing Date": date_filed, "Accession": accession, "Link": url})
        frame = pd.DataFrame(rows).drop_duplicates("Form").head(3)
        return frame, {"Source": "SEC EDGAR", "Status": "OK", "Last Updated": updated, "Error": ""}
    except Exception as exc:
        return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": "Error", "Last Updated": updated, "Error": str(exc)}
