from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from data.market_data import get_market_session_et
from utils.formatting import clean_ticker, now_et, to_float


QUOTE_COLUMNS = [
    "ticker",
    "price",
    "bid",
    "ask",
    "change",
    "change_pct",
    "market_state",
    "timestamp",
    "last_refresh",
    "data_source",
    "status",
    "error",
]
EASTERN = ZoneInfo("America/New_York")


def _empty_quotes() -> pd.DataFrame:
    return pd.DataFrame(columns=QUOTE_COLUMNS)


def _normalize_tickers(tickers: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for value in tickers or []:
        symbol = clean_ticker(str(value))
        if symbol and symbol not in cleaned:
            cleaned.append(symbol)
    return cleaned


def _secret_or_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        secret_value = st.secrets.get(name, "")
    except Exception:
        secret_value = ""
    return str(secret_value or "").strip()


def _configured_provider() -> str:
    explicit = _secret_or_env("PINETERMINAL_QUOTES_PROVIDER") or _secret_or_env("LIVE_QUOTES_PROVIDER")
    if explicit:
        return explicit.casefold()
    if _secret_or_env("FINNHUB_API_KEY"):
        return "finnhub"
    if _secret_or_env("ALPACA_API_KEY") and _secret_or_env("ALPACA_API_SECRET"):
        return "alpaca"
    if _secret_or_env("POLYGON_API_KEY") or _secret_or_env("MASSIVE_API_KEY"):
        return "polygon"
    return "yfinance_delayed"


def _status_frame(tickers: list[str], source: str, status: str, error: str) -> pd.DataFrame:
    refreshed = now_et()
    market_state = str(get_market_session_et(refreshed).get("session") or "Unknown")
    return pd.DataFrame(
        [
            {
                "ticker": symbol,
                "price": None,
                "bid": None,
                "ask": None,
                "change": None,
                "change_pct": None,
                "market_state": market_state,
                "timestamp": None,
                "last_refresh": refreshed,
                "data_source": source,
                "status": status,
                "error": error,
            }
            for symbol in tickers
        ],
        columns=QUOTE_COLUMNS,
    )


def _timestamp_from_epoch(value: object) -> datetime | None:
    number = to_float(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, EASTERN)
    except Exception:
        return None


def _fetch_finnhub_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    token = _secret_or_env("FINNHUB_API_KEY")
    if not token:
        return _status_frame(list(tickers), "Finnhub", "Unavailable", "FINNHUB_API_KEY is not configured.")
    rows: list[dict[str, object]] = []
    refreshed = now_et()
    market_state = str(get_market_session_et(refreshed).get("session") or "Unknown")
    for symbol in tickers:
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": token},
                timeout=5,
            )
            if response.status_code == 429:
                rows.append(
                    {
                        "ticker": symbol,
                        "price": None,
                        "bid": None,
                        "ask": None,
                        "change": None,
                        "change_pct": None,
                        "market_state": market_state,
                        "timestamp": None,
                        "last_refresh": refreshed,
                        "data_source": "Finnhub",
                        "status": "Rate limited",
                        "error": "Provider rate limit reached.",
                    }
                )
                continue
            response.raise_for_status()
            payload = response.json() if response.content else {}
            price = to_float(payload.get("c"))
            rows.append(
                {
                    "ticker": symbol,
                    "price": price,
                    "bid": None,
                    "ask": None,
                    "change": to_float(payload.get("d")),
                    "change_pct": to_float(payload.get("dp")),
                    "market_state": market_state,
                    "timestamp": _timestamp_from_epoch(payload.get("t")),
                    "last_refresh": refreshed,
                    "data_source": "Finnhub",
                    "status": "OK" if price is not None else "Unavailable",
                    "error": "" if price is not None else "Missing latest price.",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "ticker": symbol,
                    "price": None,
                    "bid": None,
                    "ask": None,
                    "change": None,
                    "change_pct": None,
                    "market_state": market_state,
                    "timestamp": None,
                    "last_refresh": refreshed,
                    "data_source": "Finnhub",
                    "status": "Error",
                    "error": str(exc)[:180],
                }
            )
    return pd.DataFrame(rows, columns=QUOTE_COLUMNS)


def _fast_value(fast_info: object, *keys: str) -> object:
    for key in keys:
        try:
            value = fast_info[key]  # type: ignore[index]
        except Exception:
            value = getattr(fast_info, key, None)
        if value is not None:
            return value
    return None


def _latest_history_point(symbol: str) -> tuple[float | None, datetime | None]:
    try:
        history = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False, actions=False, raise_errors=False)
    except Exception:
        return None, None
    if not isinstance(history, pd.DataFrame) or history.empty or "Close" not in history:
        return None, None
    close = pd.to_numeric(history.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    if close.empty:
        return None, None
    timestamp = close.index[-1]
    try:
        if getattr(timestamp, "tzinfo", None) is None:
            timestamp = timestamp.tz_localize(EASTERN)
        else:
            timestamp = timestamp.tz_convert(EASTERN)
        stamp_value = timestamp.to_pydatetime()
    except Exception:
        stamp_value = None
    return to_float(close.iloc[-1]), stamp_value


def _fetch_yfinance_quotes_uncached(tickers: tuple[str, ...]) -> pd.DataFrame:
    refreshed = now_et()
    market_state = str(get_market_session_et(refreshed).get("session") or "Unknown")
    rows: list[dict[str, object]] = []
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            fast = getattr(ticker, "fast_info", {}) or {}
            price = to_float(
                _fast_value(fast, "last_price", "lastPrice", "regular_market_price", "regularMarketPrice", "last_close")
            )
            previous = to_float(
                _fast_value(fast, "previous_close", "previousClose", "regular_market_previous_close", "regularMarketPreviousClose")
            )
            history_price, history_time = _latest_history_point(symbol)
            if price is None:
                price = history_price
            change = price - previous if price is not None and previous is not None else None
            change_pct = (change / previous * 100) if change is not None and previous not in (None, 0) else None
            status = "OK" if price is not None else "Unavailable"
            rows.append(
                {
                    "ticker": symbol,
                    "price": price,
                    "bid": to_float(_fast_value(fast, "bid")),
                    "ask": to_float(_fast_value(fast, "ask")),
                    "change": change,
                    "change_pct": change_pct,
                    "market_state": market_state,
                    "timestamp": history_time,
                    "last_refresh": refreshed,
                    "data_source": "Yahoo Finance delayed fallback",
                    "status": status,
                    "error": "" if status == "OK" else "No quote fields returned.",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "ticker": symbol,
                    "price": None,
                    "bid": None,
                    "ask": None,
                    "change": None,
                    "change_pct": None,
                    "market_state": market_state,
                    "timestamp": None,
                    "last_refresh": refreshed,
                    "data_source": "Yahoo Finance delayed fallback",
                    "status": "Error",
                    "error": str(exc)[:180],
                }
            )
    return pd.DataFrame(rows, columns=QUOTE_COLUMNS)


@st.cache_data(ttl=5, show_spinner=False)
def _fetch_yfinance_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    return _fetch_yfinance_quotes_uncached(tickers)


def _provider_stub(tickers: tuple[str, ...], provider: str) -> pd.DataFrame:
    return _status_frame(
        list(tickers),
        provider.title(),
        "Unavailable",
        f"{provider.title()} quote provider is configured as a future real-time source, but this connector is not wired yet.",
    )


def fetch_latest_quotes(tickers: list[str], source: str | None = None) -> pd.DataFrame:
    """Return lightweight live/delayed quote rows for the ticker fragment only.

    API keys are read from environment variables or Streamlit secrets. The
    WebSocket/live provider should plug in here later so the rest of the app
    does not need to change.
    """

    symbols = tuple(_normalize_tickers(tickers))
    if not symbols:
        return _empty_quotes()

    provider = (source or _configured_provider()).casefold()
    if provider in {"finnhub", "finnhub.io"}:
        frame = _fetch_finnhub_quotes(symbols)
        if frame["price"].notna().any():
            return frame
        fallback = _fetch_yfinance_quotes(symbols)
        if not fallback.empty:
            return fallback
        return frame
    if provider in {"alpaca", "polygon", "massive"}:
        frame = _provider_stub(symbols, provider)
        fallback = _fetch_yfinance_quotes(symbols)
        if not fallback.empty:
            return fallback
        return frame
    return _fetch_yfinance_quotes(symbols)
