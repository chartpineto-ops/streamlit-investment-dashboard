from __future__ import annotations

import pandas as pd
import streamlit as st

from data.company_identity import get_company_identity
from data.market_data import fetch_quote
from data.market_universe import market_universe
from data.news import fetch_news
from data.options import fetch_options_summary
from utils.formatting import clean_ticker, now_et, to_float


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
def scan_market_movers(
    min_move_pct: float = 5.0,
    max_results: int = 50,
    include_etfs: bool = True,
    extra_tickers: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, dict]:
    threshold = abs(float(min_move_pct or 5.0))
    rows = []
    errors = []
    for symbol in market_universe(include_etfs=include_etfs, extra_tickers=list(extra_tickers)):
        try:
            quote = fetch_quote(symbol)
            move = to_float(quote.get("daily_change_pct"))
            if move is None or abs(move) < threshold:
                continue
            avg_volume = to_float(quote.get("average_volume"))
            volume = to_float(quote.get("volume"))
            news, _ = fetch_news(symbol, 8)
            options = fetch_options_summary(symbol, quote.get("price"))
            rows.append(
                {
                    "Ticker": symbol,
                    "Company": quote.get("company_name") or symbol,
                    "Price": quote.get("price"),
                    "Daily Move %": move,
                    "Volume": volume,
                    "Relative Volume": volume / avg_volume if volume is not None and avg_volume not in (None, 0) else None,
                    "Market Cap": quote.get("market_cap"),
                    "Sector": quote.get("sector") or "N/A",
                    "Source": quote.get("source", "Yahoo Finance/yfinance"),
                    "Last Updated": quote.get("last_updated"),
                    "Catalyst / News Count": int(len(news)) if isinstance(news, pd.DataFrame) else 0,
                    "Options Available": options.get("status", "N/A"),
                }
            )
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["_abs_move"] = frame["Daily Move %"].abs()
        frame = frame.sort_values("_abs_move", ascending=False).drop(columns=["_abs_move"]).head(max_results)
    status = {
        "Source": "Cached fallback market universe + Yahoo Finance/yfinance quotes",
        "Status": "OK" if errors == [] else "Partial",
        "Last Updated": now_et(),
        "Error": "; ".join(errors[:5]),
        "Universe Size": len(market_universe(include_etfs=include_etfs, extra_tickers=list(extra_tickers))),
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
