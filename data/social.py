from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from math import sqrt
from typing import Iterable

import pandas as pd
import streamlit as st

from data.market_data import fetch_quote
from data.market_universe import market_universe
from utils.formatting import clean_ticker, now_et, to_float


SOCIAL_WARNING = (
    "Social momentum is an attention signal, not a standalone investment thesis. "
    "Confirm with price, volume, catalyst, fundamentals, and risk controls."
)


def _secret(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        secrets = getattr(st, "secrets", {})
        if name in secrets:
            return str(secrets[name])
        social = secrets.get("social", {}) if hasattr(secrets, "get") else {}
        if isinstance(social, dict) and name in social:
            return str(social[name])
    except Exception:
        return None
    return None


def _stable_int(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _as_symbols(symbols: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in symbols or []:
        symbol = clean_ticker(value)
        if symbol and symbol not in seen and not symbol.startswith("^") and "=" not in symbol and not symbol.endswith("-USD"):
            seen.add(symbol)
            output.append(symbol)
    return output


@dataclass(frozen=True)
class SocialProviderStatus:
    source: str
    status: str
    last_updated: object
    message: str


class SocialMomentumProvider:
    source = "provider"

    def is_configured(self) -> bool:
        return False

    def fetch(self, symbols: list[str]) -> tuple[pd.DataFrame, SocialProviderStatus]:
        return pd.DataFrame(), SocialProviderStatus(self.source, "Unavailable", now_et(), "Provider is not configured.")


class StocktwitsProvider(SocialMomentumProvider):
    source = "Stocktwits"

    def is_configured(self) -> bool:
        return bool(_secret("STOCKTWITS_API_KEY"))


class RedditProvider(SocialMomentumProvider):
    source = "Reddit"

    def is_configured(self) -> bool:
        return bool(_secret("REDDIT_CLIENT_ID") and _secret("REDDIT_CLIENT_SECRET"))


class FinBrainProvider(SocialMomentumProvider):
    source = "FinBrain"

    def is_configured(self) -> bool:
        return bool(_secret("FINBRAIN_API_KEY"))


class DemoSocialProvider(SocialMomentumProvider):
    source = "Demo Data"

    def is_configured(self) -> bool:
        return True

    def fetch(self, symbols: list[str]) -> tuple[pd.DataFrame, SocialProviderStatus]:
        rows = [_mock_social_row(symbol) for symbol in symbols]
        status = SocialProviderStatus(
            self.source,
            "Demo Data",
            now_et(),
            "No configured social API credentials were found; using deterministic demo data.",
        )
        return pd.DataFrame(rows), status


PROVIDERS: dict[str, SocialMomentumProvider] = {
    "stocktwits": StocktwitsProvider(),
    "reddit": RedditProvider(),
    "finbrain": FinBrainProvider(),
    "demo": DemoSocialProvider(),
}


def _quote_snapshot(symbol: str) -> dict:
    if str(os.getenv("SOCIAL_FETCH_QUOTES", "")).strip().lower() not in {"1", "true", "yes"}:
        return {"ticker": symbol}
    try:
        return fetch_quote(symbol)
    except Exception:
        return {"ticker": symbol}


def _mock_social_row(symbol: str) -> dict[str, object]:
    seed = _stable_int(symbol, now_et().date().isoformat())
    prior_seed = _stable_int(symbol, "prior")
    quote = _quote_snapshot(symbol)
    market_cap = to_float(quote.get("market_cap"))
    price_move = to_float(quote.get("daily_change_pct"))
    if price_move is None:
        price_move = ((seed % 1800) / 100) - 9
    volume = to_float(quote.get("volume")) or 0.0
    average_volume = to_float(quote.get("average_volume")) or max(1.0, volume / (0.7 + (seed % 130) / 100))
    relative_volume = volume / average_volume if average_volume else 1.0
    base_mentions = 160 + (seed % 16_000)
    if market_cap and market_cap > 200_000_000_000:
        base_mentions += 12_000
    elif market_cap and market_cap < 2_000_000_000:
        base_mentions += 1_800
    mentions_avg_30d = max(60.0, base_mentions * (0.45 + (prior_seed % 90) / 100))
    std_30d = max(24.0, mentions_avg_30d * (0.18 + (seed % 24) / 100))
    spike = 0.72 + (seed % 210) / 100
    mentions_today = int(max(12, mentions_avg_30d * spike))
    mentions_yesterday = int(max(10, mentions_avg_30d * (0.52 + (prior_seed % 130) / 100)))
    mentions_7d_avg = int(max(10, mentions_avg_30d * (0.62 + (_stable_int(symbol, "7d") % 100) / 100)))
    bullish_7d = 34 + (_stable_int(symbol, "bull7") % 34)
    sentiment_tilt = min(26, max(-26, price_move * 2.1 + ((_stable_int(symbol, "tilt") % 18) - 9)))
    bullish_pct = int(_clip(bullish_7d + sentiment_tilt, 12, 88))
    bearish_pct = int(_clip(100 - bullish_pct - (12 + seed % 18), 5, 74))
    mixed_pct = max(0, 100 - bullish_pct - bearish_pct)
    catalyst_found = (seed % 10) in {1, 2, 4, 7} or abs(price_move) > 4
    catalyst_labels = [
        "earnings commentary",
        "analyst action",
        "sector headline",
        "product catalyst",
        "filing watch",
        "news follow-through",
    ]
    narrative_pool = [
        "AI demand",
        "earnings beat",
        "short squeeze",
        "data center demand",
        "defense contracts",
        "crypto beta",
        "rate sensitivity",
        "guidance watch",
        "retail speculation",
        "margin pressure",
    ]
    series = []
    price_series = []
    for index in range(7):
        drift = 0.72 + index * (0.035 + (seed % 7) / 400)
        wave = ((_stable_int(symbol, index) % 22) - 8) / 100
        series.append(int(max(5, mentions_today * (drift + wave))))
        price_series.append(round((price_move / 6) * index + ((_stable_int(symbol, "px", index) % 80) - 40) / 100, 2))
    concentration = 38 + (seed % 50)
    float_proxy = 20_000_000 + (prior_seed % 210_000_000)
    return {
        "ticker": symbol,
        "company": quote.get("company_name") or symbol,
        "source": "Demo Data",
        "data_status": "Demo Data",
        "mentions_today": mentions_today,
        "mentions_yesterday": mentions_yesterday,
        "mentions_7d_avg": mentions_7d_avg,
        "mentions_30d_avg": mentions_avg_30d,
        "mentions_30d_std": std_30d,
        "mentions_7d_series": series,
        "price_7d_series": price_series,
        "bullish_pct": bullish_pct,
        "bearish_pct": bearish_pct,
        "mixed_pct": mixed_pct,
        "bullish_7d_avg": bullish_7d,
        "price_move_pct": price_move,
        "volume_vs_30d_avg": relative_volume,
        "catalyst_found": catalyst_found,
        "catalyst_label": catalyst_labels[seed % len(catalyst_labels)] if catalyst_found else "",
        "market_cap": market_cap,
        "float_shares": float_proxy,
        "source_concentration_pct": concentration,
        "top_social_narratives": [
            narrative_pool[seed % len(narrative_pool)],
            narrative_pool[(seed // 7) % len(narrative_pool)],
            narrative_pool[(seed // 17) % len(narrative_pool)],
        ],
        "last_updated": now_et(),
    }


def _provider_for(source: str) -> SocialMomentumProvider:
    key = str(source or "auto").strip().casefold()
    if key in PROVIDERS:
        return PROVIDERS[key]
    for provider_key in ("stocktwits", "reddit", "finbrain"):
        provider = PROVIDERS[provider_key]
        if provider.is_configured():
            return provider
    return PROVIDERS["demo"]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_social_mentions(symbols: tuple[str, ...] | list[str] | None, source: str = "auto") -> tuple[pd.DataFrame, dict]:
    clean_symbols = _as_symbols(symbols)
    if not clean_symbols:
        clean_symbols = market_universe(include_etfs=False)[:80]
    provider = _provider_for(source)
    frame, status = provider.fetch(clean_symbols)
    if frame.empty and provider.source != "Demo Data":
        frame, status = PROVIDERS["demo"].fetch(clean_symbols)
    return frame, {
        "Source": status.source,
        "Status": status.status,
        "Last Updated": status.last_updated,
        "Message": status.message,
        "Warning": SOCIAL_WARNING,
    }


def _sentiment_label(row: pd.Series) -> str:
    bullish = to_float(row.get("bullish_pct")) or 0
    bearish = to_float(row.get("bearish_pct")) or 0
    if bullish >= bearish + 18:
        return "Bullish"
    if bearish >= bullish + 15:
        return "Bearish"
    if bullish >= 48 and bearish >= 24:
        return "Mixed"
    return "Neutral"


def _price_volume_confirmation(row: pd.Series) -> float:
    bullish = to_float(row.get("bullish_pct")) or 0
    bearish = to_float(row.get("bearish_pct")) or 0
    price_move = to_float(row.get("price_move_pct")) or 0
    rel_volume = to_float(row.get("volume_vs_30d_avg")) or 1
    sentiment_direction = 1 if bullish > bearish + 8 else -1 if bearish > bullish + 8 else 0
    price_direction = 1 if price_move > 0 else -1 if price_move < 0 else 0
    aligned = sentiment_direction and sentiment_direction == price_direction
    if aligned and rel_volume >= 1.2:
        return 100
    if aligned:
        return 70
    if rel_volume >= 2.5:
        return 45
    return 25


def _risk_penalty(row: pd.Series) -> float:
    penalty = 0.0
    market_cap = to_float(row.get("market_cap"))
    if market_cap is not None and market_cap < 750_000_000:
        penalty += 14
    if (to_float(row.get("float_shares")) or 999_000_000) < 35_000_000:
        penalty += 10
    if (to_float(row.get("mention_change_24h_pct")) or 0) > 250 and not bool(row.get("catalyst_found")):
        penalty += 18
    if abs(to_float(row.get("price_move_pct")) or 0) > 20:
        penalty += 18
    if (to_float(row.get("volume_vs_30d_avg")) or 1) > 8:
        penalty += 14
    bullish = to_float(row.get("bullish_pct")) or 0
    bearish = to_float(row.get("bearish_pct")) or 0
    if max(bullish, bearish) >= 82:
        penalty += 10
    if (to_float(row.get("source_concentration_pct")) or 0) > 72:
        penalty += 12
    return penalty


def classify_social_signal(row: pd.Series | dict) -> str:
    score = to_float(row.get("social_momentum_score")) or 0
    risk = to_float(row.get("risk_penalty")) or 0
    velocity = to_float(row.get("mention_change_24h_pct")) or 0
    catalyst = bool(row.get("catalyst_found"))
    price_confirmation = to_float(row.get("price_volume_confirmation")) or 0
    if risk >= 42:
        return "Pump Risk"
    if score >= 72 and price_confirmation >= 70 and catalyst:
        return "Confirmed Momentum"
    if risk >= 26 and score >= 52:
        return "Meme / Squeeze Watch"
    if velocity >= 65 and score >= 48:
        return "Early Attention Spike"
    return "Noise"


def _risk_label(row: pd.Series | dict) -> str:
    penalty = to_float(row.get("risk_penalty")) or 0
    if penalty >= 42:
        return "Pump Risk"
    if penalty >= 26:
        return "High"
    if penalty >= 14:
        return "Moderate"
    return "Low"


def calculate_social_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    frame = df.copy()
    frame["mention_change_24h_pct"] = (
        (pd.to_numeric(frame["mentions_today"], errors="coerce") - pd.to_numeric(frame["mentions_yesterday"], errors="coerce"))
        / pd.to_numeric(frame["mentions_yesterday"], errors="coerce").replace(0, pd.NA)
        * 100
    ).fillna(0)
    frame["mention_change_7d_pct"] = (
        (pd.to_numeric(frame["mentions_today"], errors="coerce") - pd.to_numeric(frame["mentions_7d_avg"], errors="coerce"))
        / pd.to_numeric(frame["mentions_7d_avg"], errors="coerce").replace(0, pd.NA)
        * 100
    ).fillna(0)
    frame["mention_zscore"] = (
        (pd.to_numeric(frame["mentions_today"], errors="coerce") - pd.to_numeric(frame["mentions_30d_avg"], errors="coerce"))
        / pd.to_numeric(frame["mentions_30d_std"], errors="coerce").replace(0, pd.NA)
    ).fillna(0)
    frame["sentiment_delta"] = pd.to_numeric(frame["bullish_pct"], errors="coerce").fillna(0) - pd.to_numeric(frame["bullish_7d_avg"], errors="coerce").fillna(0)
    frame["sentiment_label"] = frame.apply(_sentiment_label, axis=1)
    frame["price_volume_confirmation"] = frame.apply(_price_volume_confirmation, axis=1)
    frame["catalyst_confirmation"] = frame["catalyst_found"].apply(lambda value: 100 if bool(value) else 0)
    frame["risk_penalty"] = frame.apply(_risk_penalty, axis=1)
    mention_z = pd.to_numeric(frame["mention_zscore"], errors="coerce").clip(lower=0, upper=3.5) / 3.5 * 100
    velocity = pd.to_numeric(frame["mention_change_24h_pct"], errors="coerce").clip(lower=0, upper=160) / 160 * 100
    sentiment_delta = (pd.to_numeric(frame["sentiment_delta"], errors="coerce").clip(lower=-35, upper=35) + 35) / 70 * 100
    frame["social_momentum_score"] = (
        mention_z * 0.35
        + velocity * 0.25
        + sentiment_delta * 0.15
        + pd.to_numeric(frame["price_volume_confirmation"], errors="coerce").fillna(0) * 0.15
        + pd.to_numeric(frame["catalyst_confirmation"], errors="coerce").fillna(0) * 0.10
        - pd.to_numeric(frame["risk_penalty"], errors="coerce").fillna(0)
    ).clip(0, 100)
    frame["signal_label"] = frame.apply(classify_social_signal, axis=1)
    frame["risk_label"] = frame.apply(_risk_label, axis=1)
    frame = frame.sort_values("social_momentum_score", ascending=False).reset_index(drop=True)
    frame["social_rank"] = frame.index + 1
    return frame


def fetch_social_momentum_names() -> tuple[pd.DataFrame, dict]:
    frame, status = fetch_social_mentions(tuple(market_universe(include_etfs=False)[:80]), "auto")
    scored = calculate_social_scores(frame)
    if scored.empty:
        return scored, status
    display = scored.rename(
        columns={
            "ticker": "Ticker",
            "company": "Company",
            "social_rank": "Social Rank / Trending Rank",
            "mentions_today": "Message Volume",
            "sentiment_label": "Sentiment",
            "price_move_pct": "Daily Move %",
        }
    )
    display["Watchlist Status"] = "Candidate"
    display["Link"] = display["Ticker"].apply(lambda symbol: f"https://stocktwits.com/symbol/{symbol}")
    return display, status
