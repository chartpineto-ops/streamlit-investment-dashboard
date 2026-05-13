from __future__ import annotations

from datetime import date
from math import sqrt

import pandas as pd
import streamlit as st
import yfinance as yf

from utils.formatting import clean_ticker, now_et, to_float


def _option_for_days(obj: yf.Ticker, price: float | None, target_days: int) -> dict:
    if price is None:
        return {"status": "Options unavailable from source", "debug_error": "Missing price"}
    expiries = list(getattr(obj, "options", []) or [])
    if not expiries:
        return {"status": "No listed options", "debug_error": "No options expirations"}
    today = date.today()
    parsed = []
    for expiry in expiries:
        try:
            exp_date = pd.to_datetime(expiry).date()
            days = max((exp_date - today).days, 1)
            parsed.append((abs(days - target_days), days, expiry, exp_date))
        except Exception:
            continue
    if not parsed:
        return {"status": "No suitable expiration", "debug_error": "No valid options expirations"}
    _, days, expiry, exp_date = sorted(parsed)[0]
    try:
        chain = obj.option_chain(expiry)
        options = pd.concat([chain.calls.assign(side="call"), chain.puts.assign(side="put")], ignore_index=True)
        options["distance"] = (pd.to_numeric(options["strike"], errors="coerce") - price).abs()
        atm = options.sort_values("distance").head(4)
        iv = pd.to_numeric(atm["impliedVolatility"], errors="coerce").dropna()
        if iv.empty:
            return {"status": "No suitable ATM strike", "expiry": exp_date, "days": days, "debug_error": "ATM IV unavailable"}
        annual_iv = float(iv.mean())
        move_pct = annual_iv * sqrt(days / 365) * 100
        return {"status": "OK", "expiry": exp_date, "days": days, "annual_iv": annual_iv * 100, "implied_move_pct": move_pct, "atm_strike": float(atm.iloc[0]["strike"])}
    except Exception as exc:
        return {"status": "Source error", "expiry": exp_date, "days": days, "debug_error": str(exc)}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_options_summary(ticker: str, price: float | None = None) -> dict:
    symbol = clean_ticker(ticker)
    updated = now_et()
    if not symbol:
        return {"ticker": "", "status": "Error", "error": "Invalid ticker", "last_updated": updated}
    try:
        obj = yf.Ticker(symbol)
        if price is None:
            try:
                price = to_float((obj.fast_info or {}).get("last_price"))
            except Exception:
                price = None
        seven = _option_for_days(obj, price, 7)
        thirty = _option_for_days(obj, price, 30)
        status = "OK" if seven.get("status") == "OK" or thirty.get("status") == "OK" else seven.get("status") or thirty.get("status") or "Options unavailable from source"
        return {"ticker": symbol, "status": status, "seven_day": seven, "thirty_day": thirty, "source": "Yahoo Finance/yfinance options", "last_updated": updated}
    except Exception as exc:
        return {"ticker": symbol, "status": "Source error", "debug_error": str(exc), "source": "Yahoo Finance/yfinance options", "last_updated": updated}
