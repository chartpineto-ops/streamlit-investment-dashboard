from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from data.market_data import fetch_quote
from data.market_movers import get_whole_market_movers
from data.market_universe import ETF_TICKERS, get_broad_market_universe_with_status
from utils.formatting import clean_ticker, now_et, to_float


UNIVERSE_OPTIONS = {
    "All U.S. Stocks": "all_us_stocks",
    "NYSE": "nyse",
    "Nasdaq": "nasdaq",
    "AMEX": "amex",
    "ETFs": "etfs",
    "Large Cap": "large_cap",
    "Mid Cap": "mid_cap",
    "Small Cap": "small_cap",
    "Micro Cap": "micro_cap",
    "Watchlist Only": "watchlist",
    "Custom Universe": "custom",
}

EXCHANGE_ALIASES = {
    "NMS": "Nasdaq",
    "NGM": "Nasdaq",
    "NCM": "Nasdaq",
    "NASDAQ": "Nasdaq",
    "NAS": "Nasdaq",
    "NYQ": "NYSE",
    "NYSE": "NYSE",
    "ASE": "AMEX",
    "AMEX": "AMEX",
    "PCX": "NYSE Arca",
    "ARCX": "NYSE Arca",
}


@dataclass(frozen=True)
class ScannerFilters:
    universe_type: str = "all_us_stocks"
    session: str = "Regular Market"
    min_price: float = 2.0
    min_market_cap: float = 100_000_000.0
    min_dollar_volume: float = 10_000_000.0
    min_move_pct: float = 3.0
    min_relative_volume: float = 2.0
    min_unusual_volume_pct: float = 100.0
    direction: str = "Both"
    theme: str = "All"
    include_etfs: bool = True
    exclude_low_liquidity: bool = True
    custom_tickers: tuple[str, ...] = field(default_factory=tuple)
    refresh_token: int = 0


def calculate_relative_volume(current_volume: float | None, average_volume: float | None) -> float | None:
    current = to_float(current_volume)
    average = to_float(average_volume)
    if current is None or average in (None, 0):
        return None
    return current / average


def calculate_unusual_volume_percent(current_volume: float | None, average_volume: float | None) -> float | None:
    current = to_float(current_volume)
    average = to_float(average_volume)
    if current is None or average in (None, 0):
        return None
    return ((current - average) / average) * 100


def calculate_dollar_volume(current_price: float | None, current_volume: float | None) -> float | None:
    price = to_float(current_price)
    volume = to_float(current_volume)
    if price is None or volume is None:
        return None
    return price * volume


def classify_volume_anomaly(relative_volume: float | None) -> str:
    rel = to_float(relative_volume)
    if rel is None:
        return "Unknown"
    if rel < 1:
        return "Below Normal"
    if rel < 1.5:
        return "Normal"
    if rel < 2:
        return "Elevated"
    if rel < 4:
        return "Unusual"
    if rel < 8:
        return "Very Unusual"
    return "Extreme"


def classify_move_signal(percent_change: float | None, relative_volume: float | None) -> str:
    move = to_float(percent_change)
    rel = to_float(relative_volume)
    if move is None or rel is None:
        return "Normal move"
    if move >= 10 and rel >= 4:
        return "Momentum surge"
    if move >= 5 and rel >= 2:
        return "High-volume breakout"
    if move <= -10 and rel >= 4:
        return "Breakdown / capitulation"
    if move <= -5 and rel >= 2:
        return "High-volume selloff"
    if abs(move) < 2 and rel >= 4:
        return "Volume anomaly without price confirmation"
    return "Normal move"


def _clean_tickers(values: Iterable[str] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen = set()
    for value in values or ():
        symbol = clean_ticker(value)
        if symbol and symbol not in seen:
            seen.add(symbol)
            cleaned.append(symbol)
    return tuple(cleaned)


def _normalize_exchange(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "N/A"
    return EXCHANGE_ALIASES.get(text.upper(), text)


def _source_to_data_mode(status: dict) -> str:
    raw_status = str(status.get("status") or "").casefold()
    universe_source = str(status.get("universe_source") or "")
    source = str(status.get("source") or status.get("provider") or "")
    if raw_status in {"error"}:
        return "Demo/Fallback"
    if "fallback" in raw_status or "fallback" in universe_source.casefold() or "fallback" in source.casefold():
        return "Partial/Fallback"
    if "predefined market movers" in source.casefold() or "day_gainers" in universe_source:
        return "Partial"
    if "local" in universe_source.casefold() or "listed-stock universe" in source.casefold():
        return "Live"
    return "Partial"


def _get_value(row: pd.Series, *keys: str):
    for key in keys:
        if key in row and row.get(key) is not None:
            value = row.get(key)
            if not (isinstance(value, float) and pd.isna(value)):
                return value
    return None


def _row_from_quote(quote: dict, universe_type: str, watchlist: set[str]) -> dict:
    ticker = clean_ticker(quote.get("ticker"))
    price = to_float(quote.get("price"))
    volume = to_float(quote.get("volume"))
    average_volume = to_float(quote.get("average_volume"))
    relative_volume = calculate_relative_volume(volume, average_volume)
    unusual_volume = calculate_unusual_volume_percent(volume, average_volume)
    dollar_volume = calculate_dollar_volume(price, volume)
    change_pct = to_float(quote.get("daily_change_pct"))
    return {
        "ticker": ticker,
        "companyName": quote.get("company_name") or ticker,
        "exchange": _normalize_exchange(quote.get("exchange")),
        "sector": quote.get("sector") or "N/A",
        "industry": quote.get("industry") or "N/A",
        "theme": quote.get("sector") or quote.get("industry") or "General",
        "currentPrice": price,
        "priceChangePercent": change_pct,
        "priceChangeDollar": to_float(quote.get("daily_change")),
        "currentVolume": volume,
        "averageVolume": average_volume,
        "relativeVolume": relative_volume,
        "unusualVolumePercent": unusual_volume,
        "dollarVolume": dollar_volume,
        "marketCap": to_float(quote.get("market_cap")),
        "floatShares": None,
        "shortInterestPercentFloat": None,
        "session": "Regular Market",
        "direction": _direction(change_pct),
        "catalyst": "Volume anomaly" if (relative_volume or 0) >= 2 else "No catalyst detected",
        "signal": classify_move_signal(change_pct, relative_volume),
        "volumeAnomaly": classify_volume_anomaly(relative_volume),
        "universe": universe_type,
        "quoteType": quote.get("quote_type") or "",
        "isWatchlistTicker": ticker in watchlist,
        "source": quote.get("source") or "Yahoo Finance/yfinance",
        "lastUpdated": quote.get("last_updated") or now_et(),
    }


def _direction(change_pct: float | None) -> str:
    change = to_float(change_pct)
    if change is None:
        return "Flat"
    if change > 0:
        return "Up"
    if change < 0:
        return "Down"
    return "Flat"


class MarketUniverseProvider:
    """Scanner-facing wrapper around market mover feeds and quote snapshots."""

    def getUniverse(
        self,
        universe_type: str,
        custom_tickers: Iterable[str] | None = None,
        watchlist_tickers: Iterable[str] | None = None,
        include_etfs: bool = True,
    ) -> tuple[list[str], dict]:
        if universe_type == "custom":
            tickers = list(_clean_tickers(custom_tickers))
            return tickers, {"status": "OK", "universe_source": "Custom ticker list", "universe_count": len(tickers)}
        if universe_type == "watchlist":
            tickers = list(_clean_tickers(watchlist_tickers))
            return tickers, {"status": "OK", "universe_source": "User watchlist", "universe_count": len(tickers)}
        if universe_type == "etfs":
            tickers = sorted(ETF_TICKERS)
            return tickers, {"status": "OK", "universe_source": "Bundled ETF universe", "universe_count": len(tickers)}
        tickers, status = get_broad_market_universe_with_status(include_etfs=include_etfs)
        return tickers, status

    def getTickerMetadata(self, tickers: Iterable[str]) -> pd.DataFrame:
        symbols = _clean_tickers(tickers)
        return pd.DataFrame({"ticker": symbols})

    def getMarketSnapshot(self, tickers: Iterable[str], universe_type: str, watchlist_tickers: Iterable[str]) -> pd.DataFrame:
        watchlist = set(_clean_tickers(watchlist_tickers))
        rows: list[dict] = []
        for ticker in _clean_tickers(tickers):
            quote = fetch_quote(ticker)
            if quote.get("status") == "OK":
                rows.append(_row_from_quote(quote, universe_type, watchlist))
        return pd.DataFrame(rows)

    def getVolumeMetrics(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        output = frame.copy()
        for column in (
            "currentPrice",
            "priceChangePercent",
            "priceChangeDollar",
            "currentVolume",
            "averageVolume",
            "relativeVolume",
            "unusualVolumePercent",
            "dollarVolume",
            "marketCap",
        ):
            if column in output.columns:
                output[column] = pd.to_numeric(output[column], errors="coerce")
        output["relativeVolume"] = output.apply(
            lambda row: row.get("relativeVolume")
            if pd.notna(row.get("relativeVolume"))
            else calculate_relative_volume(row.get("currentVolume"), row.get("averageVolume")),
            axis=1,
        )
        output["unusualVolumePercent"] = output.apply(
            lambda row: row.get("unusualVolumePercent")
            if pd.notna(row.get("unusualVolumePercent"))
            else calculate_unusual_volume_percent(row.get("currentVolume"), row.get("averageVolume")),
            axis=1,
        )
        output["dollarVolume"] = output.apply(
            lambda row: row.get("dollarVolume")
            if pd.notna(row.get("dollarVolume"))
            else calculate_dollar_volume(row.get("currentPrice"), row.get("currentVolume")),
            axis=1,
        )
        output["direction"] = output["priceChangePercent"].apply(_direction)
        output["volumeAnomaly"] = output["relativeVolume"].apply(classify_volume_anomaly)
        output["signal"] = output.apply(lambda row: classify_move_signal(row.get("priceChangePercent"), row.get("relativeVolume")), axis=1)
        output["catalyst"] = output["relativeVolume"].apply(lambda value: "Volume anomaly" if to_float(value) is not None and to_float(value) >= 2 else "No catalyst detected")
        return output

    def scanMarket(
        self,
        filters: ScannerFilters,
        watchlist_tickers: Iterable[str] | None = None,
        custom_tickers: Iterable[str] | None = None,
    ) -> dict:
        watchlist = set(_clean_tickers(watchlist_tickers))
        requested_custom = custom_tickers if custom_tickers is not None else filters.custom_tickers
        min_volume = 100_000 if not filters.exclude_low_liquidity else 500_000

        if filters.universe_type in {"custom", "watchlist", "etfs"}:
            tickers, universe_status = self.getUniverse(filters.universe_type, requested_custom, watchlist, filters.include_etfs)
            frame = self.getMarketSnapshot(tickers, filters.universe_type, watchlist)
            source_status = {
                **universe_status,
                "source": "Yahoo Finance/yfinance ticker snapshots",
                "provider": "Yahoo Finance/yfinance",
                "after_filters": len(frame),
                "last_updated": now_et(),
                "status": "OK" if not frame.empty else "Error",
                "message": "Ticker-level snapshots for selected scanner universe.",
            }
        else:
            packet = get_whole_market_movers(
                min_price=filters.min_price,
                min_volume=min_volume,
                max_universe_size=5000,
                include_etfs=filters.include_etfs or filters.universe_type == "etfs",
                refresh=bool(filters.refresh_token),
            )
            raw_frame = packet.get("all_scanned", pd.DataFrame())
            frame = self._normalize_mover_frame(raw_frame, filters.universe_type, watchlist)
            frame = self._enrich_filter_metadata(frame, filters.universe_type, watchlist)
            source_status = dict(packet.get("source_status", {}))

        frame = self.getVolumeMetrics(frame)
        filtered = self._apply_filters(frame, filters)
        if filtered.empty:
            summary = self._summary(filtered, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
            status = {
                **source_status,
                "data_mode": _source_to_data_mode(source_status),
                "rows": 0,
                "universe_label": self._universe_label(filters.universe_type),
                "last_updated": source_status.get("last_updated") or now_et(),
                "watchlist_alerts": 0,
            }
            return {
                "all_results": filtered,
                "gainers": pd.DataFrame(),
                "losers": pd.DataFrame(),
                "unusual_volume": pd.DataFrame(),
                "watchlist_alerts": pd.DataFrame(),
                "summary": summary,
                "status": status,
            }
        filtered = filtered.sort_values(["relativeVolume", "dollarVolume"], ascending=[False, False], na_position="last").reset_index(drop=True)
        gainers = (
            filtered[filtered["priceChangePercent"] > 0]
            .sort_values(["priceChangePercent", "relativeVolume", "dollarVolume"], ascending=[False, False, False], na_position="last")
            .reset_index(drop=True)
        )
        losers = (
            filtered[filtered["priceChangePercent"] < 0]
            .sort_values(["priceChangePercent", "relativeVolume", "dollarVolume"], ascending=[True, False, False], na_position="last")
            .reset_index(drop=True)
        )
        unusual = filtered.sort_values(["relativeVolume", "unusualVolumePercent", "dollarVolume"], ascending=[False, False, False], na_position="last").reset_index(drop=True)
        watchlist_alerts = filtered[filtered["isWatchlistTicker"]].sort_values(["relativeVolume", "priceChangePercent"], ascending=[False, False], na_position="last").reset_index(drop=True)

        summary = self._summary(filtered, gainers, losers, unusual, watchlist_alerts)
        status = {
            **source_status,
            "data_mode": _source_to_data_mode(source_status),
            "rows": len(filtered),
            "universe_label": self._universe_label(filters.universe_type),
            "last_updated": source_status.get("last_updated") or now_et(),
            "watchlist_alerts": len(watchlist_alerts),
        }
        return {
            "all_results": filtered,
            "gainers": gainers,
            "losers": losers,
            "unusual_volume": unusual,
            "watchlist_alerts": watchlist_alerts,
            "summary": summary,
            "status": status,
        }

    def _normalize_mover_frame(self, frame: pd.DataFrame, universe_type: str, watchlist: set[str]) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        rows: list[dict] = []
        for _, row in frame.iterrows():
            ticker = clean_ticker(_get_value(row, "Ticker", "ticker"))
            if not ticker:
                continue
            price = to_float(_get_value(row, "Price", "price", "currentPrice"))
            volume = to_float(_get_value(row, "Volume", "volume", "currentVolume"))
            relative_volume = to_float(_get_value(row, "Relative Volume", "relativeVolume"))
            average_volume = to_float(_get_value(row, "Average Volume", "Avg Vol", "averageVolume"))
            if average_volume is None and volume is not None and relative_volume not in (None, 0):
                average_volume = volume / relative_volume
            change_pct = to_float(_get_value(row, "Daily Move %", "% Change", "priceChangePercent"))
            rows.append(
                {
                    "ticker": ticker,
                    "companyName": _get_value(row, "Company", "companyName") or ticker,
                    "exchange": _normalize_exchange(_get_value(row, "Exchange", "exchange")),
                    "sector": _get_value(row, "Sector", "sector") or "N/A",
                    "industry": _get_value(row, "Industry", "industry") or "N/A",
                    "theme": _get_value(row, "Theme", "Sector", "Industry") or "General",
                    "currentPrice": price,
                    "priceChangePercent": change_pct,
                    "priceChangeDollar": None,
                    "currentVolume": volume,
                    "averageVolume": average_volume,
                    "relativeVolume": relative_volume,
                    "unusualVolumePercent": calculate_unusual_volume_percent(volume, average_volume),
                    "dollarVolume": calculate_dollar_volume(price, volume),
                    "marketCap": to_float(_get_value(row, "Market Cap", "marketCap")),
                    "floatShares": to_float(_get_value(row, "Float Shares", "floatShares")),
                    "shortInterestPercentFloat": to_float(_get_value(row, "Short Interest % Float", "shortInterestPercentFloat")),
                    "session": "Regular Market",
                    "direction": _direction(change_pct),
                    "catalyst": "Volume anomaly" if (relative_volume or 0) >= 2 else "No catalyst detected",
                    "signal": classify_move_signal(change_pct, relative_volume),
                    "volumeAnomaly": classify_volume_anomaly(relative_volume),
                    "universe": universe_type,
                    "quoteType": _get_value(row, "Quote Type", "quoteType") or "",
                    "isWatchlistTicker": ticker in watchlist,
                    "source": _get_value(row, "Source", "source") or "Yahoo Finance/yfinance",
                    "lastUpdated": _get_value(row, "Last Updated", "lastUpdated") or now_et(),
                }
            )
        return pd.DataFrame(rows)

    def _enrich_filter_metadata(self, frame: pd.DataFrame, universe_type: str, watchlist: set[str]) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        needs_metadata = universe_type in {"nyse", "nasdaq", "amex", "large_cap", "mid_cap", "small_cap", "micro_cap"}
        if not needs_metadata:
            return frame
        output = frame.copy()
        for idx, row in output.head(80).iterrows():
            needs_exchange = universe_type in {"nyse", "nasdaq", "amex"} and str(row.get("exchange") or "N/A") == "N/A"
            needs_cap = universe_type in {"large_cap", "mid_cap", "small_cap", "micro_cap"} and to_float(row.get("marketCap")) is None
            if not needs_exchange and not needs_cap:
                continue
            quote = fetch_quote(str(row.get("ticker") or ""))
            if quote.get("status") != "OK":
                continue
            enriched = _row_from_quote(quote, universe_type, watchlist)
            for key in ("companyName", "exchange", "sector", "industry", "theme", "marketCap", "quoteType", "averageVolume", "source", "lastUpdated"):
                value = enriched.get(key)
                if value not in (None, "", "N/A") or key in {"exchange", "marketCap", "quoteType"}:
                    output.at[idx, key] = value
        return output

    def _apply_filters(self, frame: pd.DataFrame, filters: ScannerFilters) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        output = frame.copy()
        output = output[output["currentPrice"].fillna(0) >= float(filters.min_price or 0)]
        output = output[output["dollarVolume"].fillna(0) >= float(filters.min_dollar_volume or 0)]
        output = output[output["priceChangePercent"].abs().fillna(0) >= float(filters.min_move_pct or 0)]
        output = output[output["relativeVolume"].fillna(0) >= float(filters.min_relative_volume or 0)]
        output = output[output["unusualVolumePercent"].fillna(-10_000) >= float(filters.min_unusual_volume_pct or 0)]

        if filters.min_market_cap:
            known_cap = output["marketCap"].notna()
            output = output[(~known_cap) | (output["marketCap"] >= float(filters.min_market_cap))]

        if filters.universe_type == "nyse":
            output = output[output["exchange"].str.contains("NYSE", case=False, na=False)]
        elif filters.universe_type == "nasdaq":
            output = output[output["exchange"].str.contains("Nasdaq", case=False, na=False)]
        elif filters.universe_type == "amex":
            output = output[output["exchange"].str.contains("AMEX", case=False, na=False)]
        elif filters.universe_type == "large_cap":
            output = output[output["marketCap"].fillna(0) >= 10_000_000_000]
        elif filters.universe_type == "mid_cap":
            output = output[(output["marketCap"].fillna(0) >= 2_000_000_000) & (output["marketCap"].fillna(0) < 10_000_000_000)]
        elif filters.universe_type == "small_cap":
            output = output[(output["marketCap"].fillna(0) >= 300_000_000) & (output["marketCap"].fillna(0) < 2_000_000_000)]
        elif filters.universe_type == "micro_cap":
            output = output[(output["marketCap"].fillna(0) > 0) & (output["marketCap"].fillna(0) < 300_000_000)]

        if not filters.include_etfs and "quoteType" in output.columns:
            output = output[~output["quoteType"].astype(str).str.contains("ETF|FUND", case=False, na=False)]
            output = output[~output["ticker"].isin(ETF_TICKERS)]

        if filters.direction == "Gainers":
            output = output[output["priceChangePercent"] > 0]
        elif filters.direction == "Losers":
            output = output[output["priceChangePercent"] < 0]

        if filters.theme and filters.theme != "All":
            output = output[
                output["theme"].astype(str).str.casefold().eq(filters.theme.casefold())
                | output["sector"].astype(str).str.casefold().eq(filters.theme.casefold())
            ]
        return output.reset_index(drop=True)

    def _summary(
        self,
        all_results: pd.DataFrame,
        gainers: pd.DataFrame,
        losers: pd.DataFrame,
        unusual: pd.DataFrame,
        watchlist_alerts: pd.DataFrame,
    ) -> dict:
        if all_results is None or all_results.empty:
            return {
                "highVolumeGainers": 0,
                "highVolumeLosers": 0,
                "unusualVolumeLeaders": 0,
                "watchlistAlerts": 0,
                "marketBreadth": 0.0,
                "advancers": 0,
                "decliners": 0,
            }
        advancers = int((all_results["priceChangePercent"] > 0).sum())
        decliners = int((all_results["priceChangePercent"] < 0).sum())
        total_directional = advancers + decliners
        breadth = (advancers / total_directional * 100) if total_directional else 0.0
        return {
            "highVolumeGainers": len(gainers),
            "highVolumeLosers": len(losers),
            "unusualVolumeLeaders": len(unusual),
            "watchlistAlerts": len(watchlist_alerts),
            "marketBreadth": breadth,
            "advancers": advancers,
            "decliners": decliners,
        }

    def _universe_label(self, universe_type: str) -> str:
        for label, value in UNIVERSE_OPTIONS.items():
            if value == universe_type:
                return label
        return "All U.S. Stocks"
