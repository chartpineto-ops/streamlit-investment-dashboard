from __future__ import annotations

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from data.company_identity import get_company_identity
from data.market_data import fetch_quote
from data.market_universe import get_broad_market_universe_with_status, market_universe
from data.options import fetch_options_summary
from utils.formatting import clean_ticker, now_et, to_float


YAHOO_SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 PineTerminal/1.0",
    "Accept": "application/json,text/plain,*/*",
}


@st.cache_data(ttl=86_400, show_spinner=False)
def get_company_logo_url(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    if not symbol:
        return {"logo_url": None, "logo_data_uri": None, "fallback_initials": "PT", "logo_status": "Invalid ticker"}
    identity = get_company_identity(symbol)
    return {
        "logo_url": identity.get("logo_url"),
        "logo_data_uri": identity.get("logo_data_uri"),
        "fallback_initials": identity.get("fallback_initials") or symbol[:2],
        "logo_status": identity.get("logo_status"),
        "logo_source": identity.get("logo_source"),
    }


def _chunks(values: list[str], size: int = 150):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _history_for_symbol(downloaded: pd.DataFrame, symbol: str, chunk_size: int) -> pd.DataFrame:
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        if symbol in downloaded.columns.get_level_values(0):
            return downloaded[symbol].dropna(how="all")
        if symbol in downloaded.columns.get_level_values(-1):
            return downloaded.xs(symbol, axis=1, level=-1).dropna(how="all")
        return pd.DataFrame()
    return downloaded.dropna(how="all") if chunk_size == 1 else pd.DataFrame()


def _attach_logo_fields(frame: pd.DataFrame, max_rows: int = 80) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    enriched = frame.copy()
    for idx, row in enriched.head(max_rows).iterrows():
        symbol = clean_ticker(row.get("Ticker"))
        if not symbol:
            continue
        try:
            identity = get_company_identity(symbol)
            enriched.at[idx, "Company"] = identity.get("company_name") or row.get("Company") or symbol
            enriched.at[idx, "Sector"] = identity.get("sector") or row.get("Sector") or "N/A"
            enriched.at[idx, "Logo URL"] = identity.get("logo_url")
            enriched.at[idx, "Logo Data URI"] = identity.get("logo_data_uri")
            enriched.at[idx, "Fallback Initials"] = identity.get("fallback_initials") or symbol[:2]
        except Exception:
            enriched.at[idx, "Fallback Initials"] = symbol[:2]
    return enriched


def _empty_whole_market_packet(status: dict) -> dict:
    return {
        "gainers": pd.DataFrame(),
        "losers": pd.DataFrame(),
        "most_active": pd.DataFrame(),
        "unusual_volume": pd.DataFrame(),
        "all_scanned": pd.DataFrame(),
        "source_status": status,
    }


def _quote_value(item: dict, key: str):
    value = item.get(key)
    if isinstance(value, dict):
        return value.get("raw", value.get("fmt"))
    return value


def _is_allowed_yahoo_quote(item: dict, include_etfs: bool) -> bool:
    symbol = clean_ticker(item.get("symbol"))
    if not symbol:
        return False
    if any(symbol.endswith(suffix) for suffix in ("-W", "-WS", "-WT", "-U", "-R")):
        return False
    quote_type = str(item.get("quoteType") or "").upper()
    if include_etfs:
        return quote_type in {"EQUITY", "ETF", "MUTUALFUND"} or not quote_type
    return quote_type in {"EQUITY", ""} and str(item.get("typeDisp") or "").upper() not in {"ETF", "FUND"}


def _fetch_yahoo_screener(scr_id: str, count: int = 250) -> tuple[list[dict], dict]:
    params = {"scrIds": scr_id, "count": count, "start": 0, "formatted": "false", "lang": "en-US", "region": "US"}
    response = requests.get(YAHOO_SCREENER_URL, params=params, headers=YAHOO_HEADERS, timeout=12)
    response.raise_for_status()
    payload = response.json()
    result = ((payload.get("finance") or {}).get("result") or [{}])[0]
    return result.get("quotes") or [], {
        "count": result.get("count"),
        "total": result.get("total"),
        "start": result.get("start"),
    }


def _yahoo_quotes_to_frame(quotes: list[dict], include_etfs: bool, min_price: float, min_volume: int, updated) -> pd.DataFrame:
    rows = []
    for item in quotes:
        if not _is_allowed_yahoo_quote(item, include_etfs):
            continue
        symbol = clean_ticker(item.get("symbol"))
        price = to_float(_quote_value(item, "regularMarketPrice"))
        move = to_float(_quote_value(item, "regularMarketChangePercent"))
        volume = to_float(_quote_value(item, "regularMarketVolume"))
        market_cap = to_float(_quote_value(item, "marketCap"))
        if symbol == "" or price is None or move is None:
            continue
        if price < float(min_price or 0):
            continue
        if volume is not None and volume < int(min_volume or 0):
            continue
        average_volume = to_float(_quote_value(item, "averageDailyVolume3Month") or _quote_value(item, "averageDailyVolume10Day"))
        relative_volume = volume / average_volume if volume is not None and average_volume not in (None, 0) else None
        rows.append(
            {
                "Ticker": symbol,
                "Company": item.get("shortName") or item.get("longName") or symbol,
                "Price": price,
                "Daily Move %": move,
                "Volume": volume,
                "Relative Volume": relative_volume,
                "Market Cap": market_cap,
                "Sector": item.get("sector") or item.get("sectorDisp") or "N/A",
                "Source": "Yahoo Finance market movers feed",
                "Last Updated": updated,
            }
        )
    return pd.DataFrame(rows)


def _try_yahoo_whole_market_movers(min_price: float, min_volume: int, include_etfs: bool, updated) -> dict | None:
    errors = []
    try:
        gainer_quotes, gainer_meta = _fetch_yahoo_screener("day_gainers", count=250)
    except Exception as exc:
        errors.append(f"day_gainers: {exc}")
        gainer_quotes, gainer_meta = [], {}
    try:
        loser_quotes, loser_meta = _fetch_yahoo_screener("day_losers", count=250)
    except Exception as exc:
        errors.append(f"day_losers: {exc}")
        loser_quotes, loser_meta = [], {}
    try:
        active_quotes, active_meta = _fetch_yahoo_screener("most_actives", count=250)
    except Exception as exc:
        errors.append(f"most_actives: {exc}")
        active_quotes, active_meta = [], {}

    gainers = _yahoo_quotes_to_frame(gainer_quotes, include_etfs, min_price, min_volume, updated)
    losers = _yahoo_quotes_to_frame(loser_quotes, include_etfs, min_price, min_volume, updated)
    most_active = _yahoo_quotes_to_frame(active_quotes, include_etfs, min_price, min_volume, updated)
    if gainers.empty and losers.empty:
        return None

    gainers = gainers.sort_values("Daily Move %", ascending=False).head(10).reset_index(drop=True)
    losers = losers.sort_values("Daily Move %", ascending=True).head(10).reset_index(drop=True)
    most_active = most_active.sort_values("Volume", ascending=False).head(20).reset_index(drop=True) if not most_active.empty else pd.DataFrame()
    combined = pd.concat([gainers, losers, most_active], ignore_index=True).drop_duplicates("Ticker")
    if not combined.empty:
        combined["_abs_move"] = combined["Daily Move %"].abs()
        all_scanned = combined.sort_values("_abs_move", ascending=False).drop(columns=["_abs_move"]).reset_index(drop=True)
        unusual_volume = combined.sort_values("Relative Volume", ascending=False, na_position="last").head(20).reset_index(drop=True)
    else:
        all_scanned = pd.DataFrame()
        unusual_volume = pd.DataFrame()

    display_symbols = pd.concat([gainers, losers, most_active.head(5)], ignore_index=True).drop_duplicates("Ticker")
    enriched = _attach_logo_fields(display_symbols)
    enrich_map = {row.get("Ticker"): row.to_dict() for _, row in enriched.iterrows()} if not enriched.empty else {}

    def apply_enrichment(frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        output = frame.copy()
        for idx, row in output.iterrows():
            extra = enrich_map.get(row.get("Ticker"), {})
            for key in ("Company", "Sector", "Logo URL", "Logo Data URI", "Fallback Initials"):
                if extra.get(key):
                    output.at[idx, key] = extra.get(key)
        return output

    universe_total = max(
        int(gainer_meta.get("total") or len(gainer_quotes) or 0),
        int(loser_meta.get("total") or len(loser_quotes) or 0),
        int(active_meta.get("total") or len(active_quotes) or 0),
    )
    quotes_successful = len(pd.concat([gainers, losers, most_active], ignore_index=True).drop_duplicates("Ticker"))
    status = {
        "source": "Yahoo Finance market movers feed",
        "provider": "Yahoo Finance predefined market movers",
        "universe_source": "Yahoo Finance day_gainers/day_losers/most_actives",
        "universe_count": universe_total,
        "quotes_successful": quotes_successful,
        "quotes_failed": 0,
        "after_filters": quotes_successful,
        "last_updated": updated,
        "status": "OK" if not errors else "Partial",
        "message": "Current-session leaders from Yahoo Finance's broad U.S. market movers feed.",
        "error_summary": "; ".join(errors[:5]),
        "include_etfs": include_etfs,
        "min_price": min_price,
        "min_volume": min_volume,
        "gainers_feed_total": gainer_meta.get("total"),
        "losers_feed_total": loser_meta.get("total"),
        "most_active_feed_total": active_meta.get("total"),
    }
    return {
        "gainers": apply_enrichment(gainers),
        "losers": apply_enrichment(losers),
        "most_active": apply_enrichment(most_active),
        "unusual_volume": apply_enrichment(unusual_volume),
        "all_scanned": apply_enrichment(all_scanned),
        "source_status": status,
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_whole_market_movers(
    min_price: float = 2.0,
    min_volume: int = 500_000,
    max_universe_size: int = 5000,
    include_etfs: bool = False,
    refresh: bool = False,
) -> dict:
    del refresh
    updated = now_et()
    yahoo_packet = _try_yahoo_whole_market_movers(min_price, min_volume, include_etfs, updated)
    if yahoo_packet is not None:
        return yahoo_packet

    universe, universe_status = get_broad_market_universe_with_status(include_etfs=include_etfs)
    universe = universe[: max(1, int(max_universe_size or 5000))]
    errors: list[str] = []
    rows: list[dict] = []
    for chunk in _chunks(universe, 150):
        try:
            downloaded = yf.download(
                tickers=" ".join(chunk),
                period="1mo",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=True,
            )
        except Exception as exc:
            errors.append(f"batch {chunk[0]}-{chunk[-1]}: {exc}")
            continue
        for symbol in chunk:
            try:
                history = _history_for_symbol(downloaded, symbol, len(chunk))
                if history.empty or "Close" not in history or "Volume" not in history:
                    continue
                close = pd.to_numeric(history["Close"], errors="coerce").dropna()
                volume_series = pd.to_numeric(history["Volume"], errors="coerce").dropna()
                if len(close) < 2 or volume_series.empty:
                    continue
                price = to_float(close.iloc[-1])
                previous_close = to_float(close.iloc[-2])
                volume = to_float(volume_series.iloc[-1])
                if price is None or previous_close in (None, 0) or volume is None:
                    continue
                if price < float(min_price or 0) or volume < int(min_volume or 0):
                    continue
                move = ((price - previous_close) / abs(previous_close)) * 100
                avg_volume = to_float(volume_series.tail(20).mean())
                relative_volume = volume / avg_volume if avg_volume not in (None, 0) else None
                rows.append(
                    {
                        "Ticker": symbol,
                        "Company": symbol,
                        "Price": price,
                        "Daily Move %": move,
                        "Volume": volume,
                        "Relative Volume": relative_volume,
                        "Market Cap": None,
                        "Sector": "N/A",
                        "Source": "Yahoo Finance/yfinance batch quotes",
                        "Last Updated": updated,
                    }
                )
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")

    frame = pd.DataFrame(rows)
    if frame.empty:
        fallback = get_market_movers(
            min_move_pct=0,
            max_results=20,
            include_etfs=include_etfs,
            include_watchlist=False,
            min_volume=min_volume,
        )
        fallback_frame = fallback.get("all_movers", pd.DataFrame())
        fallback_status = fallback.get("source_status", {})
        status = {
            "source": "Fallback PineTerminal universe + Yahoo Finance/yfinance quotes",
            "provider": "Yahoo Finance/yfinance",
            "universe_source": "Fallback PineTerminal curated universe",
            "universe_count": len(universe),
            "quotes_successful": int(fallback_status.get("successful_quote_fetches", 0) or 0),
            "quotes_failed": int(fallback_status.get("failed_quote_fetches", 0) or 0),
            "after_filters": len(fallback_frame),
            "last_updated": updated,
            "status": "Fallback" if not fallback_frame.empty else "Error",
            "message": "Broad market scan unavailable. Showing fallback PineTerminal universe." if not fallback_frame.empty else "Broad market scan and fallback universe are unavailable.",
            "error_summary": "; ".join(errors[:8]),
            "include_etfs": include_etfs,
            "min_price": min_price,
            "min_volume": min_volume,
        }
        if fallback_frame.empty:
            return _empty_whole_market_packet(status)
        fallback_frame = fallback_frame.copy()
        fallback_frame["Source"] = fallback_frame.get("Source", "Yahoo Finance/yfinance quotes")
        fallback_frame = _attach_logo_fields(fallback_frame)
        return {
            "gainers": fallback_frame[fallback_frame["Daily Move %"] > 0].sort_values("Daily Move %", ascending=False).head(10).reset_index(drop=True),
            "losers": fallback_frame[fallback_frame["Daily Move %"] < 0].sort_values("Daily Move %", ascending=True).head(10).reset_index(drop=True),
            "most_active": fallback_frame.sort_values("Volume", ascending=False).head(20).reset_index(drop=True),
            "unusual_volume": fallback_frame.sort_values("Relative Volume", ascending=False).head(20).reset_index(drop=True),
            "all_scanned": fallback_frame.sort_values("Daily Move %", key=lambda s: s.abs(), ascending=False).reset_index(drop=True),
            "source_status": status,
        }

    frame["_abs_move"] = frame["Daily Move %"].abs()
    frame["_volume_sort"] = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0)
    frame["_rel_volume_sort"] = pd.to_numeric(frame["Relative Volume"], errors="coerce").fillna(0)
    gainers = frame[frame["Daily Move %"] > 0].sort_values("Daily Move %", ascending=False).head(10).reset_index(drop=True)
    losers = frame[frame["Daily Move %"] < 0].sort_values("Daily Move %", ascending=True).head(10).reset_index(drop=True)
    most_active = frame.sort_values("_volume_sort", ascending=False).head(20).reset_index(drop=True)
    unusual_volume = frame.sort_values(["_rel_volume_sort", "_abs_move"], ascending=[False, False]).head(20).reset_index(drop=True)
    all_scanned = frame.sort_values("_abs_move", ascending=False).drop(columns=["_abs_move", "_volume_sort", "_rel_volume_sort"]).reset_index(drop=True)

    display_symbols = pd.concat([gainers, losers, most_active.head(5), unusual_volume.head(5)], ignore_index=True)
    enriched = _attach_logo_fields(display_symbols.drop_duplicates("Ticker"))
    enrich_map = {row.get("Ticker"): row.to_dict() for _, row in enriched.iterrows()} if not enriched.empty else {}

    def apply_enrichment(source_frame: pd.DataFrame) -> pd.DataFrame:
        output = source_frame.drop(columns=[col for col in ["_abs_move", "_volume_sort", "_rel_volume_sort"] if col in source_frame.columns]).copy()
        for idx, row in output.iterrows():
            extra = enrich_map.get(row.get("Ticker"), {})
            for key in ("Company", "Sector", "Logo URL", "Logo Data URI", "Fallback Initials"):
                if extra.get(key):
                    output.at[idx, key] = extra.get(key)
        return output

    status = {
        "source": "Yahoo Finance/yfinance quotes + broad listed-stock universe",
        "provider": "Yahoo Finance/yfinance",
        "universe_source": universe_status.get("universe_source"),
        "universe_count": len(universe),
        "quotes_successful": len(frame),
        "quotes_failed": max(0, len(universe) - len(frame)),
        "after_filters": len(frame),
        "last_updated": updated,
        "status": "OK" if not errors else "Partial",
        "message": "Current-session leaders from broad U.S. listed-stock scan.",
        "error_summary": "; ".join(errors[:8]),
        "include_etfs": include_etfs,
        "min_price": min_price,
        "min_volume": min_volume,
        "universe_status": universe_status,
    }
    return {
        "gainers": apply_enrichment(gainers),
        "losers": apply_enrichment(losers),
        "most_active": apply_enrichment(most_active),
        "unusual_volume": apply_enrichment(unusual_volume),
        "all_scanned": all_scanned,
        "source_status": status,
    }


@st.cache_data(ttl=300, show_spinner=False)
def get_biggest_movers(
    limit: int = 10,
    include_etfs: bool = True,
    extra_tickers: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows = []
    errors = []
    universe = market_universe(include_etfs=include_etfs, extra_tickers=list(extra_tickers or ()))
    for symbol in universe:
        try:
            quote = fetch_quote(symbol)
            move = to_float(quote.get("daily_change_pct"))
            price = to_float(quote.get("price"))
            if move is None or price is None:
                continue
            logo = get_company_logo_url(symbol)
            rows.append(
                {
                    "Ticker": symbol,
                    "Company": quote.get("company_name") or symbol,
                    "Daily Move %": move,
                    "Price": price,
                    "Logo URL": logo.get("logo_url") or quote.get("logo_url"),
                    "Logo Data URI": logo.get("logo_data_uri") or quote.get("logo_data_uri"),
                    "Fallback Initials": logo.get("fallback_initials") or quote.get("fallback_initials") or symbol[:2],
                    "Source": quote.get("source", "Yahoo Finance/yfinance"),
                    "Last Updated": quote.get("last_updated"),
                    "Status": quote.get("status", "Unknown"),
                }
            )
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
    frame = pd.DataFrame(rows)
    if frame.empty:
        status = {
            "Source": "Yahoo Finance/yfinance",
            "Status": "Unavailable" if not errors else "Source error",
            "Last Updated": now_et(),
            "Error": "; ".join(errors[:5]),
            "Universe Size": len(universe),
        }
        return pd.DataFrame(), pd.DataFrame(), status
    gainers = frame[frame["Daily Move %"] > 0].sort_values("Daily Move %", ascending=False).head(limit).reset_index(drop=True)
    losers = frame[frame["Daily Move %"] < 0].sort_values("Daily Move %", ascending=True).head(limit).reset_index(drop=True)
    status = {
        "Source": "Yahoo Finance/yfinance",
        "Status": "OK" if not errors else "Partial",
        "Last Updated": now_et(),
        "Error": "; ".join(errors[:5]),
        "Universe Size": len(universe),
        "Rows": len(frame),
    }
    return gainers, losers, status


@st.cache_data(ttl=600, show_spinner=False)
def get_market_movers(
    min_move_pct: float = 5.0,
    max_results: int = 50,
    include_etfs: bool = True,
    include_watchlist: bool = True,
    extra_tickers: tuple[str, ...] = (),
    min_volume: float = 500_000,
    min_market_cap: float | None = None,
    check_options: bool = False,
) -> dict:
    threshold = abs(float(min_move_pct or 5.0))
    per_side = max(1, int(max_results or 50))
    min_volume_value = max(0.0, float(min_volume or 0))
    min_market_cap_value = to_float(min_market_cap)
    errors: list[str] = []
    watchlist_tickers: tuple[str, ...] = ()
    if include_watchlist:
        try:
            from storage.watchlist import list_watchlist

            watch = list_watchlist()
            watchlist_tickers = clean_mover_tickers(watch.get("ticker", pd.Series(dtype=str)).tolist())
        except Exception as exc:
            errors.append(f"watchlist: {exc}")

    extra = clean_mover_tickers([*(extra_tickers or ()), *watchlist_tickers])
    universe = market_universe(include_etfs=include_etfs, extra_tickers=list(extra))
    raw_rows = []
    quote_errors = []

    for symbol in universe:
        try:
            quote = fetch_quote(symbol)
            move = to_float(quote.get("daily_change_pct"))
            price = to_float(quote.get("price"))
            volume = to_float(quote.get("volume"))
            market_cap = to_float(quote.get("market_cap"))
            if move is None or price is None:
                quote_errors.append(f"{symbol}: quote unavailable")
                continue
            if volume is not None and volume < min_volume_value:
                continue
            if min_market_cap_value is not None and market_cap is not None and market_cap < min_market_cap_value:
                continue

            avg_volume = to_float(quote.get("average_volume"))
            relative_volume = volume / avg_volume if volume is not None and avg_volume not in (None, 0) else None
            dollar_volume = price * volume if price is not None and volume is not None else None
            option_status = "Not checked"
            if check_options:
                try:
                    option_status = fetch_options_summary(symbol, price).get("status", "Source unavailable")
                    if option_status == "OK":
                        option_status = "Options available"
                except Exception as exc:
                    option_status = "Error"
                    errors.append(f"{symbol} options: {exc}")
            raw_rows.append(
                {
                    "Ticker": symbol,
                    "Company": quote.get("company_name") or symbol,
                    "Price": price,
                    "Daily Move %": move,
                    "Volume": volume,
                    "Relative Volume": relative_volume,
                    "Dollar Volume": dollar_volume,
                    "Market Cap": market_cap,
                    "Sector": quote.get("sector") or "N/A",
                    "Source": quote.get("source", "Yahoo Finance/yfinance"),
                    "Last Updated": quote.get("last_updated"),
                    "Catalyst / News Count": None,
                    "Options": option_status,
                    "Is Watchlist": symbol in set(watchlist_tickers),
                }
            )
        except Exception as exc:
            quote_errors.append(f"{symbol}: {exc}")

    frame = pd.DataFrame(raw_rows)
    if frame.empty:
        status = {
            "provider": "Yahoo Finance/yfinance",
            "universe_source": "Bundled broad liquid US universe",
            "source": "Cached broad market universe + Yahoo Finance/yfinance quotes",
            "status": "Unavailable" if not raw_rows else "Source error",
            "last_updated": now_et(),
            "scanned_count": len(universe),
            "successful_quote_fetches": 0,
            "failed_quote_fetches": len(quote_errors),
            "error_summary": "; ".join([*errors, *quote_errors[:5]]),
            "threshold": threshold,
            "min_volume": min_volume_value,
        }
        return {
            "gainers": pd.DataFrame(),
            "losers": pd.DataFrame(),
            "unusual_volume": pd.DataFrame(),
            "all_movers": pd.DataFrame(),
            "watchlist_movers": pd.DataFrame(),
            "summary": {},
            "source_status": status,
            "last_updated": status["last_updated"],
            "scanned_count": len(universe),
            "error_summary": status["error_summary"],
        }

    working = frame.copy()
    working["_abs_move"] = working["Daily Move %"].abs()
    working["_rel_volume_sort"] = pd.to_numeric(working["Relative Volume"], errors="coerce").fillna(0)
    working["_volume_sort"] = pd.to_numeric(working["Volume"], errors="coerce").fillna(0)

    threshold_gainers = working[working["Daily Move %"] >= threshold].sort_values("Daily Move %", ascending=False)
    threshold_losers = working[working["Daily Move %"] <= -threshold].sort_values("Daily Move %", ascending=True)
    all_gainers = working[working["Daily Move %"] > 0].sort_values("Daily Move %", ascending=False)
    all_losers = working[working["Daily Move %"] < 0].sort_values("Daily Move %", ascending=True)

    gainers_note = ""
    losers_note = ""
    gainers = threshold_gainers
    losers = threshold_losers
    if len(gainers) < min(10, per_side):
        gainers_note = f"Only {len(threshold_gainers)} tickers met the +{threshold:.1f}% threshold. Showing top gainers from scanned universe for context."
        gainers = all_gainers
    if len(losers) < min(10, per_side):
        losers_note = f"Only {len(threshold_losers)} tickers met the -{threshold:.1f}% threshold. Showing top losers from scanned universe for context."
        losers = all_losers

    all_movers = working.sort_values("_abs_move", ascending=False)
    unusual_volume = working.sort_values(["_rel_volume_sort", "_abs_move"], ascending=[False, False])
    watchlist_movers = working[working["Is Watchlist"]].sort_values("_abs_move", ascending=False)

    visible_cols = [col for col in working.columns if not col.startswith("_")]
    gainers = gainers[visible_cols].head(per_side).reset_index(drop=True)
    losers = losers[visible_cols].head(per_side).reset_index(drop=True)
    all_movers = all_movers[visible_cols].head(max(per_side * 2, per_side)).reset_index(drop=True)
    unusual_volume = unusual_volume[visible_cols].head(per_side).reset_index(drop=True)
    watchlist_movers = watchlist_movers[visible_cols].head(per_side).reset_index(drop=True)

    top_gainer = all_gainers.iloc[0].to_dict() if not all_gainers.empty else {}
    top_loser = all_losers.iloc[0].to_dict() if not all_losers.empty else {}
    highest_volume = working.sort_values("_volume_sort", ascending=False).iloc[0].to_dict()
    highest_relative_volume = unusual_volume.iloc[0].to_dict() if not unusual_volume.empty else {}
    summary = {
        "gainers_at_threshold": int(len(threshold_gainers)),
        "losers_at_threshold": int(len(threshold_losers)),
        "median_move": to_float(working["Daily Move %"].median()),
        "top_gainer": top_gainer,
        "top_loser": top_loser,
        "highest_volume_mover": highest_volume,
        "highest_relative_volume_mover": highest_relative_volume,
        "gainers_note": gainers_note,
        "losers_note": losers_note,
    }
    status = {
        "provider": "Yahoo Finance/yfinance",
        "universe_source": "Bundled broad liquid US universe" + (" + watchlist" if include_watchlist else ""),
        "source": "Cached broad market universe + Yahoo Finance/yfinance quotes",
        "status": "OK" if not quote_errors and not errors else "Partial",
        "last_updated": now_et(),
        "scanned_count": len(universe),
        "successful_quote_fetches": len(frame),
        "failed_quote_fetches": len(quote_errors),
        "error_summary": "; ".join([*errors, *quote_errors[:8]]),
        "threshold": threshold,
        "min_volume": min_volume_value,
        "min_market_cap": min_market_cap_value,
        "include_etfs": include_etfs,
        "include_watchlist": include_watchlist,
    }
    return {
        "gainers": gainers,
        "losers": losers,
        "unusual_volume": unusual_volume,
        "all_movers": all_movers,
        "watchlist_movers": watchlist_movers,
        "summary": summary,
        "source_status": status,
        "last_updated": status["last_updated"],
        "scanned_count": len(universe),
        "error_summary": status["error_summary"],
    }


@st.cache_data(ttl=600, show_spinner=False)
def scan_market_movers(
    min_move_pct: float = 5.0,
    max_results: int = 50,
    include_etfs: bool = True,
    extra_tickers: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, dict]:
    packet = get_market_movers(
        min_move_pct=min_move_pct,
        max_results=max_results,
        include_etfs=include_etfs,
        include_watchlist=False,
        extra_tickers=clean_mover_tickers(extra_tickers),
        min_volume=0,
    )
    frame = packet.get("all_movers", pd.DataFrame())
    threshold = abs(float(min_move_pct or 5.0))
    if not frame.empty:
        frame = frame[frame["Daily Move %"].abs() >= threshold].head(max_results).reset_index(drop=True)
    raw_status = packet.get("source_status", {})
    status = {
        "Source": raw_status.get("source", "Cached broad market universe + Yahoo Finance/yfinance quotes"),
        "Status": raw_status.get("status", "Unknown"),
        "Last Updated": raw_status.get("last_updated", now_et()),
        "Error": raw_status.get("error_summary", ""),
        "Universe Size": raw_status.get("scanned_count", 0),
        "Rows": len(frame),
        "Threshold": threshold,
    }
    return frame, status


def clean_mover_tickers(values) -> tuple[str, ...]:
    output = []
    seen = set()
    for value in values or []:
        symbol = clean_ticker(value)
        if symbol and symbol not in seen:
            seen.add(symbol)
            output.append(symbol)
    return tuple(output)
