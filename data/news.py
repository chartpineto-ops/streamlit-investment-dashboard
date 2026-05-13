from __future__ import annotations

from datetime import datetime

import feedparser
import pandas as pd
import streamlit as st
import yfinance as yf

from utils.formatting import clean_ticker, now_et

RSS_FEEDS = [
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
]


def catalyst_tag(text: str) -> str:
    lowered = text.casefold()
    rules = {
        "Earnings": ("earnings", "eps", "revenue", "guidance"),
        "Analyst": ("analyst", "upgrade", "downgrade", "price target"),
        "Financing/Dilution": ("offering", "convertible", "dilution", "debt offering"),
        "M&A": ("acquire", "merger", "takeover", "deal"),
        "Regulation": ("sec", "doj", "regulator", "approval"),
        "Macro": ("fed", "inflation", "jobs", "rates", "tariff"),
        "Product": ("launch", "product", "contract", "partnership"),
    }
    for label, terms in rules.items():
        if any(term in lowered for term in terms):
            return label
    return "Other"


def _published_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return pd.to_datetime(value, unit="s", utc=True)
        except Exception:
            return value
    try:
        return pd.to_datetime(value, utc=True, errors="coerce")
    except Exception:
        return value


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(ticker: str, limit: int = 20) -> tuple[pd.DataFrame, list[dict]]:
    symbol = clean_ticker(ticker)
    rows = []
    statuses = []
    if symbol:
        try:
            news = yf.Ticker(symbol).news or []
            for item in news[:limit]:
                title = item.get("title") or item.get("content", {}).get("title")
                link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url")
                provider = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName")
                published = item.get("providerPublishTime") or item.get("content", {}).get("pubDate")
                rows.append({"Headline": title, "Source": provider or "Yahoo Finance", "Published": _published_value(published), "Ticker": symbol, "Scope": "Company", "Tag": catalyst_tag(str(title)), "Link": link, "Open": "Open" if link else ""})
            statuses.append({"Source": f"Yahoo Finance news {symbol}", "Status": "OK", "Last Updated": now_et(), "Error": ""})
        except Exception as exc:
            statuses.append({"Source": f"Yahoo Finance news {symbol}", "Status": "Error", "Last Updated": now_et(), "Error": str(exc)})
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[: max(3, limit // 3)]:
                title = getattr(entry, "title", "")
                scope = "Company" if symbol and symbol in title.upper() else "Macro"
                rows.append({"Headline": title, "Source": source, "Published": _published_value(getattr(entry, "published", "")), "Ticker": symbol or "", "Scope": scope, "Tag": catalyst_tag(title), "Link": getattr(entry, "link", ""), "Open": "Open" if getattr(entry, "link", "") else ""})
            statuses.append({"Source": source, "Status": "OK", "Last Updated": now_et(), "Error": ""})
        except Exception as exc:
            statuses.append({"Source": source, "Status": "Error", "Last Updated": now_et(), "Error": str(exc)})
    frame = pd.DataFrame(rows).dropna(subset=["Headline"]).drop_duplicates(subset=["Headline"])
    if not frame.empty and "Published" in frame:
        frame = frame.sort_values("Published", ascending=False, na_position="last")
    frame = frame.head(limit)
    return frame, statuses
