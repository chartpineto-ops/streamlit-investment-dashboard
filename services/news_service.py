from __future__ import annotations

from datetime import timedelta
from typing import Iterable

import pandas as pd
import requests
import streamlit as st

from data.market_news import NewsItem, market_news_provider
from utils.formatting import clean_ticker, now_et
from utils.secrets import secret_or_env


NEWS_COLUMNS = [
    "headline",
    "source",
    "published_at",
    "ticker",
    "summary",
    "url",
    "sentiment",
    "data_source",
    "last_refresh",
]


def _empty_news() -> pd.DataFrame:
    return pd.DataFrame(columns=NEWS_COLUMNS)


def _secret_or_env(name: str) -> str:
    return secret_or_env(name)


def _configured_provider() -> str:
    explicit = _secret_or_env("PINETERMINAL_NEWS_PROVIDER") or _secret_or_env("NEWS_PROVIDER")
    if explicit:
        return explicit.casefold()
    if _secret_or_env("FINNHUB_API_KEY"):
        return "finnhub"
    if _secret_or_env("BENZINGA_API_KEY"):
        return "benzinga"
    if _secret_or_env("MARKETAUX_API_KEY"):
        return "marketaux"
    if _secret_or_env("POLYGON_API_KEY") or _secret_or_env("MASSIVE_API_KEY"):
        return "polygon"
    if _secret_or_env("ALPHA_VANTAGE_API_KEY"):
        return "alpha_vantage"
    return "demo"


def _sentiment_from_impact(value: str) -> str:
    lowered = str(value or "").casefold()
    if "positive" in lowered:
        return "Bullish"
    if "negative" in lowered:
        return "Bearish"
    if "mixed" in lowered:
        return "Mixed"
    return "Neutral"


def _news_items_to_frame(items: Iterable[NewsItem], data_source: str) -> pd.DataFrame:
    refreshed = now_et()
    rows = []
    for item in items:
        tickers = item.tickers or item.readThroughTickers or [""]
        for ticker in tickers[:3]:
            rows.append(
                {
                    "headline": item.headline,
                    "source": item.source,
                    "published_at": item.timestamp,
                    "ticker": clean_ticker(ticker),
                    "summary": item.summary or item.whyItMatters,
                    "url": item.url,
                    "sentiment": _sentiment_from_impact(item.impact),
                    "data_source": data_source,
                    "last_refresh": refreshed,
                }
            )
    frame = pd.DataFrame(rows, columns=NEWS_COLUMNS)
    if frame.empty:
        return _empty_news()
    return frame.sort_values("published_at", ascending=False).reset_index(drop=True)


def _demo_market_headlines() -> pd.DataFrame:
    return _news_items_to_frame(market_news_provider().getMarketNews(), "Provider not configured - demo news fallback")


def _demo_company_news(ticker: str) -> pd.DataFrame:
    symbol = clean_ticker(ticker)
    if not symbol:
        return _empty_news()
    return _news_items_to_frame(market_news_provider().getTickerNews(symbol), "Provider not configured - demo news fallback")


def _finnhub_request(path: str, params: dict[str, object]) -> list[dict]:
    token = _secret_or_env("FINNHUB_API_KEY")
    if not token:
        return []
    response = requests.get(
        f"https://finnhub.io/api/v1/{path.lstrip('/')}",
        params={**params, "token": token},
        timeout=8,
    )
    if response.status_code == 429:
        raise RuntimeError("Finnhub rate limit reached.")
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _finnhub_rows(items: list[dict], ticker: str = "") -> pd.DataFrame:
    refreshed = now_et()
    rows = []
    for item in items:
        published_at = pd.to_datetime(item.get("datetime"), unit="s", errors="coerce")
        if pd.isna(published_at):
            published_at = refreshed
        rows.append(
            {
                "headline": str(item.get("headline") or "").strip(),
                "source": str(item.get("source") or "Finnhub").strip(),
                "published_at": published_at,
                "ticker": clean_ticker(ticker or item.get("related") or ""),
                "summary": str(item.get("summary") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "sentiment": "Neutral",
                "data_source": "Finnhub",
                "last_refresh": refreshed,
            }
        )
    frame = pd.DataFrame(rows, columns=NEWS_COLUMNS)
    if frame.empty:
        return _empty_news()
    return frame[frame["headline"].astype(str).str.len() > 0].sort_values("published_at", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_company_news(ticker: str) -> pd.DataFrame:
    """Fetch company-specific headlines without AI summarization or scraping."""

    symbol = clean_ticker(ticker)
    if not symbol:
        return _empty_news()
    provider = _configured_provider()
    if provider == "finnhub":
        try:
            end = now_et().date()
            start = end - timedelta(days=7)
            frame = _finnhub_rows(
                _finnhub_request("company-news", {"symbol": symbol, "from": start.isoformat(), "to": end.isoformat()}),
                ticker=symbol,
            )
            return frame if not frame.empty else _demo_company_news(symbol)
        except Exception:
            return _demo_company_news(symbol)
    return _demo_company_news(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_headlines() -> pd.DataFrame:
    """Fetch market-wide headlines from a configured provider or demo fallback."""

    provider = _configured_provider()
    if provider == "finnhub":
        try:
            frame = _finnhub_rows(_finnhub_request("news", {"category": "general"}))
            return frame if not frame.empty else _demo_market_headlines()
        except Exception:
            return _demo_market_headlines()
    return _demo_market_headlines()
