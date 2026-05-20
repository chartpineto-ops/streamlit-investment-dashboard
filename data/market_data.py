from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
import streamlit as st
import yfinance as yf

from data.company_identity import get_company_identity
from utils.formatting import clean_ticker, now_et, safe_div, to_float

DEFAULT_TICKERS = ["CRWV", "IONQ", "AMPX", "AI", "ASTS", "NVDA", "PLTR", "SPY", "VOO", "FBTC", "VOLT", "REMX"]
MARKET_SYMBOLS = {
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "DIA": "Dow ETF",
    "IWM": "Russell 2000 ETF",
    "^VIX": "VIX",
    "BTC-USD": "Bitcoin",
    "^TNX": "10Y Treasury Proxy",
}


@dataclass
class SourceStatus:
    source: str
    status: str
    last_updated: datetime
    error: str = ""


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        frame = _ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False, raise_errors=False)
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _epoch_date(value) -> date | None:
    number = to_float(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number).date()
    except Exception:
        return None


def _headquarters(info: dict) -> str | None:
    city = str(info.get("city") or "").strip()
    state = str(info.get("state") or "").strip()
    country = str(info.get("country") or "").strip()
    parts = [part for part in (city, state, country) if part]
    return ", ".join(parts) if parts else None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    ticker = clean_ticker(symbol)
    if not ticker:
        return pd.DataFrame()
    return _history(ticker, period, interval)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_quote(symbol: str) -> dict:
    ticker = clean_ticker(symbol)
    updated = now_et()
    if not ticker:
        return {"ticker": "", "status": "Error", "error": "Invalid ticker", "last_updated": updated}
    info: dict = {}
    try:
        obj = _ticker(ticker)
        try:
            fast = getattr(obj, "fast_info", {}) or {}
            info.update(dict(fast))
        except Exception:
            pass
        try:
            full = obj.get_info()
            if isinstance(full, dict):
                info.update(full)
        except Exception:
            pass
        history = _history(ticker, "1y", "1d")
        close = pd.to_numeric(history.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
        volume = pd.to_numeric(history.get("Volume", pd.Series(dtype=float)), errors="coerce").dropna()
        price = to_float(info.get("lastPrice") or info.get("regularMarketPrice") or info.get("currentPrice"))
        if price is None and not close.empty:
            price = to_float(close.iloc[-1])
        previous_close = to_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        if previous_close is None and len(close) > 1:
            previous_close = to_float(close.iloc[-2])
        change = price - previous_close if price is not None and previous_close is not None else None
        change_pct = safe_div(change, previous_close, 100)
        avg_volume = to_float(info.get("averageVolume") or info.get("averageVolume10days"))
        if avg_volume is None and not volume.empty:
            avg_volume = to_float(volume.tail(30).mean())
        identity = get_company_identity(ticker)
        return {
            "ticker": ticker,
            "company_name": identity.get("company_name") or info.get("shortName") or info.get("longName") or ticker,
            "short_name": identity.get("short_name"),
            "price": price,
            "previous_close": previous_close,
            "daily_change": change,
            "daily_change_pct": change_pct,
            "volume": to_float(volume.iloc[-1]) if not volume.empty else to_float(info.get("volume")),
            "average_volume": avg_volume,
            "market_cap": to_float(info.get("marketCap")),
            "enterprise_value": to_float(info.get("enterpriseValue")),
            "total_debt": to_float(info.get("totalDebt")),
            "total_cash": to_float(info.get("totalCash")),
            "fifty_two_week_low": to_float(info.get("fiftyTwoWeekLow")),
            "fifty_two_week_high": to_float(info.get("fiftyTwoWeekHigh")),
            "sector": identity.get("sector") or info.get("sector"),
            "industry": identity.get("industry") or info.get("industry"),
            "exchange": identity.get("exchange"),
            "quote_type": identity.get("quote_type"),
            "business_summary": info.get("longBusinessSummary"),
            "shares_outstanding": to_float(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")),
            "beta": to_float(info.get("beta")),
            "price_to_book": to_float(info.get("priceToBook")),
            "trailing_pe": to_float(info.get("trailingPE")),
            "forward_pe": to_float(info.get("forwardPE")),
            "price_to_sales": to_float(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": to_float(info.get("enterpriseToEbitda")),
            "target_mean_price": to_float(info.get("targetMeanPrice")),
            "recommendation": info.get("recommendationKey"),
            "website": identity.get("website") or info.get("website"),
            "employees": to_float(info.get("fullTimeEmployees")),
            "headquarters": _headquarters(info),
            "ipo_date": info.get("ipoDate") or _epoch_date(info.get("firstTradeDateEpochUtc")),
            "next_earnings_date": _epoch_date(info.get("earningsTimestamp") or info.get("earningsTimestampStart")),
            "fiscal_year_end": _epoch_date(info.get("lastFiscalYearEnd")),
            "profile_url": identity.get("website") or info.get("website"),
            "domain": identity.get("domain"),
            "logo_url": identity.get("logo_url"),
            "logo_data_uri": identity.get("logo_data_uri"),
            "logo_status": identity.get("logo_status"),
            "logo_source": identity.get("logo_source"),
            "fallback_initials": identity.get("fallback_initials"),
            "status": "OK",
            "source": "Yahoo Finance/yfinance",
            "last_updated": updated,
        }
    except Exception as exc:
        return {"ticker": ticker, "status": "Error", "error": str(exc), "source": "Yahoo Finance/yfinance", "last_updated": updated}


def logo_url_from_info(info: dict) -> str | None:
    for key in ("logo_url", "logoUrl", "logoURL"):
        value = str(info.get(key) or "").strip()
        if value.startswith("http"):
            return value
    website = str(info.get("website") or "").strip().replace("https://", "").replace("http://", "").split("/")[0]
    if website:
        return f"https://logo.clearbit.com/{website}"
    return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_market_snapshot() -> tuple[pd.DataFrame, list[dict]]:
    rows = []
    statuses = []
    for symbol, name in MARKET_SYMBOLS.items():
        quote = fetch_quote(symbol)
        rows.append(
            {
                "Ticker": symbol,
                "Name": name,
                "Last": quote.get("price"),
                "Daily Move %": quote.get("daily_change_pct"),
                "Last Updated": quote.get("last_updated"),
                "Source": quote.get("source", "Yahoo Finance/yfinance"),
            }
        )
        statuses.append({"Source": f"Quote {symbol}", "Status": quote.get("status", "Unknown"), "Last Updated": quote.get("last_updated"), "Error": quote.get("error", "")})
    return pd.DataFrame(rows), statuses
