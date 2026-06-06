from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import streamlit as st
import yfinance as yf

from data.company_identity import get_company_identity
from data.market_data import get_market_session_et
from utils.formatting import now_et, to_float


HORIZON_DAYS = {"1D": 1, "5D": 5, "1M": 21, "3M": 63}
HORIZON_KEYS = {"1D": "return_1d", "5D": "return_5d", "1M": "return_1m", "3M": "return_3m"}


SECTOR_UNIVERSE = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLC": "Communication Services",
    "XLB": "Materials",
    "SMH": "Semiconductors",
    "IGV": "Software",
}

SECTOR_BASKETS = {
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM"],
    "XLF": ["JPM", "BAC", "WFC", "GS", "MS", "BLK"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "TMO", "DHR"],
    "XLI": ["GE", "CAT", "ETN", "RTX", "PH", "PWR"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"],
    "XLU": ["NEE", "SO", "DUK", "AEP", "XEL", "CEG"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "LOW", "BKNG"],
    "XLP": ["WMT", "COST", "PG", "KO", "PEP", "PM"],
    "XLC": ["META", "GOOGL", "NFLX", "DIS", "T", "VZ"],
    "XLB": ["LIN", "FCX", "NUE", "SHW", "DD", "APD"],
    "SMH": ["NVDA", "AVGO", "AMD", "MRVL", "MU", "TSM"],
    "IGV": ["MSFT", "CRM", "NOW", "ADBE", "SNOW", "ORCL"],
}

THEME_BASKETS = {
    "AI Infrastructure": ["NVDA", "AVGO", "MRVL", "ANET", "VRT", "CRWV"],
    "Power & Grid": ["CEG", "VST", "PWR", "ETN", "GEV", "NRG"],
    "Nuclear": ["CEG", "VST", "CCJ", "BWXT", "SMR", "OKLO"],
    "Defense": ["LMT", "RTX", "NOC", "GD", "AVAV", "KTOS"],
    "Rare Earths": ["MP", "UUUU", "REMX", "LAC", "ALB", "FCX"],
    "Cybersecurity": ["CRWD", "PANW", "FTNT", "ZS", "OKTA", "CYBR"],
    "Quantum": ["IONQ", "RGTI", "QBTS", "QUBT", "IBM", "GOOGL"],
    "Robotics": ["ISRG", "TER", "ROK", "ABB", "SYM", "PATH"],
    "Cloud": ["MSFT", "AMZN", "GOOGL", "ORCL", "CRM", "NOW"],
    "Data Centers": ["VRT", "ANET", "EQIX", "DLR", "MRVL", "AVGO"],
}

BENEFICIARY_BASKETS = {SECTOR_UNIVERSE[symbol]: tickers for symbol, tickers in SECTOR_BASKETS.items()}

COMPANY_NAMES = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "WFC": "Wells Fargo",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "BLK": "BlackRock",
    "LLY": "Eli Lilly",
    "UNH": "UnitedHealth",
    "ABBV": "AbbVie",
    "TMO": "Thermo Fisher",
    "DHR": "Danaher",
    "GE": "GE Aerospace",
    "CAT": "Caterpillar",
    "ETN": "Eaton",
    "RTX": "RTX",
    "PH": "Parker-Hannifin",
    "PWR": "Quanta Services",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    "SLB": "SLB",
    "EOG": "EOG Resources",
    "MPC": "Marathon Petroleum",
    "NEE": "NextEra Energy",
    "SO": "Southern Company",
    "DUK": "Duke Energy",
    "AEP": "American Electric Power",
    "XEL": "Xcel Energy",
    "CEG": "Constellation Energy",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "HD": "Home Depot",
    "MCD": "McDonald's",
    "LOW": "Lowe's",
    "BKNG": "Booking Holdings",
    "WMT": "Walmart",
    "COST": "Costco",
    "PG": "Procter & Gamble",
    "KO": "Coca-Cola",
    "PEP": "PepsiCo",
    "PM": "Philip Morris",
    "META": "Meta Platforms",
    "GOOGL": "Alphabet",
    "NFLX": "Netflix",
    "DIS": "Disney",
    "T": "AT&T",
    "VZ": "Verizon",
    "LIN": "Linde",
    "FCX": "Freeport-McMoRan",
    "NUE": "Nucor",
    "SHW": "Sherwin-Williams",
    "DD": "DuPont",
    "APD": "Air Products",
    "AMD": "Advanced Micro Devices",
    "MRVL": "Marvell Technology",
    "MU": "Micron",
    "TSM": "Taiwan Semiconductor",
    "NOW": "ServiceNow",
    "ADBE": "Adobe",
    "SNOW": "Snowflake",
}

MARQUEE_ASSETS = {
    "SPY": ("SPY", "equity"),
    "QQQ": ("QQQ", "equity"),
    "DIA": ("DIA", "equity"),
    "IWM": ("IWM", "equity"),
    "^VIX": ("VIX", "index"),
    "^TNX": ("10Y", "yield"),
    "BTC-USD": ("BTC", "crypto"),
    "ETH-USD": ("ETH", "crypto"),
    "GC=F": ("Gold", "commodity"),
    "SI=F": ("Silver", "commodity"),
    "HG=F": ("Copper", "commodity"),
    "CL=F": ("WTI", "commodity"),
    "DX-Y.NYB": ("DXY", "index"),
    "^MOVE": ("MOVE", "index"),
}


@dataclass(frozen=True)
class GroupMetric:
    symbol: str
    name: str
    return_1d: float | None
    return_5d: float | None
    return_1m: float | None
    return_3m: float | None
    period_return: float | None
    prior_period_return: float | None
    relative_volume: float | None
    breadth: float | None
    dollar_volume_change: float | None
    dollar_volume: float | None
    persistence: float | None


def _all_symbols() -> tuple[str, ...]:
    values = set(MARQUEE_ASSETS) | set(SECTOR_UNIVERSE)
    for basket in [*SECTOR_BASKETS.values(), *THEME_BASKETS.values(), *BENEFICIARY_BASKETS.values()]:
        values.update(basket)
    return tuple(sorted(values))


def _symbol_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()
    frame = pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        if symbol in downloaded.columns.get_level_values(0):
            frame = downloaded[symbol]
        elif symbol in downloaded.columns.get_level_values(-1):
            frame = downloaded.xs(symbol, axis=1, level=-1)
    elif len(_all_symbols()) == 1:
        frame = downloaded
    if frame is None or frame.empty:
        return pd.DataFrame()
    keep = [column for column in ("Open", "High", "Low", "Close", "Volume") if column in frame]
    return frame[keep].dropna(how="all")


@st.cache_data(ttl=300, show_spinner=False)
def _download_market_history(symbols: tuple[str, ...], refresh_token: int = 0) -> tuple[dict[str, pd.DataFrame], str]:
    del refresh_token
    try:
        downloaded = yf.download(
            list(symbols),
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
        history = {symbol: _symbol_frame(downloaded, symbol) for symbol in symbols}
        return history, ""
    except Exception as exc:
        return {symbol: pd.DataFrame() for symbol in symbols}, str(exc)


@st.cache_data(ttl=45, show_spinner=False)
def _download_marquee_intraday(symbols: tuple[str, ...], refresh_token: int = 0) -> tuple[dict[str, pd.DataFrame], str]:
    del refresh_token
    try:
        downloaded = yf.download(
            list(symbols),
            period="5d",
            interval="5m",
            prepost=True,
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
        history = {symbol: _symbol_frame(downloaded, symbol) for symbol in symbols}
        return history, ""
    except Exception as exc:
        return {symbol: pd.DataFrame() for symbol in symbols}, str(exc)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column, pd.Series(dtype=float)), errors="coerce").dropna()


def _pct_change(latest: float | None, prior: float | None) -> float | None:
    if latest is None or prior in (None, 0):
        return None
    return ((latest / prior) - 1) * 100


def _quote_from_history(symbol: str, frame: pd.DataFrame) -> dict[str, object]:
    close = _numeric(frame, "Close")
    volume = _numeric(frame, "Volume")
    if close.empty:
        return {"symbol": symbol, "status": "Missing"}
    latest = to_float(close.iloc[-1])
    previous = to_float(close.iloc[-2]) if len(close) > 1 else None
    five_day_prior = to_float(close.iloc[-6]) if len(close) > 5 else None
    one_month_prior = to_float(close.iloc[-22]) if len(close) > 21 else None
    three_month_prior = to_float(close.iloc[-64]) if len(close) > 63 else None
    prior_1d = _pct_change(to_float(close.iloc[-2]), to_float(close.iloc[-3])) if len(close) > 2 else None
    prior_5d = _pct_change(to_float(close.iloc[-2]), to_float(close.iloc[-7])) if len(close) > 6 else None
    prior_1m = _pct_change(to_float(close.iloc[-2]), to_float(close.iloc[-23])) if len(close) > 22 else None
    prior_3m = _pct_change(to_float(close.iloc[-2]), to_float(close.iloc[-65])) if len(close) > 64 else None
    latest_volume = to_float(volume.iloc[-1]) if not volume.empty else None
    average_volume = to_float(volume.tail(20).mean()) if not volume.empty else None
    relative_volume = latest_volume / average_volume if latest_volume is not None and average_volume not in (None, 0) else None
    dollar_volume = latest * latest_volume if latest is not None and latest_volume is not None else None
    historical_dollar_volume = close.reindex(volume.index).mul(volume).dropna()
    average_dollar_volume = to_float(historical_dollar_volume.tail(20).mean()) if not historical_dollar_volume.empty else None
    dollar_volume_change = _pct_change(dollar_volume, average_dollar_volume)
    recent_returns = close.pct_change().dropna().tail(5)
    persistence = float((recent_returns > 0).mean() * 100) if not recent_returns.empty else None
    high_252 = to_float(close.tail(252).max())
    low_252 = to_float(close.tail(252).min())
    latest_timestamp = frame.index[-1] if len(frame.index) else now_et()
    return {
        "symbol": symbol,
        "price": latest,
        "previous_close": previous,
        "dollar_change": latest - previous if latest is not None and previous is not None else None,
        "return_1d": _pct_change(latest, previous),
        "return_5d": _pct_change(latest, five_day_prior),
        "return_1m": _pct_change(latest, one_month_prior),
        "return_3m": _pct_change(latest, three_month_prior),
        "prior_return_1d": prior_1d,
        "prior_return_5d": prior_5d,
        "prior_return_1m": prior_1m,
        "prior_return_3m": prior_3m,
        "volume": latest_volume,
        "average_volume_20d": average_volume,
        "relative_volume": relative_volume,
        "dollar_volume": dollar_volume,
        "dollar_volume_change": dollar_volume_change,
        "persistence": persistence,
        "above_20d": bool(latest >= close.tail(20).mean()) if latest is not None and len(close) >= 20 else None,
        "above_50d": bool(latest >= close.tail(50).mean()) if latest is not None and len(close) >= 50 else None,
        "above_200d": bool(latest >= close.tail(200).mean()) if latest is not None and len(close) >= 200 else None,
        "new_high": bool(high_252 and latest and latest >= high_252 * 0.995),
        "new_low": bool(low_252 and latest and latest <= low_252 * 1.005),
        "last_updated": latest_timestamp,
        "status": "OK",
    }


def _tracked_stock_symbols() -> set[str]:
    symbols: set[str] = set()
    for basket in [*SECTOR_BASKETS.values(), *THEME_BASKETS.values(), *BENEFICIARY_BASKETS.values()]:
        symbols.update(basket)
    return symbols


def get_market_snapshot(refresh_token: int = 0) -> dict[str, object]:
    symbols = _all_symbols()
    history, error = _download_market_history(symbols, refresh_token)
    quotes = {symbol: _quote_from_history(symbol, frame) for symbol, frame in history.items()}
    market_session = get_market_session_et()
    extended_moves: dict[str, dict[str, object]] = {}
    if market_session.get("label") in {"PRE", "AH"}:
        intraday, intraday_error = _download_marquee_intraday(tuple(MARQUEE_ASSETS), refresh_token)
        if intraday_error and not error:
            error = intraday_error
        for symbol, frame in intraday.items():
            close = _numeric(frame, "Close")
            latest = to_float(close.iloc[-1]) if not close.empty else None
            quote = quotes.get(symbol, {})
            comparison = quote.get("previous_close") if market_session.get("label") == "PRE" else quote.get("price")
            extended_moves[symbol] = {
                "session_label": market_session.get("label"),
                "session_price": latest,
                "session_dollar_change": latest - comparison if latest is not None and comparison is not None else None,
                "session_change_pct": _pct_change(latest, comparison),
            }
    loaded = [symbol for symbol, quote in quotes.items() if quote.get("status") == "OK"]
    missing = [symbol for symbol in symbols if symbol not in loaded]
    stocks = _tracked_stock_symbols()
    movers = [quotes[symbol] for symbol in stocks if quotes.get(symbol, {}).get("return_1d") is not None]
    top_gainer = max(movers, key=lambda row: float(row.get("return_1d") or 0), default=None)
    top_loser = min(movers, key=lambda row: float(row.get("return_1d") or 0), default=None)
    marquee = []
    for symbol, (label, asset_type) in MARQUEE_ASSETS.items():
        quote = quotes.get(symbol, {})
        marquee.append({**quote, **extended_moves.get(symbol, {}), "display_symbol": label, "asset_type": asset_type})
    if top_gainer:
        marquee.append({**top_gainer, "display_symbol": f'Top + {top_gainer["symbol"]}', "asset_type": "mover"})
    if top_loser:
        marquee.append({**top_loser, "display_symbol": f'Top - {top_loser["symbol"]}', "asset_type": "mover"})
    completeness = len(loaded) / len(symbols) * 100 if symbols else 0
    return {
        "quotes": quotes,
        "history": history,
        "marquee": marquee,
        "status": {
            "provider": "Yahoo Finance/yfinance batch history",
            "status": "OK" if completeness >= 90 else "Partial" if loaded else "Unavailable",
            "symbols_loaded": len(loaded),
            "symbols_missing": len(missing),
            "missing_symbols": missing,
            "completeness": completeness,
            "last_refresh": now_et(),
            "error": error,
            "market_session": market_session,
        },
    }


def _mean(values: Iterable[object]) -> float | None:
    numbers = [number for value in values if (number := to_float(value)) is not None]
    return sum(numbers) / len(numbers) if numbers else None


def _basket_breadth(snapshot: dict[str, object], basket: Iterable[str], field: str = "return_1d") -> float | None:
    quotes = snapshot.get("quotes", {})
    values = [to_float(quotes.get(symbol, {}).get(field)) for symbol in basket]
    valid = [value for value in values if value is not None]
    return sum(value > 0 for value in valid) / len(valid) * 100 if valid else None


def _horizon_key(horizon: str) -> str:
    return HORIZON_KEYS.get(horizon, "return_5d")


def _horizon_persistence(frame: pd.DataFrame, horizon: str) -> float | None:
    close = _numeric(frame, "Close")
    days = HORIZON_DAYS.get(horizon, 5)
    returns = close.pct_change().dropna().tail(days)
    return float((returns > 0).mean() * 100) if not returns.empty else None


def _group_metric(snapshot: dict[str, object], symbol: str, name: str, basket: Iterable[str], horizon: str) -> GroupMetric:
    quote = snapshot.get("quotes", {}).get(symbol, {})
    period_key = _horizon_key(horizon)
    return GroupMetric(
        symbol=symbol,
        name=name,
        return_1d=to_float(quote.get("return_1d")),
        return_5d=to_float(quote.get("return_5d")),
        return_1m=to_float(quote.get("return_1m")),
        return_3m=to_float(quote.get("return_3m")),
        period_return=to_float(quote.get(period_key)),
        prior_period_return=to_float(quote.get(f"prior_{period_key}")),
        relative_volume=to_float(quote.get("relative_volume")),
        breadth=_basket_breadth(snapshot, basket, period_key),
        dollar_volume_change=to_float(quote.get("dollar_volume_change")),
        dollar_volume=to_float(quote.get("dollar_volume")),
        persistence=_horizon_persistence(snapshot.get("history", {}).get(symbol, pd.DataFrame()), horizon),
    )


def _rank_normalize(series: pd.Series, low: float = -1.0, high: float = 1.0) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(0.0, index=series.index)
    ranks = numeric.rank(pct=True, method="average").fillna(0.5)
    return low + ranks * (high - low)


def calculate_flow_acceleration(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    current = pd.to_numeric(output.get("period_return"), errors="coerce").fillna(0)
    prior = pd.to_numeric(output.get("prior_period_return"), errors="coerce").fillna(0)
    output["return_acceleration"] = current - prior
    prior_flow = _rank_normalize(output.get("prior_period_return", pd.Series(index=output.index, dtype=float))) * 100
    output["prior_flow_score"] = prior_flow
    output["flow_acceleration"] = pd.to_numeric(output.get("flow_score"), errors="coerce").fillna(0) - prior_flow

    def acceleration_label(row: pd.Series) -> str:
        acceleration = to_float(row.get("flow_acceleration")) or 0.0
        period_return = to_float(row.get("period_return")) or 0.0
        prior_return = to_float(row.get("prior_period_return")) or 0.0
        if period_return > 0 >= prior_return or period_return < 0 <= prior_return:
            return "Reversing"
        if acceleration >= 20:
            return "Accelerating"
        if acceleration <= -20 and period_return < 0:
            return "Fading"
        if acceleration <= -20:
            return "Decelerating"
        return "Stable"

    output["acceleration_label"] = output.apply(acceleration_label, axis=1)
    return output


def calculate_institutional_score(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    inputs = {
        "flow_score": 0.22,
        "leadership_score": 0.18,
        "relative_volume": 0.13,
        "breadth": 0.13,
        "persistence": 0.11,
        "relative_strength_spy": 0.13,
        "flow_acceleration": 0.10,
    }
    score = pd.Series(0.0, index=output.index)
    for column, weight in inputs.items():
        values = output.get(column, pd.Series(0.0, index=output.index))
        score += _rank_normalize(values, 0, 100) * weight
    output["institutional_score"] = score.clip(0, 100)
    output["institutional_label"] = output["institutional_score"].apply(
        lambda value: "Institutional leadership"
        if value >= 85
        else "Strong accumulation"
        if value >= 70
        else "Watchlist quality"
        if value >= 50
        else "Weak confirmation"
        if value >= 30
        else "Avoid / capital flight"
    )
    return output


def calculate_flow_scores(snapshot: dict[str, object], horizon: str = "5D") -> pd.DataFrame:
    rows = [
        _group_metric(snapshot, symbol, name, SECTOR_BASKETS.get(symbol, []), horizon).__dict__
        for symbol, name in SECTOR_UNIVERSE.items()
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    components = {
        "period_return": 0.45,
        "return_1d": 0.10,
        "relative_volume": 0.20,
        "breadth": 0.15,
        "dollar_volume_change": 0.10,
    }
    score = pd.Series(0.0, index=frame.index)
    for column, weight in components.items():
        score += _rank_normalize(frame[column]) * weight
    frame["flow_score"] = (score * 100).clip(-100, 100)
    frame["estimated_flow_proxy"] = (
        pd.to_numeric(frame["dollar_volume"], errors="coerce").fillna(0)
        * pd.to_numeric(frame["period_return"], errors="coerce").fillna(0)
        / 100
        * pd.to_numeric(frame["relative_volume"], errors="coerce").fillna(1).clip(lower=0.25)
    )
    frame["horizon"] = horizon
    return calculate_flow_acceleration(frame)


def calculate_sector_leadership_scores(sectors: pd.DataFrame, snapshot: dict[str, object], horizon: str = "5D") -> pd.DataFrame:
    if sectors is None or sectors.empty:
        return pd.DataFrame()
    frame = sectors.copy()
    spy_period = to_float(snapshot.get("quotes", {}).get("SPY", {}).get(_horizon_key(horizon))) or 0.0
    frame["relative_strength_spy"] = pd.to_numeric(frame["period_return"], errors="coerce") - spy_period
    inputs = {
        "period_return": 0.22,
        "relative_strength_spy": 0.20,
        "relative_volume": 0.15,
        "breadth": 0.18,
        "persistence": 0.12,
        "flow_score": 0.13,
    }
    leadership = pd.Series(0.0, index=frame.index)
    for column, weight in inputs.items():
        leadership += _rank_normalize(frame[column], 0, 100) * weight
    frame["leadership_score"] = leadership.clip(0, 100)
    frame["leadership_label"] = frame["leadership_score"].apply(_leadership_label)
    frame["trend"] = frame.apply(
        lambda row: "Rising" if (to_float(row.get("return_1d")) or 0) > 0 and (to_float(row.get("period_return")) or 0) > 0
        else "Falling" if (to_float(row.get("return_1d")) or 0) < 0 and (to_float(row.get("period_return")) or 0) < 0
        else "Mixed",
        axis=1,
    )
    frame["flow_label"] = frame["flow_score"].apply(_flow_label)
    return calculate_institutional_score(frame).sort_values("flow_score", ascending=False).reset_index(drop=True)


def _flow_label(score: object) -> str:
    value = to_float(score) or 0.0
    if value >= 60:
        return "Strong inflow"
    if value >= 20:
        return "Moderate inflow"
    if value <= -60:
        return "Strong outflow"
    if value <= -20:
        return "Moderate outflow"
    return "Neutral"


def _leadership_label(score: object) -> str:
    value = to_float(score) or 0.0
    if value >= 90:
        return "Market Leadership"
    if value >= 70:
        return "Strong Leadership"
    if value >= 50:
        return "Neutral"
    if value >= 30:
        return "Weak"
    return "Capital Flight"


def _regime_label(score: float) -> str:
    if score >= 55:
        return "Strong risk-on"
    if score >= 20:
        return "Moderate risk-on"
    if score <= -55:
        return "Strong risk-off"
    if score <= -20:
        return "Moderate risk-off"
    return "Neutral"


def calculate_market_regime(snapshot: dict[str, object], sectors: pd.DataFrame, horizon: str = "5D") -> dict[str, object]:
    quotes = snapshot.get("quotes", {})
    benchmark_1d = _mean(quotes.get(symbol, {}).get("return_1d") for symbol in ("SPY", "QQQ", "IWM")) or 0.0
    period_key = _horizon_key(horizon)
    prior_key = f"prior_{period_key}"
    benchmark_period = _mean(quotes.get(symbol, {}).get(period_key) for symbol in ("SPY", "QQQ", "IWM")) or 0.0
    prior_1d = _mean(quotes.get(symbol, {}).get("prior_return_1d") for symbol in ("SPY", "QQQ", "IWM")) or 0.0
    prior_period = _mean(quotes.get(symbol, {}).get(prior_key) for symbol in ("SPY", "QQQ", "IWM")) or 0.0
    vix_level = to_float(quotes.get("^VIX", {}).get("price"))
    vix_change = to_float(quotes.get("^VIX", {}).get("return_1d")) or 0.0
    prior_vix_change = to_float(quotes.get("^VIX", {}).get("prior_return_1d")) or 0.0
    yield_change = to_float(quotes.get("^TNX", {}).get("return_1d")) or 0.0
    breadth = calculate_market_breadth(snapshot)
    advancer_pct = to_float(breadth.get("advancer_pct")) or 50.0
    positive_sector_pct = float((sectors["flow_score"] > 0).mean() * 100) if sectors is not None and not sectors.empty else 50.0
    vix_score = 25 if vix_level is not None and vix_level < 16 else -25 if vix_level is not None and vix_level > 25 else 0
    risk_score = (
        benchmark_1d * 8
        + benchmark_period * 4
        - vix_change * 1.5
        - yield_change * 0.5
        + (advancer_pct - 50) * 0.45
        + (positive_sector_pct - 50) * 0.35
        + vix_score
    )
    previous_score = prior_1d * 8 + prior_period * 4 - prior_vix_change * 1.5 + vix_score
    risk_score = max(-100, min(100, risk_score))
    previous_score = max(-100, min(100, previous_score))
    trend = "Improving" if risk_score > previous_score + 5 else "Deteriorating" if risk_score < previous_score - 5 else "Stable"
    explanation = (
        f"{positive_sector_pct:.0f}% of tracked groups have positive flow scores; "
        f"benchmark momentum is {benchmark_period:+.1f}% over {horizon} and tracked-stock breadth is {advancer_pct:.0f}%."
    )
    return {
        "regime": _regime_label(risk_score),
        "previous_regime": _regime_label(previous_score),
        "trend": trend,
        "risk_score": risk_score,
        "explanation": explanation,
        "horizon": horizon,
    }


def calculate_market_breadth(snapshot: dict[str, object]) -> dict[str, object]:
    quotes = snapshot.get("quotes", {})
    rows = [quotes.get(symbol, {}) for symbol in _tracked_stock_symbols()]
    loaded = [row for row in rows if row.get("status") == "OK"]
    count = len(loaded)
    if not count:
        return {
            "tracked": 0,
            "above_20d": None,
            "above_50d": None,
            "above_200d": None,
            "advancers": 0,
            "decliners": 0,
            "advancer_pct": None,
            "new_highs": 0,
            "new_lows": 0,
            "health": "Unavailable",
        }
    pct = lambda field: sum(row.get(field) is True for row in loaded) / count * 100
    advancers = sum((to_float(row.get("return_1d")) or 0) > 0 for row in loaded)
    decliners = sum((to_float(row.get("return_1d")) or 0) < 0 for row in loaded)
    above_50d = pct("above_50d")
    health = "Healthy" if above_50d >= 60 else "Deteriorating" if above_50d < 40 else "Mixed"
    return {
        "tracked": count,
        "above_20d": pct("above_20d"),
        "above_50d": above_50d,
        "above_200d": pct("above_200d"),
        "advancers": advancers,
        "decliners": decliners,
        "advancer_pct": advancers / max(1, advancers + decliners) * 100,
        "new_highs": sum(row.get("new_high") is True for row in loaded),
        "new_lows": sum(row.get("new_low") is True for row in loaded),
        "health": health,
    }


def _theme_metrics(snapshot: dict[str, object], horizon: str = "5D") -> pd.DataFrame:
    quotes = snapshot.get("quotes", {})
    period_key = _horizon_key(horizon)
    prior_key = f"prior_{period_key}"
    rows = []
    for name, basket in THEME_BASKETS.items():
        available = [quotes.get(symbol, {}) for symbol in basket if quotes.get(symbol, {}).get("status") == "OK"]
        rows.append(
            {
                "name": name,
                "symbol": "Basket",
                "return_1d": _mean(row.get("return_1d") for row in available),
                "return_5d": _mean(row.get("return_5d") for row in available),
                "period_return": _mean(row.get(period_key) for row in available),
                "prior_period_return": _mean(row.get(prior_key) for row in available),
                "relative_volume": _mean(row.get("relative_volume") for row in available),
                "breadth": _basket_breadth(snapshot, basket, period_key),
                "dollar_volume_change": _mean(row.get("dollar_volume_change") for row in available),
                "persistence": _mean(_horizon_persistence(snapshot.get("history", {}).get(symbol, pd.DataFrame()), horizon) for symbol in basket),
                "loaded": len(available),
                "basket_size": len(basket),
                "top_movers": ", ".join(
                    row["symbol"]
                    for row in sorted(available, key=lambda item: float(item.get("return_1d") or -999), reverse=True)[:3]
                ),
            }
        )
    return pd.DataFrame(rows)


def identify_emerging_themes(snapshot: dict[str, object], horizon: str = "5D") -> pd.DataFrame:
    frame = _theme_metrics(snapshot, horizon)
    if frame.empty:
        return frame
    spy_return = to_float(snapshot.get("quotes", {}).get("SPY", {}).get(_horizon_key(horizon))) or 0.0
    frame["relative_strength_spy"] = pd.to_numeric(frame["period_return"], errors="coerce") - spy_return
    score = (
        _rank_normalize(frame["period_return"]) * 0.45
        + _rank_normalize(frame["return_1d"]) * 0.10
        + _rank_normalize(frame["relative_volume"]) * 0.20
        + _rank_normalize(frame["breadth"]) * 0.15
        + _rank_normalize(frame["dollar_volume_change"]) * 0.10
    )
    frame["flow_score"] = (score * 100).clip(-100, 100)
    frame = calculate_flow_acceleration(frame)
    frame["leadership_score"] = (
        _rank_normalize(frame["flow_score"], 0, 100) * 0.35
        + _rank_normalize(frame["relative_strength_spy"], 0, 100) * 0.25
        + _rank_normalize(frame["relative_volume"], 0, 100) * 0.15
        + _rank_normalize(frame["breadth"], 0, 100) * 0.15
        + _rank_normalize(frame["persistence"], 0, 100) * 0.10
    ).clip(0, 100)
    frame["momentum"] = frame["acceleration_label"]
    completeness = frame["loaded"] / frame["basket_size"].clip(lower=1)
    frame["confidence"] = (
        completeness * 55
        + pd.to_numeric(frame["relative_volume"], errors="coerce").fillna(1).clip(0, 2) / 2 * 20
        + pd.to_numeric(frame["breadth"], errors="coerce").fillna(50) / 100 * 25
    ).clip(0, 100)
    frame["horizon"] = horizon
    return calculate_institutional_score(frame).sort_values("flow_score", ascending=False).reset_index(drop=True)


def identify_beneficiaries(sectors: pd.DataFrame, snapshot: dict[str, object], horizon: str = "5D") -> list[dict[str, object]]:
    if sectors is None or sectors.empty:
        return []
    quotes = snapshot.get("quotes", {})
    period_key = _horizon_key(horizon)
    spy_return = to_float(quotes.get("SPY", {}).get(period_key)) or 0.0
    output = []
    for _, sector in sectors.head(4).iterrows():
        sector_name = str(sector["name"])
        sector_return = to_float(sector.get("period_return")) or 0.0
        candidates = []
        for symbol in BENEFICIARY_BASKETS.get(sector_name, []):
            quote = quotes.get(symbol, {})
            stock_return = to_float(quote.get(period_key))
            if stock_return is None:
                continue
            relative_spy = stock_return - spy_return
            relative_sector = stock_return - sector_return
            volume_confirmed = (to_float(quote.get("relative_volume")) or 0) >= 1.05
            confirmation = min(relative_spy, relative_sector)
            confidence = max(
                0,
                min(
                    100,
                    45
                    + (to_float(sector.get("flow_score")) or 0) * 0.25
                    + confirmation * 6
                    + ((to_float(quote.get("relative_volume")) or 1) - 1) * 15,
                ),
            )
            candidates.append(
                {
                    "ticker": symbol,
                    "company": COMPANY_NAMES.get(symbol, symbol),
                    "period_return": stock_return,
                    "relative_spy": relative_spy,
                    "relative_sector": relative_sector,
                    "relative_volume": to_float(quote.get("relative_volume")),
                    "confidence": confidence,
                    "reason": (
                        "Volume confirmed"
                        if confirmation > 0 and volume_confirmed
                        else "Outperforming sector"
                        if relative_sector > 0
                        else "Outperforming SPY"
                        if relative_spy > 0
                        else "Weak confirmation"
                        if confirmation < -1
                        else "Watch only"
                    ),
                }
            )
        top_candidates = sorted(candidates, key=lambda row: row["confidence"], reverse=True)[:3]
        for candidate in top_candidates:
            identity = get_company_identity(str(candidate["ticker"]))
            candidate["company"] = identity.get("company_name") or candidate["company"]
            candidate["logo_url"] = identity.get("logo_data_uri") or identity.get("logo_url")
            candidate["fallback_initials"] = identity.get("fallback_initials") or str(candidate["ticker"])[:2]
        output.append(
            {
                "theme": sector_name,
                "flow_score": to_float(sector.get("flow_score")) or 0.0,
                "beneficiaries": top_candidates,
            }
        )
    return output


def _group_memberships(sectors: pd.DataFrame, themes: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    memberships: dict[str, list[dict[str, object]]] = {}
    if sectors is not None and not sectors.empty:
        for _, row in sectors.iterrows():
            for ticker in SECTOR_BASKETS.get(str(row.get("symbol")), []):
                memberships.setdefault(ticker, []).append({**row.to_dict(), "group_type": "Sector"})
    if themes is not None and not themes.empty:
        for _, row in themes.iterrows():
            for ticker in THEME_BASKETS.get(str(row.get("name")), []):
                memberships.setdefault(ticker, []).append({**row.to_dict(), "group_type": "Theme"})
    return memberships


def _candidate_stock_rows(
    sectors: pd.DataFrame,
    themes: pd.DataFrame,
    snapshot: dict[str, object],
    horizon: str,
    strongest_parent: bool,
) -> pd.DataFrame:
    quotes = snapshot.get("quotes", {})
    period_key = _horizon_key(horizon)
    prior_key = f"prior_{period_key}"
    spy_return = to_float(quotes.get("SPY", {}).get(period_key)) or 0.0
    rows = []
    for ticker, parents in _group_memberships(sectors, themes).items():
        quote = quotes.get(ticker, {})
        stock_return = to_float(quote.get(period_key))
        if stock_return is None:
            continue
        parent = sorted(parents, key=lambda row: to_float(row.get("institutional_score")) or 0.0, reverse=strongest_parent)[0]
        prior_return = to_float(quote.get(prior_key)) or 0.0
        parent_return = to_float(parent.get("period_return")) or 0.0
        rows.append(
            {
                "ticker": ticker,
                "company": COMPANY_NAMES.get(ticker, ticker),
                "parent": parent.get("name"),
                "group_type": parent.get("group_type"),
                "parent_flow_score": to_float(parent.get("flow_score")) or 0.0,
                "parent_institutional_score": to_float(parent.get("institutional_score")) or 0.0,
                "parent_breadth": to_float(parent.get("breadth")) or 0.0,
                "period_return": stock_return,
                "prior_period_return": prior_return,
                "return_acceleration": stock_return - prior_return,
                "relative_spy": stock_return - spy_return,
                "relative_parent": stock_return - parent_return,
                "relative_volume": to_float(quote.get("relative_volume")) or 0.0,
            }
        )
    return pd.DataFrame(rows)


def calculate_opportunity_scores(
    sectors: pd.DataFrame,
    themes: pd.DataFrame,
    snapshot: dict[str, object],
    horizon: str = "5D",
) -> pd.DataFrame:
    frame = _candidate_stock_rows(sectors, themes, snapshot, horizon, True)
    if frame.empty:
        return frame
    frame["institutional_score"] = (
        _rank_normalize(frame["parent_flow_score"], 0, 100) * 0.18
        + _rank_normalize(frame["parent_institutional_score"], 0, 100) * 0.24
        + _rank_normalize(frame["relative_spy"], 0, 100) * 0.17
        + _rank_normalize(frame["relative_parent"], 0, 100) * 0.13
        + _rank_normalize(frame["relative_volume"], 0, 100) * 0.11
        + _rank_normalize(frame["parent_breadth"], 0, 100) * 0.09
        + _rank_normalize(frame["return_acceleration"], 0, 100) * 0.08
    ).clip(0, 100)
    score = (
        frame["institutional_score"] * 0.55
        + _rank_normalize(frame["parent_flow_score"], 0, 100) * 0.14
        + _rank_normalize(frame["period_return"], 0, 100) * 0.11
        + _rank_normalize(frame["relative_spy"], 0, 100) * 0.12
        + _rank_normalize(frame["return_acceleration"], 0, 100) * 0.08
    )
    frame["opportunity_score"] = score.clip(0, 100)

    def opportunity_tag(row: pd.Series) -> str:
        if (to_float(row.get("relative_volume")) or 0) >= 1.25 and (to_float(row.get("relative_spy")) or 0) > 0:
            return "Volume confirmed"
        if (to_float(row.get("parent_flow_score")) or 0) >= 50 and (to_float(row.get("relative_parent")) or 0) > 0:
            return "Flow confirmed"
        if str(row.get("group_type")) == "Theme" and (to_float(row.get("relative_parent")) or 0) > 0:
            return "Theme leader"
        if (to_float(row.get("relative_parent")) or 0) > 0:
            return "Sector leader"
        if (to_float(row.get("return_acceleration")) or 0) > 0:
            return "Watch breakout"
        return "Defensive leader"

    frame["tag"] = frame.apply(opportunity_tag, axis=1)
    frame = frame.sort_values("opportunity_score", ascending=False).reset_index(drop=True)
    for index in frame.head(8).index:
        identity = get_company_identity(str(frame.at[index, "ticker"]))
        frame.at[index, "company"] = identity.get("company_name") or frame.at[index, "company"]
        frame.at[index, "logo_url"] = identity.get("logo_data_uri") or identity.get("logo_url")
        frame.at[index, "fallback_initials"] = identity.get("fallback_initials") or str(frame.at[index, "ticker"])[:2]
    return frame


def calculate_risk_scores(
    sectors: pd.DataFrame,
    themes: pd.DataFrame,
    snapshot: dict[str, object],
    horizon: str = "5D",
) -> pd.DataFrame:
    stocks = _candidate_stock_rows(sectors, themes, snapshot, horizon, False)
    group_frames = []
    for frame, group_type in ((sectors, "Sector"), (themes, "Theme")):
        if frame is not None and not frame.empty:
            group = frame.copy()
            group["ticker"] = group.get("symbol", "Basket")
            group["company"] = group["name"]
            group["parent"] = group["name"]
            group["group_type"] = group_type
            group["parent_flow_score"] = group["flow_score"]
            group["parent_institutional_score"] = group["institutional_score"]
            group["parent_breadth"] = group["breadth"]
            group["relative_spy"] = group["relative_strength_spy"]
            group["relative_parent"] = 0.0
            group["return_acceleration"] = group["return_acceleration"]
            group_frames.append(group[stocks.columns] if not stocks.empty else group)
    candidates = pd.concat(([stocks] if not stocks.empty else []) + group_frames, ignore_index=True, sort=False)
    if candidates.empty:
        return candidates
    down_volume = pd.to_numeric(candidates["relative_volume"], errors="coerce").fillna(0) * (
        pd.to_numeric(candidates["period_return"], errors="coerce").fillna(0) < 0
    )
    score = (
        _rank_normalize(-pd.to_numeric(candidates["parent_flow_score"], errors="coerce"), 0, 100) * 0.22
        + _rank_normalize(-pd.to_numeric(candidates["relative_spy"], errors="coerce"), 0, 100) * 0.19
        + _rank_normalize(-pd.to_numeric(candidates["relative_parent"], errors="coerce"), 0, 100) * 0.12
        + _rank_normalize(-pd.to_numeric(candidates["period_return"], errors="coerce"), 0, 100) * 0.16
        + _rank_normalize(down_volume, 0, 100) * 0.12
        + _rank_normalize(-pd.to_numeric(candidates["parent_breadth"], errors="coerce"), 0, 100) * 0.10
        + _rank_normalize(-pd.to_numeric(candidates["return_acceleration"], errors="coerce"), 0, 100) * 0.09
    )
    candidates["risk_score"] = score.clip(0, 100)

    def risk_tag(row: pd.Series) -> str:
        if (to_float(row.get("parent_flow_score")) or 0) <= -55:
            return "Capital flight"
        if (to_float(row.get("relative_volume")) or 0) >= 1.25 and (to_float(row.get("period_return")) or 0) < 0:
            return "High-volume selloff"
        if (to_float(row.get("parent_breadth")) or 50) < 35:
            return "Weak breadth"
        if (to_float(row.get("return_acceleration")) or 0) < -2:
            return "Losing leadership"
        if (to_float(row.get("relative_spy")) or 0) < -2:
            return "Breakdown watch"
        return "Avoid for now"

    candidates["tag"] = candidates.apply(risk_tag, axis=1)
    return candidates.sort_values("risk_score", ascending=False).reset_index(drop=True)


def generate_market_drivers(
    sectors: pd.DataFrame,
    themes: pd.DataFrame,
    snapshot: dict[str, object],
    breadth: dict[str, object],
    regime: dict[str, object],
) -> list[str]:
    if sectors is None or sectors.empty:
        return ["Live market drivers are unavailable until the sector snapshot refreshes."]
    sector_index = sectors.set_index("name")
    theme_index = themes.set_index("name") if themes is not None and not themes.empty else pd.DataFrame()
    quotes = snapshot.get("quotes", {})
    drivers: list[str] = []
    defensive = _mean(sector_index.loc[name, "flow_score"] for name in ("Healthcare", "Consumer Staples", "Utilities") if name in sector_index.index) or 0.0
    growth = _mean(sector_index.loc[name, "flow_score"] for name in ("Software", "Technology", "Semiconductors") if name in sector_index.index) or 0.0
    if defensive > growth + 20:
        drivers.append("Defensive rotation is strengthening as Healthcare, Staples, and Utilities outperform high-beta growth.")
    if "Financials" in sector_index.index and (to_float(sector_index.loc["Financials", "flow_score"]) or 0) > 20 and (to_float(quotes.get("^TNX", {}).get("return_1d")) or 0) > 0:
        drivers.append("Rising Treasury yields are confirming relative strength in Financials.")
    if "Energy" in sector_index.index and (to_float(sector_index.loc["Energy", "flow_score"]) or 0) > 20 and (to_float(quotes.get("CL=F", {}).get("return_1d")) or 0) > 0:
        drivers.append("Energy leadership is being confirmed by positive oil-price momentum.")
    if "Semiconductors" in sector_index.index and (to_float(sector_index.loc["Semiconductors", "flow_score"]) or 0) < -20 and (to_float(sector_index.loc["Semiconductors", "relative_volume"]) or 0) > 1.05:
        drivers.append("Semiconductors are experiencing above-normal selling pressure and losing relative leadership.")
    if not theme_index.empty and "Data Centers" in theme_index.index and "AI Infrastructure" in theme_index.index:
        if (to_float(theme_index.loc["Data Centers", "flow_score"]) or 0) > (to_float(theme_index.loc["AI Infrastructure", "flow_score"]) or 0) + 20:
            drivers.append("Data Center demand remains resilient even as broader AI Infrastructure momentum fades.")
    drivers.append(str(breadth.get("interpretation") or "Breadth confirmation remains mixed."))
    if len(drivers) < 3:
        drivers.append(str(regime.get("explanation") or "The market regime remains balanced."))
    if len(drivers) < 3:
        leader = sectors.iloc[0]
        drivers.append(
            f'{leader["name"]} has the strongest current combination of flow, breadth, and relative performance versus SPY.'
        )
    return drivers[:6]


def generate_money_going_next(sectors: pd.DataFrame, themes: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    combined = []
    for frame, group_type in ((sectors, "Sector"), (themes, "Theme")):
        if frame is not None and not frame.empty:
            copy = frame.copy()
            copy["group_type"] = group_type
            combined.append(copy)
    if not combined:
        return {"emerging": [], "losing": []}
    frame = pd.concat(combined, ignore_index=True, sort=False)

    def rows(source: pd.DataFrame, rising: bool) -> list[dict[str, object]]:
        output = []
        for _, row in source.head(5).iterrows():
            acceleration = to_float(row.get("flow_acceleration")) or 0.0
            confidence = min(
                100.0,
                max(
                    0.0,
                    (to_float(row.get("institutional_score")) or 0) * 0.55
                    + min(100, abs(acceleration)) * 0.25
                    + (to_float(row.get("persistence")) or 50) * 0.20,
                ),
            )
            output.append(
                {
                    "name": row.get("name"),
                    "group_type": row.get("group_type"),
                    "current_score": to_float(row.get("flow_score")) or 0.0,
                    "acceleration": acceleration,
                    "confidence": confidence,
                    "reason": (
                        "Flow, breadth, and relative strength are improving."
                        if rising
                        else "Flow momentum and relative strength are deteriorating."
                    ),
                }
            )
        return output

    emerging = frame.sort_values(["flow_acceleration", "relative_strength_spy"], ascending=False)
    losing = frame.sort_values(["flow_acceleration", "relative_strength_spy"], ascending=True)
    return {"emerging": rows(emerging, True), "losing": rows(losing, False)}


def _history_metric(frame: pd.DataFrame, offset: int, period_days: int = 5) -> dict[str, float | None]:
    close = _numeric(frame, "Close")
    volume = _numeric(frame, "Volume")
    if len(close) < offset + period_days + 2:
        return {}
    position = len(close) - 1 - offset
    latest = to_float(close.iloc[position])
    prior = to_float(close.iloc[position - 1])
    period_prior = to_float(close.iloc[position - period_days])
    latest_volume = to_float(volume.iloc[position]) if len(volume) > position else None
    avg_volume = to_float(volume.iloc[max(0, position - 20):position].mean()) if not volume.empty else None
    return {
        "return_1d": _pct_change(latest, prior),
        "period_return": _pct_change(latest, period_prior),
        "relative_volume": latest_volume / avg_volume if latest_volume is not None and avg_volume not in (None, 0) else None,
    }


def build_rotation_persistence(snapshot: dict[str, object], horizon: str = "5D", sessions: int = 10) -> pd.DataFrame:
    history = snapshot.get("history", {})
    spy = history.get("SPY", pd.DataFrame())
    dates = list(spy.index[-sessions:]) if spy is not None and not spy.empty else []
    period_days = HORIZON_DAYS.get(horizon, 5)
    matrix: dict[str, dict[str, float]] = {name: {} for name in SECTOR_UNIVERSE.values()}
    for offset, stamp in enumerate(reversed(dates)):
        rows = []
        for symbol, name in SECTOR_UNIVERSE.items():
            metric = _history_metric(history.get(symbol, pd.DataFrame()), offset, period_days)
            if metric:
                rows.append({"symbol": symbol, "name": name, **metric})
        frame = pd.DataFrame(rows)
        if frame.empty:
            continue
        score = _rank_normalize(frame["period_return"]) * 0.65 + _rank_normalize(frame["return_1d"]) * 0.15 + _rank_normalize(frame["relative_volume"]) * 0.20
        frame["score"] = score * 100
        date_label = pd.Timestamp(stamp).strftime("%b %d")
        for _, row in frame.iterrows():
            matrix[str(row["name"])][date_label] = float(row["score"])
    result = pd.DataFrame.from_dict(matrix, orient="index").dropna(how="all")
    return result.loc[:, list(reversed(result.columns))]


def build_rotation_timeline(snapshot: dict[str, object], horizon: str = "5D", sessions: int = 10) -> list[dict[str, object]]:
    persistence = build_rotation_persistence(snapshot, horizon, sessions)
    output = []
    for date_label in persistence.columns:
        leaders = persistence[date_label].dropna().sort_values(ascending=False).head(2)
        if leaders.empty:
            continue
        output.append(
            {
                "date": date_label,
                "leader": " + ".join(leaders.index.tolist()),
                "score": to_float(leaders.iloc[0]) or 0.0,
            }
        )
    return output


def generate_rotation_persistence_takeaway(
    persistence: pd.DataFrame,
    sectors: pd.DataFrame,
    regime: dict[str, object],
) -> dict[str, str]:
    if persistence is None or persistence.empty:
        return {"label": "Unstable rotation", "takeaway": "Historical leadership confirmation is unavailable."}
    first = persistence.iloc[:, 0].sort_values(ascending=False)
    latest = persistence.iloc[:, -1].sort_values(ascending=False)
    previous_leaders = first.head(2).index.tolist()
    latest_leaders = latest.head(2).index.tolist()
    common = len(set(previous_leaders) & set(latest_leaders))
    defensive = {"Healthcare", "Consumer Staples", "Utilities"}
    growth = {"Technology", "Software", "Semiconductors", "Consumer Discretionary"}
    if len(set(latest_leaders) & defensive) > len(set(previous_leaders) & defensive):
        label = "Defensive rotation"
    elif len(set(latest_leaders) & growth) > len(set(previous_leaders) & growth):
        label = "Growth leadership"
    elif common == 0:
        label = "Unstable rotation"
    elif common == len(latest_leaders):
        label = "Leadership narrowing"
    else:
        label = "Leadership broadening"
    return {
        "label": label,
        "takeaway": (
            f'Leadership has shifted from {" and ".join(previous_leaders)} toward {" and ".join(latest_leaders)} '
            f'over the latest sessions; the market regime is {str(regime.get("regime") or "neutral").lower()}.'
        ),
    }


def generate_sector_research_insights(
    sectors: pd.DataFrame,
    regime: dict[str, object],
    themes: pd.DataFrame,
    timeline: list[dict[str, object]],
    horizon: str = "5D",
) -> list[str]:
    if sectors is None or sectors.empty:
        return ["Sector data is unavailable; refresh when the market data provider is reachable."]
    leader = sectors.iloc[0]
    laggard = sectors.iloc[-1]
    insights = [
        f'{leader["name"]} leads capital rotation with a {float(leader["flow_score"]):+.0f} flow score and {float(leader["breadth"] or 0):.0f}% proxy breadth.',
        f'{laggard["name"]} is the weakest group at {float(laggard["flow_score"]):+.0f}, indicating relative capital pressure.',
        f'Market regime is {regime.get("regime", "Neutral").lower()} and the {horizon} risk trend is {str(regime.get("trend", "Stable")).lower()}.',
    ]
    if themes is not None and not themes.empty:
        theme = themes.iloc[0]
        insights.append(
            f'{theme["name"]} is the strongest emerging theme with {float(theme["flow_score"]):+.0f} flow and {float(theme["confidence"]):.0f}% confidence.'
        )
    if timeline:
        recent = [row["leader"] for row in timeline[-4:]]
        if recent and len(set(recent)) == 1:
            insights.append(f"{recent[0]} has held daily leadership for four consecutive tracked sessions.")
    return insights[:5]


def calculate_rotation_conviction(sectors: pd.DataFrame) -> dict[str, object]:
    if sectors is None or sectors.empty:
        return {"score": 0.0, "label": "Noise", "components": {}}
    breadth = pd.to_numeric(sectors["breadth"], errors="coerce").dropna()
    relative_volumes = pd.to_numeric(sectors["relative_volume"], errors="coerce").dropna()
    flow_scores = pd.to_numeric(sectors["flow_score"], errors="coerce").dropna()
    persistence_scores = pd.to_numeric(sectors["persistence"], errors="coerce").dropna()
    breadth_confirmation = min(100.0, float((breadth - 50).abs().mean() * 2)) if not breadth.empty else 0.0
    relative_volume = min(100.0, max(0.0, float((relative_volumes.mean() - 0.75) * 100))) if not relative_volumes.empty else 0.0
    dispersion = min(100.0, float(flow_scores.std(ddof=0) * 1.8)) if not flow_scores.empty else 0.0
    persistence = min(100.0, float((persistence_scores - 50).abs().mean() * 2)) if not persistence_scores.empty else 0.0
    positive = int((sectors["flow_score"] > 20).sum())
    negative = int((sectors["flow_score"] < -20).sum())
    confirmation = max(positive, negative) / max(1, len(sectors)) * 100
    top_bottom_gap = min(100.0, float((flow_scores.max() - flow_scores.min()) / 2)) if not flow_scores.empty else 0.0
    components = {
        "Breadth confirmation": breadth_confirmation,
        "Relative volume": relative_volume,
        "Leadership dispersion": dispersion,
        "Persistence": persistence,
        "Direction confirmation": confirmation,
        "Top / bottom gap": top_bottom_gap,
    }
    score = (
        breadth_confirmation * 0.20
        + relative_volume * 0.15
        + dispersion * 0.20
        + persistence * 0.15
        + confirmation * 0.15
        + top_bottom_gap * 0.15
    )
    label = "Very strong rotation" if score >= 80 else "Strong rotation" if score >= 60 else "Mixed rotation" if score >= 40 else "Weak signal" if score >= 20 else "Noise"
    return {"score": max(0.0, min(100.0, score)), "label": label, "components": components}


def generate_sector_research_brief(
    sectors: pd.DataFrame,
    regime: dict[str, object],
    conviction: dict[str, object],
    horizon: str = "5D",
) -> dict[str, object]:
    if sectors is None or sectors.empty:
        return {
            "regime": "Unavailable",
            "leader": "N/A",
            "laggard": "N/A",
            "direction": "Insufficient live data",
            "conviction": conviction,
            "takeaway": "Live sector rotation data is unavailable.",
        }
    leader = sectors.iloc[0]
    laggard = sectors.iloc[-1]
    direction = f'{laggard["name"]} to {leader["name"]}'
    risk_phrase = (
        "Risk appetite is improving."
        if "risk-on" in str(regime.get("regime", "")).casefold()
        else "Risk appetite is deteriorating."
        if "risk-off" in str(regime.get("regime", "")).casefold()
        else "Risk appetite is balanced."
    )
    return {
        "regime": regime.get("regime", "Neutral"),
        "leader": leader["name"],
        "laggard": laggard["name"],
        "direction": direction,
        "conviction": conviction,
        "takeaway": (
            f'Capital is rotating from {laggard["name"]} into {leader["name"]} over the selected {horizon} horizon. '
            f'{risk_phrase} Rotation conviction is {str(conviction.get("label", "noise")).lower()}.'
        ),
    }


def generate_what_this_means(sectors: pd.DataFrame, regime: dict[str, object], themes: pd.DataFrame) -> dict[str, object]:
    if sectors is None or sectors.empty:
        return {"favored": [], "pressured": [], "watchlist_impact": "Wait for a complete market refresh.", "risk_tone": "Unavailable"}
    favored = sectors.head(3)["name"].tolist()
    pressured = sectors.tail(3).sort_values("flow_score")["name"].tolist()
    if themes is not None and not themes.empty and to_float(themes.iloc[0].get("flow_score")) and float(themes.iloc[0]["flow_score"]) > 20:
        favored.append(str(themes.iloc[0]["name"]))
    risk_tone = str(regime.get("regime") or "Neutral")
    return {
        "favored": favored[:4],
        "pressured": pressured[:4],
        "watchlist_impact": f'Favor names confirming strength in {favored[0]}; review exposure tied to {pressured[0]}.',
        "risk_tone": risk_tone,
    }


def generate_breadth_interpretation(breadth: dict[str, object], sectors: pd.DataFrame) -> str:
    health = str(breadth.get("health") or "Unavailable").casefold()
    leader = str(sectors.iloc[0]["name"]) if sectors is not None and not sectors.empty else "leading groups"
    laggard = str(sectors.iloc[-1]["name"]) if sectors is not None and not sectors.empty else "weaker groups"
    if health == "healthy":
        return f"Breadth is healthy: participation supports leadership in {leader}."
    if health == "deteriorating":
        return f"Breadth is deteriorating: strength is narrow and {laggard} remains under pressure."
    if health == "mixed":
        return f"Breadth is mixed: {leader} is participating, but weakness in {laggard} limits confirmation."
    return "Breadth data is incomplete; treat the rotation read cautiously."


def generate_rotation_summary(sectors: pd.DataFrame, regime: dict[str, object], status: dict[str, object]) -> dict[str, object]:
    if sectors is None or sectors.empty:
        return {
            "key_takeaway": "Live sector rotation data is unavailable.",
            "inflow_proxy": 0.0,
            "outflow_proxy": 0.0,
            "net_rotation_proxy": 0.0,
            "regime": regime.get("regime", "Unavailable"),
            "last_refresh": status.get("last_refresh"),
        }
    leader = sectors.iloc[0]
    laggard = sectors.iloc[-1]
    inflow = float(sectors.loc[sectors["estimated_flow_proxy"] > 0, "estimated_flow_proxy"].sum())
    outflow = float(sectors.loc[sectors["estimated_flow_proxy"] < 0, "estimated_flow_proxy"].sum())
    return {
        "key_takeaway": (
            f'Capital is rotating from {laggard["name"]} toward {leader["name"]}; '
            f'{leader["name"]} has the strongest combination of price momentum, volume, and breadth.'
        ),
        "inflow_proxy": inflow,
        "outflow_proxy": outflow,
        "net_rotation_proxy": inflow + outflow,
        "regime": regime.get("regime", "Neutral"),
        "last_refresh": status.get("last_refresh"),
    }


def fetch_sector_data(snapshot: dict[str, object], horizon: str = "5D") -> pd.DataFrame:
    return calculate_sector_leadership_scores(calculate_flow_scores(snapshot, horizon), snapshot, horizon)


def build_sector_research_packet(snapshot: dict[str, object], horizon: str = "5D") -> dict[str, object]:
    sectors = fetch_sector_data(snapshot, horizon)
    breadth = calculate_market_breadth(snapshot)
    regime = calculate_market_regime(snapshot, sectors, horizon)
    themes = identify_emerging_themes(snapshot, horizon)
    beneficiaries = identify_beneficiaries(sectors, snapshot, horizon)
    timeline = build_rotation_timeline(snapshot, horizon)
    persistence = build_rotation_persistence(snapshot, horizon)
    persistence_takeaway = generate_rotation_persistence_takeaway(persistence, sectors, regime)
    conviction = calculate_rotation_conviction(sectors)
    brief = generate_sector_research_brief(sectors, regime, conviction, horizon)
    what_this_means = generate_what_this_means(sectors, regime, themes)
    breadth["interpretation"] = generate_breadth_interpretation(breadth, sectors)
    opportunities = calculate_opportunity_scores(sectors, themes, snapshot, horizon)
    risks = calculate_risk_scores(sectors, themes, snapshot, horizon)
    market_drivers = generate_market_drivers(sectors, themes, snapshot, breadth, regime)
    money_going_next = generate_money_going_next(sectors, themes)
    status = snapshot.get("status", {})
    completeness = to_float(status.get("completeness")) or 0.0
    breadth_available = breadth.get("tracked", 0) > 0
    confidence_score = completeness * 0.65 + (20 if breadth_available else 0) + (15 if not sectors.empty else 0)
    confidence = "High" if confidence_score >= 85 else "Medium" if confidence_score >= 60 else "Low"
    health = {**status, "confidence": confidence, "confidence_score": min(100, confidence_score)}
    return {
        "sectors": sectors,
        "breadth": breadth,
        "regime": regime,
        "themes": themes,
        "beneficiaries": beneficiaries,
        "opportunities": opportunities,
        "risks": risks,
        "market_drivers": market_drivers,
        "money_going_next": money_going_next,
        "timeline": timeline,
        "persistence": persistence,
        "persistence_takeaway": persistence_takeaway,
        "conviction": conviction,
        "brief": brief,
        "what_this_means": what_this_means,
        "horizon": horizon,
        "insights": generate_sector_research_insights(sectors, regime, themes, timeline, horizon),
        "summary": generate_rotation_summary(sectors, regime, status),
        "health": health,
    }
