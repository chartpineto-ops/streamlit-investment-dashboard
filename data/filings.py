from __future__ import annotations

import requests
import pandas as pd
import streamlit as st

from utils.formatting import clean_ticker, now_et

HEADERS = {"User-Agent": "Research Terminal 2.0 V1 contact@example.com"}


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_sec_filings(ticker: str) -> tuple[pd.DataFrame, dict]:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": "Error", "Last Updated": updated, "Error": "Invalid ticker"}
    try:
        tickers = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=12).json()
        cik = None
        for item in tickers.values():
            if str(item.get("ticker", "")).upper() == symbol:
                cik = str(item.get("cik_str")).zfill(10)
                break
        if not cik:
            return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": "Unavailable", "Last Updated": updated, "Error": "CIK not found"}
        payload = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS, timeout=12).json()
        recent = payload.get("filings", {}).get("recent", {})
        rows = []
        for form, date_filed, accession, doc in zip(recent.get("form", []), recent.get("filingDate", []), recent.get("accessionNumber", []), recent.get("primaryDocument", [])):
            if form in {"10-K", "10-Q", "8-K"}:
                accession_clean = accession.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{doc}"
                rows.append({"Form": form, "Filing Date": date_filed, "Accession": accession, "Link": url})
        frame = pd.DataFrame(rows).drop_duplicates("Form").head(3)
        return frame, {"Source": "SEC EDGAR", "Status": "OK", "Last Updated": updated, "Error": ""}
    except Exception as exc:
        return pd.DataFrame(), {"Source": "SEC EDGAR", "Status": "Error", "Last Updated": updated, "Error": str(exc)}

