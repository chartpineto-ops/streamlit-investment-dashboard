from __future__ import annotations

import requests
import pandas as pd
import streamlit as st

from utils.formatting import clean_ticker, now_et

HEADERS = {"User-Agent": "Research Terminal 2.0 V1 contact@example.com"}
RELEVANT_FORMS = {"10-Q", "10-K", "8-K", "6-K", "20-F"}


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
        for form, filed, report, accession, doc in zip(
            recent.get("form", []),
            recent.get("filingDate", []),
            recent.get("reportDate", []),
            recent.get("accessionNumber", []),
            recent.get("primaryDocument", []),
        ):
            if form in RELEVANT_FORMS:
                rows.append(
                    {
                        "ticker": symbol,
                        "cik": cik,
                        "form_type": form,
                        "filing_date": filed,
                        "report_date": report,
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
