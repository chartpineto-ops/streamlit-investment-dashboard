from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from data.filings import fetch_sec_filings
from data.financials import load_latest_company_financials
from data.market_data import fetch_history, get_market_session_et
from data.market_movers import get_whole_market_movers
from pineterminal.live_data import load_dashboard_analysis
from services.economic_data_service import fetch_macro_dashboard
from services.competitive_intelligence_service import fetch_competitive_intelligence
from services.live_quotes import fetch_latest_quotes
from services.news_service import fetch_company_news, fetch_market_headlines
from services.social_sentiment_service import (
    fetch_social_momentum,
    fetch_social_theme_trends,
    fetch_ticker_social_snapshot,
)
from signals.signal_engine import compute_signal
from storage.watchlist import list_watchlist
from utils.formatting import clean_ticker, now_et


BENCHMARKS = ["SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "USO", "BTC-USD"]
SECTOR_ETFS = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLV", "XLB", "XLRE", "XLP", "XLU"]


@dataclass
class Result:
    value: Any
    status: str = "OK"
    error: str = ""


def safe_call(fn: Callable[..., Any], *args: Any, fallback: Any = None, **kwargs: Any) -> Result:
    try:
        return Result(fn(*args, **kwargs))
    except Exception as exc:
        return Result(fallback, "Error", str(exc)[:240])


def tape_symbols(selected_ticker: str = "") -> list[str]:
    symbols = list(BENCHMARKS)
    watch = safe_call(list_watchlist, fallback=pd.DataFrame()).value
    if isinstance(watch, pd.DataFrame) and not watch.empty:
        symbols.extend(watch.get("ticker", pd.Series(dtype=str)).astype(str).tolist())
    symbol = clean_ticker(selected_ticker)
    if symbol:
        symbols.insert(0, symbol)
    return list(dict.fromkeys(item for item in symbols if item))[:18]


def market_quotes(selected_ticker: str = "") -> pd.DataFrame:
    result = safe_call(fetch_latest_quotes, tape_symbols(selected_ticker), fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def benchmark_quotes() -> pd.DataFrame:
    result = safe_call(fetch_latest_quotes, BENCHMARKS, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def sector_quotes() -> pd.DataFrame:
    result = safe_call(fetch_latest_quotes, SECTOR_ETFS, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def movers_packet() -> dict:
    result = safe_call(
        get_whole_market_movers,
        min_price=2.0,
        min_volume=750_000,
        max_universe_size=1_000,
        include_etfs=False,
        fallback={},
    )
    return result.value if isinstance(result.value, dict) else {}


def market_news() -> pd.DataFrame:
    result = safe_call(fetch_market_headlines, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def social_market() -> pd.DataFrame:
    result = safe_call(fetch_social_momentum, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def social_themes() -> pd.DataFrame:
    result = safe_call(fetch_social_theme_trends, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def macro_dashboard() -> pd.DataFrame:
    result = safe_call(fetch_macro_dashboard, fallback=pd.DataFrame())
    return result.value if isinstance(result.value, pd.DataFrame) else pd.DataFrame()


def security_packet(ticker: str) -> dict[str, Any]:
    symbol = clean_ticker(ticker)
    if not symbol:
        return {"ticker": "", "status": "Error", "error": "Invalid ticker"}
    analysis = safe_call(load_dashboard_analysis, symbol).value
    financials_result = safe_call(load_latest_company_financials, symbol, fallback={})
    signal_result = safe_call(compute_signal, symbol, fallback={})
    history_result = safe_call(fetch_history, symbol, period="2y", interval="1d", fallback=pd.DataFrame())
    news_result = safe_call(fetch_company_news, symbol, fallback=pd.DataFrame())
    social_result = safe_call(fetch_ticker_social_snapshot, symbol, fallback=pd.DataFrame())
    filings_result = safe_call(fetch_sec_filings, symbol, fallback=(pd.DataFrame(), {}))
    filings, filing_status = filings_result.value if isinstance(filings_result.value, tuple) else (pd.DataFrame(), {})
    company = getattr(analysis, "company", None)
    peer_result = safe_call(
        fetch_competitive_intelligence,
        symbol,
        str(getattr(company, "sector", "") or ""),
        str(getattr(company, "industry", "") or ""),
        tuple(getattr(company, "themes", ()) or ()),
        fallback=(pd.DataFrame(), {}),
    )
    peers, peer_status = peer_result.value if isinstance(peer_result.value, tuple) else (pd.DataFrame(), {})
    return {
        "ticker": symbol,
        "analysis": analysis,
        "financials": financials_result.value if isinstance(financials_result.value, dict) else {},
        "signal": signal_result.value if isinstance(signal_result.value, dict) else {},
        "history": history_result.value if isinstance(history_result.value, pd.DataFrame) else pd.DataFrame(),
        "news": news_result.value if isinstance(news_result.value, pd.DataFrame) else pd.DataFrame(),
        "social": social_result.value if isinstance(social_result.value, pd.DataFrame) else pd.DataFrame(),
        "filings": filings if isinstance(filings, pd.DataFrame) else pd.DataFrame(),
        "filing_status": filing_status if isinstance(filing_status, dict) else {},
        "peers": peers if isinstance(peers, pd.DataFrame) else pd.DataFrame(),
        "peer_status": peer_status if isinstance(peer_status, dict) else {},
        "status": "OK" if analysis is not None else "Partial",
        "error": financials_result.error or signal_result.error,
        "loaded_at": now_et(),
    }


def market_session() -> dict:
    result = safe_call(get_market_session_et, fallback={})
    return result.value if isinstance(result.value, dict) else {}
