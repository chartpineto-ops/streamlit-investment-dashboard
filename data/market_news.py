from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Iterable

import pandas as pd

from pineterminal.demo_data import ANALYSES, COMPANIES, THEME_EXPOSURES
from utils.formatting import clean_ticker, now_et


UPDATE_TYPES = [
    "Company News",
    "Earnings",
    "Guidance",
    "Analyst Action",
    "Macro",
    "Sector",
    "Policy / Regulatory",
    "Supply Chain",
    "Commodity",
    "Market Flow",
    "ETF / Index Flow",
    "Crypto",
    "Rates / Yields",
    "Geopolitical",
    "Technology",
    "Other",
]

THESIS_LEVERS = [
    "Customer Demand",
    "Revenue Growth",
    "Gross Margin",
    "Operating Margin",
    "Execution",
    "Balance Sheet",
    "Competitive Position",
    "Valuation Sensitivity",
    "Liquidity Sensitivity",
    "Strategic Value",
    "Asset Demand",
    "Regulatory Risk",
    "Unknown",
]

VALUATION_LEVERS = [
    "Revenue Growth",
    "Gross Margin",
    "Operating Margin",
    "Multiple Expansion",
    "Multiple Compression",
    "Asset Price",
    "Risk Premium",
    "Discount Rate",
    "Cash Flow",
    "Balance Sheet",
    "Dilution Risk",
    "Unknown",
]

SOURCE_TYPES = [
    "News Provider",
    "SEC Filings",
    "Earnings Transcripts",
    "Press Releases",
    "Economic Data",
    "Internal Model / Demo",
]


@dataclass(frozen=True)
class NewsItem:
    id: str
    date: str
    timestamp: datetime
    headline: str
    summary: str
    source: str
    url: str
    tickers: list[str] = field(default_factory=list)
    companyNames: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    updateType: str = "Other"
    directness: str = "Theme"
    impact: str = "Unknown"
    confidence: str = "Medium"
    affectedThesisLever: str = "Unknown"
    affectedValuationLever: str = "Unknown"
    dashboardAdjustment: str = "No model change"
    whyItMatters: str = ""
    readThroughTickers: list[str] = field(default_factory=list)
    readThroughThemes: list[str] = field(default_factory=list)
    signalStrength: float = 0.0
    relevanceScore: float = 0.0
    sourceReliability: str = "Medium"
    dataMode: str = "Demo"
    sourceType: str = "Internal Model / Demo"
    confidenceExplanation: str = "Demo classification based on theme, ticker, and lever mapping."


def _clean_tickers(values: Iterable[str] | None) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for value in values or []:
        symbol = clean_ticker(value)
        if symbol and symbol not in seen:
            cleaned.append(symbol)
            seen.add(symbol)
    return cleaned


def _company_names(tickers: Iterable[str]) -> list[str]:
    names = []
    for ticker in _clean_tickers(tickers):
        company = COMPANIES.get(ticker)
        names.append(company.company_name if company else ticker)
    return names


def _sectors_for_tickers(tickers: Iterable[str], fallback: str = "General") -> list[str]:
    sectors = []
    for ticker in _clean_tickers(tickers):
        company = COMPANIES.get(ticker)
        sector = company.sector if company else fallback
        if sector not in sectors:
            sectors.append(sector)
    return sectors or [fallback]


def _theme_tickers(theme: str) -> list[str]:
    for exposure in THEME_EXPOSURES:
        if exposure.theme.casefold() == theme.casefold():
            return _clean_tickers(exposure.impacted_tickers)
    return []


def _theme_readthrough(theme: str) -> str:
    for exposure in THEME_EXPOSURES:
        if exposure.theme.casefold() == theme.casefold():
            return exposure.transmission_path
    return ""


def _confidence_weight(confidence: str) -> float:
    return {"High": 2.0, "Medium": 1.2, "Low": 0.5}.get(confidence, 0.6)


def _impact_weight(impact: str) -> float:
    return {"Positive": 1.4, "Negative": 1.4, "Mixed": 1.0, "Neutral": 0.5}.get(impact, 0.2)


def _source_weight(source_reliability: str) -> float:
    return {"High": 2.0, "Medium": 1.2, "Low": 0.4}.get(source_reliability, 0.5)


def _recency_weight(timestamp: datetime, reference: datetime) -> float:
    age_days = max(0, (reference.date() - timestamp.date()).days)
    if age_days == 0:
        return 2.0
    if age_days <= 7:
        return 1.2
    if age_days <= 30:
        return 0.5
    return 0.0


def _relevance_score(item: NewsItem, watchlist: set[str], reference: datetime) -> float:
    ticker_mentions = 1.5 if item.tickers else 0.0
    theme_match = min(1.5, len(item.themes) * 0.35)
    watchlist_boost = 1.2 if watchlist.intersection(item.tickers + item.readThroughTickers) else 0.0
    directness_boost = {"Direct": 1.0, "Sector": 0.8, "Theme": 0.7, "Macro": 0.6, "Indirect": 0.6}.get(item.directness, 0.4)
    score = (
        _source_weight(item.sourceReliability)
        + ticker_mentions
        + theme_match
        + _impact_weight(item.impact)
        + _confidence_weight(item.confidence)
        + _recency_weight(item.timestamp, reference)
        + watchlist_boost
        + directness_boost
    )
    return round(score, 2)


def _make_item(
    *,
    id: str,
    day: date,
    time_et: time,
    headline: str,
    summary: str,
    source: str,
    url: str = "",
    tickers: Iterable[str] = (),
    sectors: Iterable[str] = (),
    themes: Iterable[str] = (),
    update_type: str = "Other",
    directness: str = "Theme",
    impact: str = "Unknown",
    confidence: str = "Medium",
    thesis_lever: str = "Unknown",
    valuation_lever: str = "Unknown",
    dashboard_adjustment: str = "No model change",
    why: str = "",
    readthrough_tickers: Iterable[str] = (),
    readthrough_themes: Iterable[str] = (),
    signal_strength: float = 0.0,
    source_reliability: str = "Medium",
    source_type: str = "Internal Model / Demo",
) -> NewsItem:
    clean_direct = _clean_tickers(tickers)
    clean_readthrough = _clean_tickers(readthrough_tickers)
    theme_values = [str(theme) for theme in themes if str(theme).strip()]
    inferred_readthrough = []
    for theme in theme_values:
        inferred_readthrough.extend(_theme_tickers(theme))
    combined_readthrough = _clean_tickers([*clean_readthrough, *inferred_readthrough])
    timestamp = datetime.combine(day, time_et, tzinfo=now_et().tzinfo)
    sector_values = list(dict.fromkeys([str(sector) for sector in sectors if str(sector).strip()] + _sectors_for_tickers([*clean_direct, *combined_readthrough], "General")))
    return NewsItem(
        id=id,
        date=day.isoformat(),
        timestamp=timestamp,
        headline=headline,
        summary=summary,
        source=source,
        url=url,
        tickers=clean_direct,
        companyNames=_company_names(clean_direct),
        sectors=sector_values,
        themes=theme_values,
        updateType=update_type,
        directness=directness,
        impact=impact,
        confidence=confidence,
        affectedThesisLever=thesis_lever,
        affectedValuationLever=valuation_lever,
        dashboardAdjustment=dashboard_adjustment,
        whyItMatters=why or summary or _theme_readthrough(theme_values[0] if theme_values else ""),
        readThroughTickers=combined_readthrough,
        readThroughThemes=list(dict.fromkeys([*theme_values, *[str(theme) for theme in readthrough_themes if str(theme).strip()]])),
        signalStrength=signal_strength,
        relevanceScore=0.0,
        sourceReliability=source_reliability,
        dataMode="Demo",
        sourceType=source_type,
        confidenceExplanation=(
            "High confidence because the item has a direct ticker or clear operational implication."
            if confidence == "High"
            else "Medium confidence because this is a plausible theme/read-through implication."
            if confidence == "Medium"
            else "Low confidence because the market connection is broad or early."
        ),
    )


class NewsProvider:
    def getMarketNews(self) -> list[NewsItem]:
        raise NotImplementedError

    def getTickerNews(self, ticker: str) -> list[NewsItem]:
        symbol = clean_ticker(ticker)
        return [item for item in self.getMarketNews() if symbol in item.tickers or symbol in item.readThroughTickers]

    def getThemeNews(self, theme: str) -> list[NewsItem]:
        selected = str(theme or "").casefold()
        return [item for item in self.getMarketNews() if selected in {value.casefold() for value in item.themes + item.readThroughThemes}]

    def getWatchlistNews(self, tickers: Iterable[str]) -> list[NewsItem]:
        watchlist = set(_clean_tickers(tickers))
        return [item for item in self.getMarketNews() if watchlist.intersection(item.tickers + item.readThroughTickers)]

    def classifyNewsItem(self, item: NewsItem) -> NewsItem:
        return item

    def mapNewsToThemes(self, item: NewsItem) -> list[str]:
        return item.themes

    def mapThemesToTickers(self, themes: Iterable[str]) -> list[str]:
        tickers: list[str] = []
        for theme in themes:
            tickers.extend(_theme_tickers(str(theme)))
        return _clean_tickers(tickers)


class DemoMarketNewsProvider(NewsProvider):
    def __init__(self, reference: datetime | None = None):
        self.reference = reference or now_et()

    def getMarketNews(self) -> list[NewsItem]:
        today = self.reference.date()
        items = [
            _make_item(
                id="ai-capex-20260603",
                day=today,
                time_et=time(9, 28),
                headline="Hyperscaler AI capex guidance moves higher again",
                summary="Cloud operators point to another step-up in AI infrastructure spend across networking, custom silicon, servers, cooling, and power.",
                source="Demo News Provider",
                tickers=[],
                sectors=["Technology", "Utilities", "Industrials"],
                themes=["AI Data Centers", "Custom Silicon", "Power Demand"],
                update_type="Sector",
                directness="Sector",
                impact="Positive",
                confidence="High",
                thesis_lever="Customer Demand",
                valuation_lever="Revenue Growth",
                dashboard_adjustment="Catalyst score +0.4",
                why="Supports demand visibility for AI networking, custom silicon, servers, cooling, and power infrastructure.",
                signal_strength=4.4,
                source_reliability="High",
            ),
            _make_item(
                id="rates-20260603",
                day=today,
                time_et=time(8, 47),
                headline="Treasury yields move higher as inflation concerns persist",
                summary="A firmer rates backdrop raises discount-rate pressure on speculative growth and other long-duration assets.",
                source="Demo Macro Desk",
                sectors=["Financials", "Technology"],
                themes=["Rates / Treasury Yields", "Speculative Technology"],
                update_type="Rates / Yields",
                directness="Macro",
                impact="Negative",
                confidence="Medium",
                thesis_lever="Valuation Sensitivity",
                valuation_lever="Multiple Compression",
                dashboard_adjustment="Risk discount +0.2",
                why="Higher discount rates pressure long-duration growth stocks and reduce willingness to pay for distant optionality.",
                readthrough_tickers=["IONQ", "AMPX", "RGTI", "QBTS"],
                signal_strength=-3.4,
            ),
            _make_item(
                id="rare-earth-20260603",
                day=today,
                time_et=time(8, 16),
                headline="Rare earth export controls tighten around magnet supply",
                summary="New licensing pressure raises the strategic value of domestic rare-earth producers and defense supply chain assets.",
                source="Demo Policy Wire",
                sectors=["Materials", "Industrials"],
                themes=["Critical Minerals", "Defense Supply Chain"],
                update_type="Policy / Regulatory",
                directness="Sector",
                impact="Positive",
                confidence="Medium",
                thesis_lever="Strategic Value",
                valuation_lever="Multiple Expansion",
                dashboard_adjustment="Multiple support +0.3",
                why="Supply-chain pressure can increase strategic value of domestic critical mineral producers and suppliers.",
                readthrough_tickers=["MP", "REMX", "LAC"],
                signal_strength=3.2,
            ),
            _make_item(
                id="bitcoin-flows-20260603",
                day=today,
                time_et=time(7, 52),
                headline="Spot Bitcoin ETF inflows continue for fifth consecutive session",
                summary="Digital asset funds attract sustained institutional demand while liquidity remains supportive.",
                source="Demo Digital Assets",
                tickers=["FBTC", "IBIT"],
                sectors=["Digital Assets", "Financials"],
                themes=["Bitcoin", "Crypto ETF Flows", "Digital Assets"],
                update_type="ETF / Index Flow",
                directness="Sector",
                impact="Positive",
                confidence="High",
                thesis_lever="Asset Demand",
                valuation_lever="Asset Price",
                dashboard_adjustment="Catalyst score +0.3",
                why="Sustained inflows support crypto asset prices and validate institutional allocation demand.",
                readthrough_tickers=["COIN", "MSTR", "MARA", "RIOT"],
                signal_strength=3.6,
                source_reliability="High",
            ),
            _make_item(
                id="drone-procurement-20260602",
                day=today - timedelta(days=1),
                time_et=time(14, 5),
                headline="Pentagon increases funding for small autonomous drone programs",
                summary="Procurement language emphasizes endurance, lightweight payloads, and domestic supply chain resilience.",
                source="Demo Defense Wire",
                sectors=["Industrials", "Technology"],
                themes=["Military Drones", "Defense Supply Chain", "Batteries"],
                update_type="Policy / Regulatory",
                directness="Theme",
                impact="Positive",
                confidence="Medium",
                thesis_lever="Customer Demand",
                valuation_lever="Revenue Growth",
                dashboard_adjustment="Revenue confidence +0.2",
                why="Higher drone demand increases the value of lightweight, high-density batteries, sensors, and autonomous systems.",
                readthrough_tickers=["AMPX", "AVAV", "KTOS", "RCAT"],
                signal_strength=3.1,
            ),
            _make_item(
                id="mrvl-guidance-20260602",
                day=today - timedelta(days=1),
                time_et=time(10, 34),
                headline="Marvell points to stronger AI custom silicon visibility",
                summary="Management commentary highlights custom silicon demand and AI networking content as near-term growth supports.",
                source="Demo Company News",
                tickers=["MRVL"],
                sectors=["Technology"],
                themes=["Custom Silicon", "AI Data Centers", "Semiconductors"],
                update_type="Guidance",
                directness="Direct",
                impact="Positive",
                confidence="High",
                thesis_lever="Customer Demand",
                valuation_lever="Revenue Growth",
                dashboard_adjustment="Catalyst score +0.4",
                why="AI ASIC demand is accelerating across cloud customers, improving revenue confidence.",
                readthrough_tickers=["AVGO", "TSM", "NVDA"],
                signal_strength=4.0,
                source_reliability="High",
                source_type="Press Releases",
            ),
            _make_item(
                id="nvda-supercomputers-20260602",
                day=today - timedelta(days=1),
                time_et=time(9, 12),
                headline="NVIDIA expands U.S. AI supercomputer manufacturing partnerships",
                summary="New manufacturing partners improve capacity, supply resilience, and policy alignment for AI infrastructure.",
                source="Demo Press Release",
                tickers=["NVDA"],
                sectors=["Technology"],
                themes=["AI Compute", "GPUs", "Supply Chain"],
                update_type="Company News",
                directness="Direct",
                impact="Positive",
                confidence="High",
                thesis_lever="Competitive Position",
                valuation_lever="Strategic Value",
                dashboard_adjustment="Strategic value +0.3",
                why="Strengthens supply resilience and reinforces domestic AI infrastructure positioning.",
                signal_strength=3.5,
                source_reliability="High",
                source_type="Press Releases",
            ),
            _make_item(
                id="power-contracts-20260602",
                day=today - timedelta(days=1),
                time_et=time(7, 35),
                headline="Utilities report early-summer load growth above five-year average",
                summary="Data-center load and electrification demand support longer-duration power contracts.",
                source="Demo Energy Desk",
                sectors=["Utilities", "Energy", "Industrials"],
                themes=["Power Demand", "Nuclear Energy", "Grid Demand"],
                update_type="Sector",
                directness="Sector",
                impact="Positive",
                confidence="High",
                thesis_lever="Customer Demand",
                valuation_lever="Revenue Growth",
                dashboard_adjustment="Revenue confidence +0.1",
                why="Stronger load growth benefits power infrastructure, generators, and grid suppliers.",
                readthrough_tickers=["CEG", "VST", "ETN", "PWR", "VRT"],
                signal_strength=3.3,
            ),
            _make_item(
                id="ionq-rd-20260601",
                day=today - timedelta(days=2),
                time_et=time(6, 2),
                headline="Federal quantum R&D award cycle expands pilot funding",
                summary="Government-backed pilot funding supports quantum ecosystem development and early platform validation.",
                source="Demo Government Data",
                sectors=["Technology"],
                themes=["Quantum Computing", "Government R&D"],
                update_type="Technology",
                directness="Indirect",
                impact="Positive",
                confidence="Low",
                thesis_lever="Strategic Value",
                valuation_lever="Multiple Expansion",
                dashboard_adjustment="Catalyst score +0.2",
                why="Funding can validate emerging quantum platforms and extend runway, but commercialization remains early.",
                readthrough_tickers=["IONQ", "RGTI", "QBTS", "QUBT"],
                signal_strength=2.0,
                source_type="Economic Data",
            ),
            _make_item(
                id="battery-supply-20260601",
                day=today - timedelta(days=2),
                time_et=time(11, 18),
                headline="Battery supply chain update highlights qualification delays",
                summary="Advanced-cell suppliers face longer customer validation cycles despite stronger defense and aviation interest.",
                source="Demo Supply Chain",
                sectors=["Technology", "Industrials"],
                themes=["Batteries", "Military Drones", "Supply Chain"],
                update_type="Supply Chain",
                directness="Theme",
                impact="Mixed",
                confidence="Medium",
                thesis_lever="Execution",
                valuation_lever="Revenue Growth",
                dashboard_adjustment="Execution risk +0.1",
                why="Customer demand is improving, but qualification timing still governs when revenue can scale.",
                readthrough_tickers=["AMPX", "QS", "SLDP", "ALB"],
                signal_strength=0.8,
            ),
            _make_item(
                id="semi-inventory-20260601",
                day=today - timedelta(days=2),
                time_et=time(9, 43),
                headline="Semiconductor inventory digestion persists outside AI end markets",
                summary="Non-AI demand remains uneven, offsetting AI strength for diversified semiconductor suppliers.",
                source="Demo Sector Research",
                sectors=["Technology"],
                themes=["Semiconductor Cycle", "Semiconductors"],
                update_type="Sector",
                directness="Sector",
                impact="Negative",
                confidence="Medium",
                thesis_lever="Revenue Growth",
                valuation_lever="Gross Margin",
                dashboard_adjustment="Margin confidence -0.1",
                why="Weak non-AI demand can pressure blended margins and reduce cyclically sensitive revenue support.",
                readthrough_tickers=["MRVL", "AMD", "TSM", "QCOM", "TXN"],
                signal_strength=-2.8,
            ),
            _make_item(
                id="analyst-power-20260531",
                day=today - timedelta(days=3),
                time_et=time(10, 20),
                headline="Analysts lift power equipment targets on data-center backlog",
                summary="Several coverage teams point to backlog durability across grid equipment and thermal management.",
                source="Demo Analyst Desk",
                sectors=["Industrials", "Utilities"],
                themes=["Power Demand", "Grid Demand", "AI Data Centers"],
                update_type="Analyst Action",
                directness="Theme",
                impact="Positive",
                confidence="Medium",
                thesis_lever="Competitive Position",
                valuation_lever="Multiple Expansion",
                dashboard_adjustment="Multiple support +0.2",
                why="Backlog visibility can support premium multiples for infrastructure suppliers tied to AI load growth.",
                readthrough_tickers=["VRT", "ETN", "PWR", "CEG"],
                signal_strength=2.7,
                source_type="News Provider",
            ),
            _make_item(
                id="mp-export-20260531",
                day=today - timedelta(days=3),
                time_et=time(8, 58),
                headline="Magnet supply discussions add policy support for domestic rare earths",
                summary="Policy discussions focus on domestic magnet supply chains and defense procurement resilience.",
                source="Demo Policy Wire",
                tickers=["MP"],
                sectors=["Materials", "Industrials"],
                themes=["Critical Minerals", "Rare Earths", "Defense Supply Chain"],
                update_type="Policy / Regulatory",
                directness="Direct",
                impact="Positive",
                confidence="High",
                thesis_lever="Strategic Value",
                valuation_lever="Multiple Expansion",
                dashboard_adjustment="Strategic value +0.4",
                why="Directly supports the strategic value argument for domestic rare earth capacity.",
                readthrough_tickers=["REMX", "LAC", "LMT", "RTX"],
                signal_strength=3.8,
                source_reliability="High",
            ),
        ]
        scored = []
        for item in items:
            scored.append(item.__class__(**{**item.__dict__, "relevanceScore": _relevance_score(item, set(), self.reference)}))
        return sorted(scored, key=lambda item: (item.relevanceScore, item.timestamp), reverse=True)


def market_news_provider() -> NewsProvider:
    return DemoMarketNewsProvider()


def filter_news_items(
    items: Iterable[NewsItem],
    *,
    mode: str = "Market-Wide",
    watchlist_tickers: Iterable[str] = (),
    selected_ticker: str = "",
    ticker_filters: Iterable[str] = (),
    sector: str = "All",
    theme: str = "All",
    impact: str = "All",
    update_type: str = "All",
    directness: str = "All",
    source_type: str = "All Sources",
    date_filter: str = "Last 7 Days",
    custom_start: date | None = None,
    custom_end: date | None = None,
    search: str = "",
) -> list[NewsItem]:
    watchlist = set(_clean_tickers(watchlist_tickers))
    selected = clean_ticker(selected_ticker)
    explicit_tickers = set(_clean_tickers(ticker_filters))
    reference = now_et()
    output = []
    for item in items:
        related_tickers = set(item.tickers + item.readThroughTickers)
        if mode == "Watchlist" and not watchlist.intersection(related_tickers):
            continue
        if mode == "Ticker" and selected and selected not in related_tickers:
            continue
        if explicit_tickers and not explicit_tickers.intersection(related_tickers):
            continue
        if sector != "All" and sector not in item.sectors:
            continue
        if theme != "All" and theme not in item.themes and theme not in item.readThroughThemes:
            continue
        if impact != "All" and item.impact != impact:
            continue
        if update_type != "All" and item.updateType != update_type:
            continue
        if directness != "All" and item.directness != directness:
            continue
        if source_type != "All Sources" and item.sourceType != source_type:
            continue
        if not _date_matches(item.timestamp.date(), date_filter, reference.date(), custom_start, custom_end):
            continue
        if search:
            haystack = " ".join(
                [
                    item.headline,
                    item.summary,
                    item.whyItMatters,
                    " ".join(item.tickers),
                    " ".join(item.readThroughTickers),
                    " ".join(item.themes),
                    " ".join(item.sectors),
                ]
            ).casefold()
            if search.casefold() not in haystack:
                continue
        output.append(item.__class__(**{**item.__dict__, "relevanceScore": _relevance_score(item, watchlist, reference)}))
    return sorted(output, key=lambda item: (item.relevanceScore, item.timestamp), reverse=True)


def _date_matches(item_date: date, date_filter: str, today: date, custom_start: date | None, custom_end: date | None) -> bool:
    if date_filter == "Today":
        return item_date == today
    if date_filter == "Last 7 Days":
        return item_date >= today - timedelta(days=7)
    if date_filter == "Last 30 Days":
        return item_date >= today - timedelta(days=30)
    if date_filter == "Custom":
        start = custom_start or today - timedelta(days=7)
        end = custom_end or today
        return start <= item_date <= end
    return True


def news_summary(items: Iterable[NewsItem], watchlist_tickers: Iterable[str]) -> dict[str, int]:
    rows = list(items)
    watchlist = set(_clean_tickers(watchlist_tickers))
    return {
        "market_updates": sum(1 for item in rows if item.directness in {"Macro", "Sector", "Theme", "Indirect"}),
        "company_news": sum(1 for item in rows if item.directness == "Direct" or item.updateType in {"Company News", "Earnings", "Guidance"}),
        "indirect_readthroughs": sum(1 for item in rows if item.directness in {"Indirect", "Theme", "Sector", "Macro"}),
        "watchlist_impacts": sum(1 for item in rows if watchlist.intersection(item.tickers + item.readThroughTickers)),
    }
