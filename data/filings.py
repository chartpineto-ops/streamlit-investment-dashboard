from __future__ import annotations

import requests
import pandas as pd
import streamlit as st

from utils.formatting import clean_ticker, now_et

HEADERS = {"User-Agent": "Research Terminal 2.0 V1 contact@example.com"}
RELEVANT_FORMS = {"10-Q", "10-K", "8-K", "6-K", "20-F"}
PERIODIC_FORMS = {"10-Q", "10-K", "20-F"}


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
def get_sec_company_facts(cik: str) -> tuple[dict, dict]:
    updated = now_et()
    cik_clean = str(cik or "").strip().zfill(10)
    if not cik_clean or not cik_clean.isdigit():
        return {}, {"Source": "SEC companyfacts", "Status": "Missing", "Last Updated": updated, "Error": "Missing CIK"}
    try:
        payload = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_clean}.json", headers=HEADERS, timeout=18).json()
        if not payload.get("facts"):
            return {}, {"Source": "SEC companyfacts", "Status": "Missing", "Last Updated": updated, "Error": "No companyfacts returned"}
        return payload, {"Source": "SEC companyfacts", "Status": "OK", "Last Updated": updated, "Error": ""}
    except Exception as exc:
        return {}, {"Source": "SEC companyfacts", "Status": "Source error", "Last Updated": updated, "Error": str(exc)}


def extract_sec_concept_value(
    company_facts: dict,
    concepts: tuple[str, ...],
    form_types: tuple[str, ...],
    period_end_date,
    fiscal_year=None,
    fiscal_period=None,
    accession_number: str | None = None,
) -> dict:
    try:
        target_end = pd.Timestamp(period_end_date).strftime("%Y-%m-%d")
    except Exception:
        target_end = None
    fy = None
    try:
        fy = int(fiscal_year) if fiscal_year not in ("", None) else None
    except Exception:
        fy = None
    fp = str(fiscal_period or "").strip().upper() or None
    forms = set(form_types)
    candidates = []
    facts = company_facts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        concept_block = facts.get(concept, {})
        for unit, values in concept_block.get("units", {}).items():
            for item in values:
                if forms and item.get("form") not in forms:
                    continue
                if target_end and item.get("end") != target_end:
                    continue
                if fy is not None and item.get("fy") not in (fy, str(fy)):
                    continue
                if fp and str(item.get("fp") or "").upper() != fp:
                    continue
                score = 0
                if accession_number and item.get("accn") == accession_number:
                    score += 5
                if target_end and item.get("end") == target_end:
                    score += 4
                if fy is not None and item.get("fy") in (fy, str(fy)):
                    score += 2
                if fp and str(item.get("fp") or "").upper() == fp:
                    score += 2
                frame = str(item.get("frame") or "").upper()
                if frame:
                    score += 1
                    if fp and fp != "FY" and fp in frame and "YTD" not in frame:
                        score += 3
                    if "YTD" in frame and fp not in {"", None, "FY"}:
                        score -= 3
                start = item.get("start")
                if start and target_end:
                    try:
                        days = (pd.Timestamp(target_end) - pd.Timestamp(start)).days + 1
                        if fp == "FY":
                            if 300 <= days <= 400:
                                score += 3
                        else:
                            if 70 <= days <= 110:
                                score += 3
                            elif days > 120:
                                score -= 2
                    except Exception:
                        pass
                candidates.append((score, concept, unit, item))
    if not candidates:
        return {"value": None, "concept": None, "unit": None, "source_note": "SEC concept not found for matching period"}
    score, concept, unit, item = sorted(candidates, key=lambda row: (row[0], str(row[3].get("filed") or "")), reverse=True)[0]
    return {
        "value": item.get("val"),
        "unit": unit,
        "concept": concept,
        "form": item.get("form"),
        "filed": item.get("filed"),
        "accession_number": item.get("accn"),
        "fiscal_year": item.get("fy"),
        "fiscal_period": item.get("fp"),
        "period_end_date": item.get("end"),
        "source_note": f"SEC companyfacts {concept}",
    }


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
def fetch_latest_periodic_sec_filing(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    updated = now_et()
    cik, cik_status = ticker_to_cik(symbol)
    if not cik:
        return {
            "ticker": symbol,
            "source": "SEC EDGAR periodic submissions",
            "source_status": cik_status.get("Status", "Missing"),
            "last_updated": updated,
            "error": cik_status.get("Error", "CIK not found"),
        }
    try:
        payload = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS, timeout=12).json()
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        for index, form in enumerate(forms):
            if form not in PERIODIC_FORMS:
                continue
            filed = _value_at(recent.get("filingDate", []), index)
            report = _value_at(recent.get("reportDate", []), index)
            accession = _value_at(recent.get("accessionNumber", []), index)
            doc = _value_at(recent.get("primaryDocument", []), index)
            fiscal_year = _value_at(recent.get("fiscalYear", []), index)
            fiscal_period = _value_at(recent.get("fiscalPeriod", []), index)
            return {
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
                "source": f"SEC EDGAR latest periodic {form}",
                "source_status": "OK",
                "last_updated": updated,
                "error": "",
            }
        return {"ticker": symbol, "source": "SEC EDGAR periodic submissions", "source_status": "Missing", "last_updated": updated, "error": "No periodic filings found"}
    except Exception as exc:
        return {"ticker": symbol, "source": "SEC EDGAR periodic submissions", "source_status": "Source error", "last_updated": updated, "error": str(exc)}


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
