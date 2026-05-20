from __future__ import annotations

import base64
from urllib.parse import urlparse

import requests
import streamlit as st
import yfinance as yf

from utils.formatting import clean_ticker, now_et

LOGO_HEADERS = {"User-Agent": "PineTerminal V1 logo check"}


def _domain_from_website(website: str | None) -> str | None:
    if not website:
        return None
    value = str(website).strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    try:
        domain = urlparse(value).netloc.lower()
    except Exception:
        return None
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def _fallback_initials(ticker: str, company_name: str | None) -> str:
    if company_name:
        parts = [part[0] for part in str(company_name).replace(",", " ").split() if part and part[0].isalnum()]
        if len(parts) >= 2:
            return "".join(parts[:2]).upper()
    return "".join(ch for ch in ticker if ch.isalnum())[:2].upper() or "PT"


def _fetch_logo_data_uri(url: str | None) -> str | None:
    if not url or not str(url).startswith("https://"):
        return None
    try:
        response = requests.get(url, headers=LOGO_HEADERS, timeout=4, stream=True)
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or "image" not in content_type.lower():
            return None
        payload = response.content
        if not payload:
            return None
        encoded = base64.b64encode(payload).decode("ascii")
        return f"data:{content_type.split(';')[0]};base64,{encoded}"
    except Exception:
        return None


def _candidate_logo_urls(info: dict, domain: str | None, symbol: str | None = None) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for key in ("logo_url", "logoUrl", "logoURL"):
        value = str(info.get(key) or "").strip()
        if value.startswith("https://"):
            candidates.append((value, "Yahoo Finance logo URL"))
    clean_symbol = clean_ticker(symbol or "")
    if clean_symbol:
        logo_symbol = clean_symbol.replace(".", "-")
        candidates.append((f"https://financialmodelingprep.com/image-stock/{logo_symbol}.png", "Financial Modeling Prep public logo"))
        candidates.append((f"https://companiesmarketcap.com/img/company-logos/128/{logo_symbol}.png", "CompaniesMarketCap public logo"))
    if domain:
        candidates.append((f"https://logo.clearbit.com/{domain}?size=256", "Clearbit domain logo"))
        candidates.append((f"https://www.google.com/s2/favicons?sz=256&domain={domain}", "Google favicon fallback"))
        candidates.append((f"https://icons.duckduckgo.com/ip3/{domain}.ico", "DuckDuckGo favicon fallback"))
    return candidates


@st.cache_data(ttl=86_400, show_spinner=False)
def get_company_identity(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return {
            "ticker": "",
            "company_name": "",
            "short_name": "",
            "exchange": None,
            "quote_type": None,
            "sector": None,
            "industry": None,
            "website": None,
            "domain": None,
            "logo_url": None,
            "logo_data_uri": None,
            "logo_status": "Invalid ticker",
            "logo_source": "N/A",
            "fallback_initials": "PT",
            "last_updated": updated,
        }
    try:
        info = yf.Ticker(symbol).get_info() or {}
        company_name = info.get("longName") or info.get("shortName") or symbol
        short_name = info.get("shortName") or company_name
        website = info.get("website")
        domain = _domain_from_website(website)
        logo_url = None
        logo_data_uri = None
        logo_source = "Initials placeholder"
        logo_status = "Missing website" if not domain else "Placeholder"
        fallback_candidate = None
        for candidate, source in _candidate_logo_urls(info, domain, symbol):
            fallback_candidate = fallback_candidate or (candidate, source)
            data_uri = _fetch_logo_data_uri(candidate)
            if data_uri:
                logo_url = candidate
                logo_data_uri = data_uri
                logo_source = source
                logo_status = "OK"
                break
        if logo_url is None and fallback_candidate:
            logo_url, logo_source = fallback_candidate
            logo_status = "OK"
        return {
            "ticker": symbol,
            "company_name": company_name,
            "short_name": short_name,
            "exchange": info.get("exchange") or info.get("fullExchangeName"),
            "quote_type": info.get("quoteType"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "website": website,
            "domain": domain,
            "logo_url": logo_url,
            "logo_data_uri": logo_data_uri,
            "logo_status": logo_status,
            "logo_source": logo_source,
            "fallback_initials": _fallback_initials(symbol, company_name),
            "last_updated": updated,
        }
    except Exception as exc:
        return {
            "ticker": symbol,
            "company_name": symbol,
            "short_name": symbol,
            "exchange": None,
            "quote_type": None,
            "sector": None,
            "industry": None,
            "website": None,
            "domain": None,
            "logo_url": None,
            "logo_data_uri": None,
            "logo_status": "Source error",
            "logo_source": "N/A",
            "fallback_initials": _fallback_initials(symbol, symbol),
            "last_updated": updated,
            "error": str(exc),
        }
