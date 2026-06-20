from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from data.market_universe import market_universe
from data.social import SOCIAL_WARNING, calculate_social_scores, fetch_social_mentions
from utils.formatting import clean_ticker, now_et, to_float


SOCIAL_FIELDS = [
    "ticker",
    "company_name",
    "source",
    "mention_count",
    "mention_change_pct",
    "sentiment_score",
    "sentiment_label",
    "bullish_count",
    "bearish_count",
    "price_change_pct",
    "volume_change_pct",
    "theme",
    "confidence_score",
    "last_updated",
]

THEME_TICKERS = {
    "AI": {"NVDA", "MSFT", "AVGO", "MRVL", "ANET", "CRWV", "AMD", "PLTR"},
    "Semiconductors": {"NVDA", "MRVL", "AVGO", "AMD", "TSM", "MU", "SMH", "INTC"},
    "Quantum": {"IONQ", "RGTI", "QBTS", "QUBT", "IBM", "GOOGL"},
    "Crypto": {"FBTC", "COIN", "MSTR", "IBIT", "GBTC", "BITO", "RIOT", "MARA"},
    "Nuclear / Uranium": {"CEG", "VST", "CCJ", "BWXT", "SMR", "OKLO", "UEC"},
    "Rare Earths": {"MP", "UUUU", "REMX", "LAC", "ALB", "FCX"},
    "Defense": {"LMT", "RTX", "NOC", "GD", "AVAV", "KTOS", "AMPX"},
    "Biotech": {"MRNA", "BNTX", "REGN", "VRTX", "BIIB", "GILD"},
    "Meme / Speculation": {"GME", "AMC", "BB", "KOSS", "RIVN", "LCID", "RGTI", "QUBT"},
    "Consumer": {"AMZN", "TSLA", "WMT", "COST", "HD", "NKE", "SBUX"},
    "Fintech": {"PYPL", "SQ", "HOOD", "COIN", "SOFI", "AFRM"},
    "Energy": {"XOM", "CVX", "SLB", "OXY", "EOG", "XLE"},
    "EV / Battery": {"TSLA", "RIVN", "LCID", "AMPX", "QS", "ALB", "LAC"},
}

THEME_KEYWORDS = {
    "AI": ("ai", "data center", "server", "blackwell"),
    "Semiconductors": ("chip", "semiconductor", "custom silicon"),
    "Quantum": ("quantum",),
    "Crypto": ("bitcoin", "crypto", "etf inflows"),
    "Nuclear / Uranium": ("nuclear", "uranium", "power"),
    "Rare Earths": ("rare earth", "critical minerals"),
    "Defense": ("defense", "drone", "contracts"),
    "Biotech": ("biotech", "fda", "trial"),
    "Meme / Speculation": ("short squeeze", "retail speculation", "meme"),
    "Consumer": ("consumer", "retail"),
    "Fintech": ("fintech", "payments"),
    "Energy": ("energy", "oil", "gas"),
    "EV / Battery": ("ev", "battery", "lithium"),
}

THEME_DESCRIPTIONS = {
    "AI": "AI infrastructure and compute demand are driving attention.",
    "Semiconductors": "Chip supply, custom silicon, and AI hardware remain active narratives.",
    "Quantum": "Quantum names are drawing speculative attention around funding and milestones.",
    "Crypto": "Digital asset flows and bitcoin beta are shaping social discussion.",
    "Nuclear / Uranium": "Power demand and nuclear capacity narratives are lifting attention.",
    "Rare Earths": "Critical-minerals policy and supply-chain risk are in focus.",
    "Defense": "Defense spending, drones, and procurement headlines are driving interest.",
    "Biotech": "Clinical, regulatory, and pipeline catalysts are driving discussion.",
    "Meme / Speculation": "Retail speculation and squeeze dynamics are elevated.",
    "Consumer": "Consumer demand, spending, and brand momentum are in focus.",
    "Fintech": "Payments, brokerage, and crypto-adjacent fintech narratives are active.",
    "Energy": "Energy prices and cyclicals are shaping social attention.",
    "EV / Battery": "EV demand, batteries, lithium, and energy density are active themes.",
}


def _theme_for_row(row: pd.Series | dict) -> str:
    ticker = clean_ticker(str(row.get("ticker") or ""))
    for theme, tickers in THEME_TICKERS.items():
        if ticker in tickers:
            return theme
    narratives = " ".join(str(item) for item in (row.get("top_social_narratives") or []))
    lowered = narratives.casefold()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return theme
    return "Other"


def _clean_symbols(symbols: Iterable[str] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    for value in symbols or []:
        symbol = clean_ticker(str(value))
        if symbol and symbol not in cleaned and not symbol.startswith("^") and "=" not in symbol and not symbol.endswith("-USD"):
            cleaned.append(symbol)
    return tuple(cleaned)


def _default_symbols() -> tuple[str, ...]:
    return tuple(market_universe(include_etfs=False)[:120])


def _normalize_social_frame(frame: pd.DataFrame, status: dict | None = None) -> pd.DataFrame:
    if frame is None or frame.empty:
        empty = pd.DataFrame(columns=SOCIAL_FIELDS)
        empty.attrs["status"] = status or {}
        return empty
    normalized = frame.copy()
    normalized["company_name"] = normalized.get("company", normalized.get("company_name", normalized.get("ticker", "")))
    normalized["mention_count"] = pd.to_numeric(normalized.get("mentions_today"), errors="coerce").fillna(0)
    normalized["mention_change_pct"] = pd.to_numeric(normalized.get("mention_change_24h_pct"), errors="coerce").fillna(0)
    normalized["sentiment_score"] = (
        pd.to_numeric(normalized.get("bullish_pct"), errors="coerce").fillna(0)
        - pd.to_numeric(normalized.get("bearish_pct"), errors="coerce").fillna(0)
    )
    normalized["bullish_count"] = (normalized["mention_count"] * pd.to_numeric(normalized.get("bullish_pct"), errors="coerce").fillna(0) / 100).round()
    normalized["bearish_count"] = (normalized["mention_count"] * pd.to_numeric(normalized.get("bearish_pct"), errors="coerce").fillna(0) / 100).round()
    normalized["price_change_pct"] = pd.to_numeric(normalized.get("price_move_pct"), errors="coerce").fillna(0)
    normalized["volume_change_pct"] = (pd.to_numeric(normalized.get("volume_vs_30d_avg"), errors="coerce").fillna(1) - 1) * 100
    normalized["theme"] = normalized.apply(_theme_for_row, axis=1)
    normalized["confidence_score"] = (
        100
        - pd.to_numeric(normalized.get("risk_penalty"), errors="coerce").fillna(0)
        + pd.to_numeric(normalized.get("mention_zscore"), errors="coerce").fillna(0).clip(lower=0, upper=3) * 5
    ).clip(0, 100)
    if "last_updated" not in normalized:
        normalized["last_updated"] = now_et()
    if "source" not in normalized:
        normalized["source"] = (status or {}).get("Source", "Social provider")
    normalized.attrs["status"] = status or {}
    return normalized


@st.cache_data(ttl=300, show_spinner=False)
def fetch_social_momentum() -> pd.DataFrame:
    raw, status = fetch_social_mentions(_default_symbols(), "auto")
    scored = calculate_social_scores(raw)
    return _normalize_social_frame(scored, status)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_social_trending_tickers() -> pd.DataFrame:
    frame = fetch_social_momentum()
    return frame.sort_values("mention_count", ascending=False).reset_index(drop=True) if not frame.empty else frame


@st.cache_data(ttl=300, show_spinner=False)
def fetch_social_sentiment_leaders() -> pd.DataFrame:
    frame = fetch_social_momentum()
    if frame.empty:
        return frame
    reliable = frame[(frame["mention_count"] >= 250) | (frame["confidence_score"] >= 45)].copy()
    if reliable.empty:
        reliable = frame.copy()
    reliable["sentiment_abs"] = pd.to_numeric(reliable["sentiment_score"], errors="coerce").abs()
    return reliable.sort_values(["sentiment_abs", "mention_count"], ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_social_theme_trends() -> pd.DataFrame:
    frame = fetch_social_momentum()
    if frame.empty:
        return pd.DataFrame(columns=["theme", "top_tickers", "total_mentions", "average_sentiment", "average_price_move", "description", "last_updated"])
    rows = []
    for theme, group in frame.groupby("theme"):
        if theme == "Other" and len(group) < 3:
            continue
        top = group.sort_values("mention_count", ascending=False).head(5)
        rows.append(
            {
                "theme": theme,
                "top_tickers": ", ".join(top["ticker"].astype(str).tolist()),
                "total_mentions": float(pd.to_numeric(group["mention_count"], errors="coerce").sum()),
                "average_sentiment": float(pd.to_numeric(group["sentiment_score"], errors="coerce").mean()),
                "average_price_move": float(pd.to_numeric(group["price_change_pct"], errors="coerce").mean()),
                "description": THEME_DESCRIPTIONS.get(theme, "Social discussion is broad and mixed across this group."),
                "last_updated": group["last_updated"].iloc[0] if "last_updated" in group else now_et(),
            }
        )
    return pd.DataFrame(rows).sort_values("total_mentions", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker_social_snapshot(ticker: str) -> pd.DataFrame:
    symbol = clean_ticker(ticker)
    if not symbol:
        return pd.DataFrame()
    raw, status = fetch_social_mentions((symbol,), "auto")
    scored = calculate_social_scores(raw)
    frame = _normalize_social_frame(scored, status)
    if frame.empty:
        return frame
    return frame[frame["ticker"].astype(str).str.upper() == symbol].reset_index(drop=True)
