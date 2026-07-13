from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st
import yfinance as yf

from data.sector_research import SECTOR_BASKETS, SECTOR_UNIVERSE, THEME_BASKETS
from utils.formatting import clean_ticker, now_et, to_float


PEER_GROUPS = (
    ({"battery", "electrical equipment", "energy storage", "silicon anode"}, ("ENVX", "QS", "SLDP", "SES", "AMPX")),
    ({"semiconductor", "custom silicon", "chip", "networking"}, ("NVDA", "AVGO", "AMD", "MRVL", "MU", "TSM")),
    ({"quantum"}, ("IONQ", "RGTI", "QBTS", "QUBT", "IBM")),
    ({"rare earth", "critical mineral", "mining"}, ("MP", "UUUU", "LAC", "ALB", "FCX")),
    ({"nuclear", "utility", "power producer"}, ("CEG", "VST", "NRG", "NEE", "SO")),
    ({"power electronics", "electronic component"}, ("VICR", "MPWR", "MCHP", "ON", "NXPI")),
    ({"software", "cloud"}, ("MSFT", "CRM", "NOW", "ADBE", "ORCL")),
    ({"cybersecurity"}, ("CRWD", "PANW", "FTNT", "ZS", "CYBR")),
    ({"defense", "aerospace"}, ("LMT", "RTX", "NOC", "GD", "AVAV")),
)


def _peer_symbols(symbol: str, sector: str, industry: str, themes: tuple[str, ...], limit: int = 4) -> tuple[str, ...]:
    text = " ".join([sector, industry, *themes]).casefold()
    candidates: list[str] = []
    for keywords, group in PEER_GROUPS:
        if any(keyword in text for keyword in keywords):
            candidates.extend(group)
            break
    if not candidates:
        for theme, basket in THEME_BASKETS.items():
            if theme.casefold() in text or any(token in text for token in theme.casefold().split()):
                candidates.extend(basket)
                break
    if not candidates:
        sector_etf = next((ticker for ticker, name in SECTOR_UNIVERSE.items() if name.casefold() == sector.casefold()), "")
        candidates.extend(SECTOR_BASKETS.get(sector_etf, ()))
    selected = clean_ticker(symbol)
    ordered = [selected, *(clean_ticker(value) for value in candidates)]
    return tuple(dict.fromkeys(value for value in ordered if value))[: limit + 1]


def _history_for_symbol(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        if symbol in downloaded.columns.get_level_values(0):
            return downloaded[symbol]
        if symbol in downloaded.columns.get_level_values(-1):
            return downloaded.xs(symbol, axis=1, level=-1)
    return downloaded


def _return(close: pd.Series, sessions: int) -> float | None:
    values = pd.to_numeric(close, errors="coerce").dropna()
    if len(values) <= sessions:
        if sessions >= 200 and len(values) >= 200:
            prior = to_float(values.iloc[0])
            latest = to_float(values.iloc[-1])
            return (latest / prior - 1) * 100 if latest is not None and prior not in (None, 0) else None
        return None
    latest = to_float(values.iloc[-1])
    prior = to_float(values.iloc[-sessions - 1])
    if latest is None or prior in (None, 0):
        return None
    return (latest / prior - 1) * 100


def _fundamental_snapshot(symbol: str) -> dict[str, object]:
    try:
        info = yf.Ticker(symbol).get_info() or {}
        market_cap = to_float(info.get("marketCap"))
        enterprise_value = to_float(info.get("enterpriseValue"))
        total_revenue = to_float(info.get("totalRevenue"))
        ebitda = to_float(info.get("ebitda"))
        free_cash_flow = to_float(info.get("freeCashflow"))
        total_cash = to_float(info.get("totalCash"))
        total_debt = to_float(info.get("totalDebt"))
        current_price = to_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        target_price = to_float(info.get("targetMeanPrice"))
        street_rating = str(info.get("recommendationKey") or "").strip()
        if street_rating.casefold() in {"none", "null", "nan"}:
            street_rating = ""
        ev_to_sales = to_float(info.get("enterpriseToRevenue"))
        if ev_to_sales is None and enterprise_value is not None and total_revenue not in (None, 0):
            ev_to_sales = enterprise_value / total_revenue
        ev_to_ebitda = to_float(info.get("enterpriseToEbitda"))
        if ev_to_ebitda is None and enterprise_value is not None and ebitda not in (None, 0):
            ev_to_ebitda = enterprise_value / ebitda
        return {
            "ticker": symbol,
            "company": info.get("shortName") or info.get("longName") or symbol,
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "revenue_ttm": total_revenue,
            "revenue_growth": to_float(info.get("revenueGrowth")),
            "earnings_growth": to_float(info.get("earningsGrowth")),
            "gross_margin": to_float(info.get("grossMargins")),
            "operating_margin": to_float(info.get("operatingMargins")),
            "fcf_yield": (free_cash_flow / market_cap * 100) if free_cash_flow is not None and market_cap not in (None, 0) else None,
            "return_on_equity": to_float(info.get("returnOnEquity")),
            "net_cash": (total_cash - total_debt) if total_cash is not None and total_debt is not None else None,
            "forward_pe": to_float(info.get("forwardPE")),
            "price_to_sales": to_float(info.get("priceToSalesTrailing12Months")),
            "ev_to_sales": ev_to_sales,
            "ev_to_ebitda": ev_to_ebitda,
            "target_price": target_price,
            "target_upside": ((target_price / current_price) - 1) * 100 if target_price is not None and current_price not in (None, 0) else None,
            "analyst_count": to_float(info.get("numberOfAnalystOpinions")),
            "street_rating": street_rating.replace("_", " ").title(),
            "beta": to_float(info.get("beta")),
            "status": "OK",
        }
    except Exception as exc:
        return {"ticker": symbol, "company": symbol, "status": "Unavailable", "error": str(exc)}


def _relative_read(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)

    def numeric_column(column: str) -> pd.Series:
        if column not in frame:
            return pd.Series(float("nan"), index=frame.index, dtype=float)
        return pd.to_numeric(frame[column], errors="coerce")

    score = pd.Series(0.0, index=frame.index)
    available = pd.Series(0.0, index=frame.index)
    for column, positive in (("return_3m", True), ("revenue_growth", True), ("gross_margin", True), ("operating_margin", True), ("fcf_yield", True), ("ev_to_sales", False)):
        values = numeric_column(column)
        valid = values.notna()
        if valid.sum() < 2:
            continue
        percentile = values.rank(pct=True)
        if not positive:
            percentile = 1 - percentile + (1 / valid.sum())
        score.loc[valid] += percentile.loc[valid]
        available.loc[valid] += 1
    normalized = score.div(available.where(available > 0)).mul(100)
    labels = normalized.apply(lambda value: "Leading" if pd.notna(value) and value >= 67 else "Competitive" if pd.notna(value) and value >= 45 else "Lagging" if pd.notna(value) else "Insufficient data")
    valuation_available = numeric_column("ev_to_sales").notna() | numeric_column("forward_pe").notna()
    decision_grade = (available >= 3) & (numeric_column("revenue_growth").notna() | valuation_available)
    return labels.where(decision_grade, "Insufficient data")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_competitive_intelligence(symbol: str, sector: str, industry: str, themes: tuple[str, ...]) -> tuple[pd.DataFrame, dict[str, object]]:
    tickers = _peer_symbols(symbol, sector, industry, themes)
    if not tickers:
        return pd.DataFrame(), {"status": "Unavailable", "source": "Yahoo Finance/yfinance", "last_updated": now_et()}
    try:
        downloaded = yf.download(list(tickers), period="1y", interval="1d", auto_adjust=False, progress=False, threads=True, group_by="ticker")
    except Exception:
        downloaded = pd.DataFrame()
    fundamentals: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=min(5, len(tickers))) as executor:
        futures = {executor.submit(_fundamental_snapshot, ticker): ticker for ticker in tickers}
        for future in as_completed(futures):
            row = future.result()
            fundamentals[str(row.get("ticker") or futures[future])] = row
    rows = []
    for ticker in tickers:
        row = dict(fundamentals.get(ticker) or {"ticker": ticker, "company": ticker, "status": "Unavailable"})
        history = _history_for_symbol(downloaded, ticker)
        close = history.get("Close", pd.Series(dtype=float)) if not history.empty else pd.Series(dtype=float)
        row.update({"return_1m": _return(close, 21), "return_3m": _return(close, 63), "return_1y": _return(close, 251)})
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame["relative_read"] = _relative_read(frame)
    loaded = int((frame.get("status") == "OK").sum()) if "status" in frame else 0
    return frame, {
        "status": "OK" if loaded == len(frame) else "Partial" if loaded else "Unavailable",
        "source": "Yahoo Finance/yfinance company fundamentals and daily history",
        "last_updated": now_et(),
        "symbols_loaded": loaded,
        "symbols_requested": len(frame),
    }
