from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

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
ET_TZ = ZoneInfo("America/New_York")


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


def _intraday_prepost(symbol: str, interval: str = "1m") -> pd.DataFrame:
    try:
        frame = _ticker(symbol).history(
            period="5d",
            interval=interval,
            prepost=True,
            auto_adjust=False,
            actions=False,
            raise_errors=False,
        )
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _as_et(value: datetime | None = None) -> datetime:
    raw = value or now_et()
    if raw.tzinfo is None:
        return raw.replace(tzinfo=ET_TZ)
    return raw.astimezone(ET_TZ)


def _epoch_datetime(value) -> datetime | None:
    number = to_float(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, ET_TZ)
    except Exception:
        return None


def get_market_session_et(moment: datetime | None = None) -> dict:
    current = _as_et(moment)
    weekday = current.weekday()
    clock = current.time()
    if weekday >= 5:
        session = "Closed"
        label = "CLOSED"
    elif time(4, 0) <= clock < time(9, 30):
        session = "Pre-Market"
        label = "PRE"
    elif time(9, 30) <= clock < time(16, 0):
        session = "Regular Market"
        label = "LIVE"
    elif time(16, 0) <= clock < time(20, 0):
        session = "After Hours"
        label = "AH"
    else:
        session = "Closed"
        label = "CLOSED"
    return {
        "session": session,
        "label": label,
        "timestamp": current,
        "is_open": label in {"PRE", "LIVE", "AH"},
        "timezone": "America/New_York",
    }


def _normalize_intraday_index(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        return pd.DataFrame()
    local = frame.copy()
    try:
        if local.index.tz is None:
            local.index = local.index.tz_localize("UTC").tz_convert(ET_TZ)
        else:
            local.index = local.index.tz_convert(ET_TZ)
    except Exception:
        return pd.DataFrame()
    return local


def _latest_intraday_window(frame: pd.DataFrame, session_date: date, start: time, end: time, include_end: bool = False) -> tuple[float | None, datetime | None, float | None]:
    local = _normalize_intraday_index(frame)
    if local.empty or "Close" not in local:
        return None, None, None
    mask = []
    for stamp in local.index:
        current_time = stamp.time()
        in_window = start <= current_time <= end if include_end else start <= current_time < end
        mask.append(stamp.date() == session_date and in_window)
    window = local.loc[mask]
    close = pd.to_numeric(window.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    if close.empty:
        return None, None, None
    latest_index = close.index[-1]
    volume = None
    if "Volume" in window:
        volume = to_float(window.loc[latest_index, "Volume"])
    return to_float(close.iloc[-1]), latest_index.to_pydatetime(), volume


def _latest_intraday_price(frame: pd.DataFrame) -> tuple[float | None, datetime | None, float | None]:
    local = _normalize_intraday_index(frame)
    if local.empty or "Close" not in local:
        return None, None, None
    close = pd.to_numeric(local.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    if close.empty:
        return None, None, None
    latest_index = close.index[-1]
    volume = None
    if "Volume" in local:
        volume = to_float(local.loc[latest_index, "Volume"])
    return to_float(close.iloc[-1]), latest_index.to_pydatetime(), volume


def _quote_info(symbol: str) -> dict:
    info: dict = {}
    try:
        obj = _ticker(symbol)
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
    except Exception:
        pass
    return info


def _first_float(mapping: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = to_float(mapping.get(key))
        if value is not None:
            return value
    return None


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
            "revenue_growth": to_float(info.get("revenueGrowth")),
            "earnings_growth": to_float(info.get("earningsGrowth")),
            "gross_margin": to_float(info.get("grossMargins")),
            "operating_margin": to_float(info.get("operatingMargins")),
            "free_cash_flow": to_float(info.get("freeCashflow")),
            "return_on_equity": to_float(info.get("returnOnEquity")),
            "debt_to_equity": to_float(info.get("debtToEquity")),
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


@st.cache_data(ttl=45, show_spinner=False)
def get_extended_hours_quote(symbol: str) -> dict:
    ticker = clean_ticker(symbol)
    updated = now_et()
    session = get_market_session_et(updated)
    if not ticker:
        return {
            "ticker": "",
            "company_name": "N/A",
            "regular_price": None,
            "previous_close": None,
            "regular_change_pct": None,
            "premarket_price": None,
            "premarket_change_pct": None,
            "afterhours_price": None,
            "afterhours_change_pct": None,
            "latest_price": None,
            "latest_session": session["label"],
            "latest_session_name": session["session"],
            "latest_timestamp": updated,
            "volume": None,
            "source": "Yahoo Finance/yfinance",
            "source_status": "Invalid ticker",
            "error": "Invalid ticker",
        }
    try:
        info = _quote_info(ticker)
        identity = get_company_identity(ticker)
        intraday = _intraday_prepost(ticker, "1m")
        if intraday.empty:
            intraday = _intraday_prepost(ticker, "5m")
        regular_price = _first_float(info, ("regularMarketPrice", "currentPrice", "lastPrice", "last_price"))
        previous_close = _first_float(info, ("regularMarketPreviousClose", "previousClose", "previous_close"))
        premarket_price = _first_float(info, ("preMarketPrice", "premarketPrice", "pre_market_price"))
        afterhours_price = _first_float(info, ("postMarketPrice", "afterHoursPrice", "post_market_price"))
        session_date = _as_et(updated).date()
        pre_window_price, pre_window_ts, pre_window_volume = _latest_intraday_window(intraday, session_date, time(4, 0), time(9, 30))
        regular_window_price, regular_window_ts, regular_window_volume = _latest_intraday_window(intraday, session_date, time(9, 30), time(16, 0), include_end=True)
        after_window_price, after_window_ts, after_window_volume = _latest_intraday_window(intraday, session_date, time(16, 0), time(20, 0), include_end=True)
        latest_intraday, latest_intraday_ts, latest_intraday_volume = _latest_intraday_price(intraday)
        if premarket_price is None:
            premarket_price = pre_window_price
        if afterhours_price is None:
            afterhours_price = after_window_price
        if regular_price is None:
            regular_price = regular_window_price if regular_window_price is not None else latest_intraday
        if previous_close is None:
            daily = _history(ticker, "7d", "1d")
            close = pd.to_numeric(daily.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
            if len(close) > 1:
                previous_close = to_float(close.iloc[-2])
            elif len(close) == 1 and regular_price is not None:
                previous_close = to_float(close.iloc[-1])
        premarket_ts = _epoch_datetime(info.get("preMarketTime")) or pre_window_ts
        afterhours_ts = _epoch_datetime(info.get("postMarketTime")) or after_window_ts
        regular_ts = _epoch_datetime(info.get("regularMarketTime")) or regular_window_ts
        latest_price = regular_price
        latest_ts = regular_ts or latest_intraday_ts or updated
        latest_volume = _first_float(info, ("regularMarketVolume", "volume", "lastVolume"))
        if latest_volume is None:
            latest_volume = regular_window_volume or latest_intraday_volume
        if session["label"] == "PRE" and premarket_price is not None:
            latest_price = premarket_price
            latest_ts = premarket_ts or latest_ts
            latest_volume = pre_window_volume or latest_volume
        elif session["label"] == "AH" and afterhours_price is not None:
            latest_price = afterhours_price
            latest_ts = afterhours_ts or latest_ts
            latest_volume = after_window_volume or latest_volume
        elif session["label"] == "LIVE" and latest_intraday is not None:
            latest_price = latest_intraday
            latest_ts = latest_intraday_ts or latest_ts
            latest_volume = latest_intraday_volume or latest_volume
        elif session["label"] == "CLOSED":
            if afterhours_price is not None and afterhours_ts and afterhours_ts.date() == session_date:
                latest_price = afterhours_price
                latest_ts = afterhours_ts
                latest_volume = after_window_volume or latest_volume
            elif latest_intraday is not None:
                latest_price = latest_intraday
                latest_ts = latest_intraday_ts or latest_ts
                latest_volume = latest_intraday_volume or latest_volume
        regular_change_pct = safe_div((regular_price - previous_close) if regular_price is not None and previous_close is not None else None, previous_close, 100)
        premarket_change_pct = safe_div((premarket_price - previous_close) if premarket_price is not None and previous_close is not None else None, previous_close, 100)
        afterhours_change_pct = safe_div((afterhours_price - previous_close) if afterhours_price is not None and previous_close is not None else None, previous_close, 100)
        status = "OK" if regular_price is not None and previous_close is not None else "Partial"
        if premarket_price is None and afterhours_price is None and session["label"] in {"PRE", "AH"}:
            status = "Extended-hours unavailable"
        return {
            "ticker": ticker,
            "company_name": identity.get("company_name") or info.get("shortName") or info.get("longName") or ticker,
            "logo_url": identity.get("logo_url"),
            "logo_data_uri": identity.get("logo_data_uri"),
            "fallback_initials": identity.get("fallback_initials"),
            "regular_price": regular_price,
            "previous_close": previous_close,
            "regular_change_pct": regular_change_pct,
            "premarket_price": premarket_price,
            "premarket_change_pct": premarket_change_pct,
            "afterhours_price": afterhours_price,
            "afterhours_change_pct": afterhours_change_pct,
            "latest_price": latest_price,
            "bid": _first_float(info, ("bid", "regularMarketBid")),
            "ask": _first_float(info, ("ask", "regularMarketAsk")),
            "latest_session": session["label"],
            "latest_session_name": session["session"],
            "latest_timestamp": _as_et(latest_ts),
            "volume": latest_volume,
            "source": "Yahoo Finance/yfinance prepost intraday",
            "source_status": status,
            "last_updated": updated,
        }
    except Exception as exc:
        return {
            "ticker": ticker,
            "company_name": ticker,
            "regular_price": None,
            "previous_close": None,
            "regular_change_pct": None,
            "premarket_price": None,
            "premarket_change_pct": None,
            "afterhours_price": None,
            "afterhours_change_pct": None,
            "latest_price": None,
            "latest_session": session["label"],
            "latest_session_name": session["session"],
            "latest_timestamp": updated,
            "volume": None,
            "source": "Yahoo Finance/yfinance prepost intraday",
            "source_status": "Source error",
            "error": str(exc),
            "last_updated": updated,
        }


@st.cache_data(ttl=45, show_spinner=False)
def get_extended_hours_table(symbols: tuple[str, ...]) -> pd.DataFrame:
    seen: set[str] = set()
    rows: list[dict] = []
    for raw in symbols:
        ticker = clean_ticker(raw)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        rows.append(get_extended_hours_quote(ticker))
    return pd.DataFrame(rows)


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
