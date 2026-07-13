from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd

from utils.formatting import now_et
from utils.secrets import secret_or_env


@dataclass(frozen=True)
class FeedContract:
    domain: str
    feed: str
    primary: str
    fallback: str
    refresh_seconds: int
    credential_names: tuple[str, ...]
    integrity_rule: str
    configured_status: str = "Live"
    fallback_status: str = "Delayed"


FEED_CONTRACTS: tuple[FeedContract, ...] = (
    FeedContract(
        "Market",
        "US equity quotes",
        "Finnhub",
        "Yahoo Finance delayed fallback",
        10,
        ("FINNHUB_API_KEY",),
        "Reject missing prices; show provider timestamp and market session.",
    ),
    FeedContract(
        "Market",
        "Consolidated trade feed",
        "Polygon / Massive",
        "Not active",
        5,
        ("POLYGON_API_KEY", "MASSIVE_API_KEY"),
        "Entitlement required; never label delayed quotes real-time.",
        configured_status="Configured / unwired",
        fallback_status="Unavailable",
    ),
    FeedContract(
        "Financials",
        "Reported fundamentals",
        "SEC EDGAR companyfacts",
        "Yahoo Finance statement fallback",
        86_400,
        (),
        "Reconcile fiscal period, units, and filed facts before deriving ratios.",
        configured_status="Authoritative",
        fallback_status="Partial",
    ),
    FeedContract(
        "Financials",
        "Estimates and company news",
        "Finnhub",
        "Yahoo Finance estimates / demo news",
        120,
        ("FINNHUB_API_KEY",),
        "Timestamp every observation; keep estimates separate from reported facts.",
        fallback_status="Mixed",
    ),
    FeedContract(
        "Economic",
        "Macro time series",
        "FRED",
        "Demo macro dataset",
        3_600,
        ("FRED_API_KEY",),
        "Preserve release date and revisions; do not mix vintage and latest values.",
        configured_status="Official",
        fallback_status="Demo",
    ),
    FeedContract(
        "Economic",
        "Labor releases",
        "BLS Public Data API",
        "FRED mirror",
        3_600,
        ("BLS_API_KEY",),
        "Match series ID, seasonal adjustment, period, and release calendar.",
        configured_status="Official",
        fallback_status="Official mirror",
    ),
    FeedContract(
        "Social",
        "Retail attention and sentiment",
        "Stocktwits / Reddit / FinBrain",
        "Clearly labeled demo data",
        300,
        ("STOCKTWITS_API_KEY", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "FINBRAIN_API_KEY"),
        "Require source diversity, minimum sample size, and outlier penalties.",
        configured_status="Configured / adapter pending",
        fallback_status="Demo",
    ),
)


def _configured(names: Iterable[str]) -> bool:
    names = tuple(names)
    return not names or any(bool(secret_or_env(name)) for name in names)


def _contract_configured(contract: FeedContract) -> bool:
    if contract.domain == "Social":
        reddit = bool(secret_or_env("REDDIT_CLIENT_ID") and secret_or_env("REDDIT_CLIENT_SECRET"))
        return bool(secret_or_env("STOCKTWITS_API_KEY") or secret_or_env("FINBRAIN_API_KEY") or reddit)
    return _configured(contract.credential_names)


def provider_health() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    checked = now_et()
    for contract in FEED_CONTRACTS:
        configured = _contract_configured(contract)
        status = contract.configured_status if configured else contract.fallback_status
        rows.append(
            {
                **asdict(contract),
                "configured": configured,
                "status": status,
                "checked_at": checked,
            }
        )
    return pd.DataFrame(rows)


def classify_frame(frame: pd.DataFrame | None, source_column: str = "data_source") -> str:
    if frame is None or frame.empty:
        return "Unavailable"
    if source_column not in frame:
        return "Available"
    sources = " ".join(frame[source_column].dropna().astype(str).unique()).casefold()
    if "demo" in sources or "placeholder" in sources:
        return "Demo"
    if "delayed" in sources or "yahoo" in sources:
        return "Delayed"
    if "fred" in sources or "sec" in sources or "bls" in sources:
        return "Official"
    return "Live"


def newest_timestamp(frame: pd.DataFrame | None, candidates: tuple[str, ...]) -> datetime | None:
    if frame is None or frame.empty:
        return None
    for column in candidates:
        if column not in frame:
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce", utc=True).dropna()
        if not parsed.empty:
            value = parsed.max()
            return value.to_pydatetime()
    return None


def freshness_label(timestamp: object, stale_after_seconds: int) -> tuple[str, str]:
    parsed = pd.to_datetime(timestamp, errors="coerce", utc=True)
    if pd.isna(parsed):
        return "No timestamp", "bad"
    current = pd.Timestamp.now(tz="UTC")
    age = max(0, int((current - parsed).total_seconds()))
    if age < 60:
        label = f"{age}s ago"
    elif age < 3_600:
        label = f"{age // 60}m ago"
    elif age < 86_400:
        label = f"{age // 3_600}h ago"
    else:
        label = f"{age // 86_400}d ago"
    return label, "ok" if age <= stale_after_seconds else "warn"


def status_tone(status: str) -> str:
    lowered = str(status or "").casefold()
    if any(token in lowered for token in ("live", "official", "authoritative", "ok", "available")):
        return "ok"
    if any(token in lowered for token in ("delayed", "partial", "mixed", "fallback", "mirror")):
        return "warn"
    return "bad"
