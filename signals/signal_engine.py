from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from data.financials import load_latest_company_financials
from data.market_data import fetch_history, fetch_quote
from data.news import fetch_news
from data.options import fetch_options_summary
from utils.formatting import clean_ticker, safe_div, to_float

WEIGHTS = {
    "growth_score": 0.20,
    "profitability_score": 0.15,
    "balance_sheet_score": 0.15,
    "valuation_score": 0.20,
    "momentum_score": 0.15,
    "catalyst_score": 0.15,
}


def _bounded(value: float | None, default: float = 50) -> float:
    if value is None or pd.isna(value):
        return default
    return max(0, min(100, float(value)))


def _score_growth(latest: dict) -> tuple[float, list[str], list[str]]:
    growth = to_float(latest.get("revenue_yoy_growth") or latest.get("revenue_qoq_growth"))
    if growth is None:
        return 45, [], ["Revenue growth unavailable"]
    base_effect = bool(latest.get("revenue_yoy_base_effect") or latest.get("revenue_qoq_base_effect") or abs(growth) > 500)
    score = 50 + min(max(growth, -50), 80) * 0.7
    if base_effect:
        score = min(score, 62)
    strengths = [f"Revenue growth is {growth:.1f}%"] if growth > 0 and not base_effect else []
    weaknesses = [f"Revenue growth is {growth:.1f}%"] if growth < 0 else []
    if base_effect:
        weaknesses.append("Revenue growth may be distorted by a small base")
    return _bounded(score), strengths, weaknesses


def _score_profitability(latest: dict) -> tuple[float, list[str], list[str]]:
    gross = to_float(latest.get("gross_margin"))
    op = to_float(latest.get("operating_margin"))
    net = to_float(latest.get("net_margin"))
    fcf = to_float(latest.get("free_cash_flow"))
    revenue = to_float(latest.get("revenue"))
    score = 40
    if gross is not None:
        score += min(max(gross, 0), 80) * 0.25
    if op is not None:
        score += min(max(op, -40), 40) * 0.45
    if net is not None:
        score += min(max(net, -40), 40) * 0.30
    if op is not None and op < 0:
        score -= 10
    if net is not None and net < 0:
        score -= 10
    if fcf is not None and fcf < 0:
        score -= 10
    strengths = []
    weaknesses = []
    if op is not None and op > 15:
        strengths.append("Operating margin is healthy")
    if net is not None and net < 0:
        weaknesses.append("Net margin is negative")
    if fcf is not None and fcf < 0:
        weaknesses.append("Free cash flow is negative")
    if revenue is not None and revenue < 1_000_000:
        weaknesses.append("Margins may be not meaningful due to small revenue base")
    return _bounded(score), strengths, weaknesses


def _score_balance(latest: dict) -> tuple[float, list[str], list[str]]:
    cash = to_float(latest.get("cash"))
    debt = to_float(latest.get("total_debt"))
    current_ratio = to_float(latest.get("current_ratio"))
    fcf = to_float(latest.get("free_cash_flow"))
    equity = to_float(latest.get("shareholders_equity"))
    score = 50
    strengths = []
    weaknesses = []
    runway_years = cash / abs(fcf) if cash is not None and fcf is not None and fcf < 0 else None
    if cash is not None and debt is not None:
        if cash >= debt:
            score += 12
            strengths.append("Cash is greater than total debt")
        else:
            score -= min(25, (debt - cash) / max(debt, 1) * 25)
            weaknesses.append("Debt exceeds cash")
    if runway_years is not None:
        if runway_years < 1:
            score -= 35
            weaknesses.append("Cash runway proxy is below 12 months")
        elif runway_years < 2:
            score -= 20
            weaknesses.append("Cash runway proxy is 12-24 months")
        else:
            score -= 5
            strengths.append("Cash runway proxy is above 24 months")
    if current_ratio is not None:
        score += 10 if current_ratio >= 1.5 else -10 if current_ratio < 1 else 0
    if debt is not None and equity is not None and equity > 0 and debt / equity > 2:
        score -= 15
        weaknesses.append("Debt/equity is elevated")
    return _bounded(score), strengths, weaknesses


def _score_valuation(quote: dict, latest: dict) -> tuple[float, list[str], list[str], str]:
    ps = to_float(quote.get("price_to_sales"))
    ev_sales = to_float(quote.get("enterprise_value"))
    revenue = to_float(latest.get("revenue"))
    ev_to_sales = ev_sales / revenue if ev_sales is not None and revenue not in (None, 0) else None
    pe = to_float(quote.get("trailing_pe"))
    growth = to_float(latest.get("revenue_yoy_growth") or latest.get("revenue_qoq_growth"))
    profitable = to_float(latest.get("net_income")) is not None and to_float(latest.get("net_income")) > 0
    if ps is None and pe is None and ev_to_sales is None:
        return 45, [], ["Valuation metrics unavailable"], "Not meaningful / insufficient data"
    if not profitable:
        sales_multiple = ps if ps is not None else ev_to_sales
        score = 62 - min((sales_multiple or 8) * 4, 42)
        label = "Cheap" if sales_multiple is not None and sales_multiple < 3 else "Reasonable" if sales_multiple is not None and sales_multiple < 8 else "Expensive" if sales_multiple is not None and sales_multiple < 15 else "Very expensive"
    else:
        score = 70 - min((pe or 30) * 0.8, 45)
        label = "Cheap" if pe is not None and pe < 15 else "Reasonable" if pe is not None and pe < 30 else "Expensive" if pe is not None and pe < 60 else "Very expensive"
    if growth is not None and growth > 30:
        score += 8
    strengths = [f"Valuation appears {label.lower()}"] if label in {"Cheap", "Reasonable"} else []
    weaknesses = [f"Valuation appears {label.lower()}"] if label in {"Expensive", "Very expensive"} else []
    return _bounded(score), strengths, weaknesses, label


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) <= period:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    values = (100 - (100 / (1 + rs))).dropna()
    return to_float(values.iloc[-1]) if not values.empty else None


def _score_momentum(ticker: str, quote: dict) -> tuple[float, list[str], list[str], dict]:
    history = fetch_history(ticker, "1y", "1d")
    close = pd.to_numeric(history.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    if close.empty:
        return 45, [], ["Price history unavailable"], {}
    last = to_float(close.iloc[-1])
    sma50 = to_float(close.tail(50).mean()) if len(close) >= 50 else None
    sma200 = to_float(close.tail(200).mean()) if len(close) >= 200 else None
    ret_1m = safe_div(last - close.iloc[-22], close.iloc[-22], 100) if len(close) > 22 else None
    rsi = _rsi(close)
    score = 50
    strengths = []
    weaknesses = []
    if sma50 is not None:
        score += 12 if last and last > sma50 else -12
    if sma200 is not None:
        score += 12 if last and last > sma200 else -12
    if ret_1m is not None:
        score += max(min(ret_1m, 20), -20) * 0.6
    if rsi is not None and rsi > 75:
        score -= 8
        weaknesses.append("RSI appears extended")
    if sma50 is not None and last and last > sma50:
        strengths.append("Price is above 50D average")
    return _bounded(score), strengths, weaknesses, {"sma50": sma50, "sma200": sma200, "rsi": rsi, "one_month_return": ret_1m}


def _score_catalysts(ticker: str) -> tuple[float, list[str], list[str]]:
    news, _ = fetch_news(ticker, 12)
    if news.empty:
        return 45, [], ["Recent catalyst data unavailable"]
    company_news = news[news.get("Scope", "Company").eq("Company")] if "Scope" in news else news
    if company_news.empty:
        return 48, [], ["No recent company-specific catalysts found"]
    negative_tags = company_news["Tag"].isin(["Financing/Dilution", "Regulation"]).sum()
    positive_tags = company_news["Tag"].isin(["Earnings", "Product", "M&A", "Analyst"]).sum()
    score = 50 + positive_tags * 4 - negative_tags * 6
    strengths = [f"{positive_tags} recent catalyst headline(s)"] if positive_tags else []
    weaknesses = [f"{negative_tags} risk-related headline(s)"] if negative_tags else []
    return _bounded(score), strengths, weaknesses


def _weighted_data_completeness(quote: dict, latest: dict, financials: dict, technicals: dict) -> tuple[float, list[str]]:
    required = {
        "growth_score": ["revenue", "revenue_yoy_growth"],
        "profitability_score": ["gross_margin", "operating_margin", "net_margin", "free_cash_flow"],
        "balance_sheet_score": ["cash", "total_debt", "free_cash_flow", "current_ratio"],
        "valuation_score": ["price_to_sales", "enterprise_value", "trailing_pe", "forward_pe"],
        "momentum_score": ["price", "sma50", "sma200"],
        "catalyst_score": ["news"],
    }
    sources = {**latest, **quote, **technicals}
    missing = list(financials.get("missing_fields", []))
    availability = {}
    for category, fields in required.items():
        present = 0
        for field in fields:
            if field == "news":
                present += 1
            elif to_float(sources.get(field)) is not None:
                present += 1
        availability[category] = present / len(fields)
    completeness = sum(availability[key] * WEIGHTS[key] for key in WEIGHTS)
    if availability["valuation_score"] < 0.35:
        missing.append("valuation metrics")
    if financials.get("status") in {"Partial", "Invalid", "Error"}:
        missing.append(f"financials status: {financials.get('status')}")
    return completeness, sorted(set(missing))


@st.cache_data(ttl=900, show_spinner=False)
def compute_signal(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    if not symbol:
        return {"ticker": "", "signal_label": "No Rating / Insufficient Data", "composite_score": 0, "confidence": "Low", "missing_data_warnings": ["Invalid ticker"]}
    financials = load_latest_company_financials(symbol)
    quote = financials.get("latest_quote") or fetch_quote(symbol)
    latest = financials.get("latest_financials", {})
    growth, s1, w1 = _score_growth(latest)
    profitability, s2, w2 = _score_profitability(latest)
    balance, s3, w3 = _score_balance(latest)
    valuation, s4, w4, valuation_label = _score_valuation(quote, latest)
    momentum, s5, w5, technicals = _score_momentum(symbol, quote)
    catalysts, s6, w6 = _score_catalysts(symbol)
    scores = {
        "growth_score": growth,
        "profitability_score": profitability,
        "balance_sheet_score": balance,
        "valuation_score": valuation,
        "momentum_score": momentum,
        "catalyst_score": catalysts,
    }
    completeness, missing = _weighted_data_completeness(quote, latest, financials, technicals)
    composite = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)
    if completeness < 0.40 or len(missing) >= 7:
        label = "No Rating / Insufficient Data"
    elif composite >= 80:
        label = "Buy"
    elif composite >= 65:
        label = "Speculative Buy" if balance < 55 or profitability < 45 else "Buy"
    elif composite >= 45:
        label = "Hold / Watchlist"
    elif composite >= 25:
        label = "Sell / Trim"
    else:
        label = "Avoid"
    if completeness >= 0.80 and "valuation metrics" not in missing and financials.get("status") == "Valid":
        confidence = "High"
    elif completeness >= 0.55:
        confidence = "Medium"
    else:
        confidence = "Low"
    strengths = (s1 + s2 + s3 + s4 + s5 + s6)[:6]
    weaknesses = (w1 + w2 + w3 + w4 + w5 + w6 + [f"Missing {field}" for field in missing])[:8]
    return {
        "ticker": symbol,
        "composite_score": round(composite, 1),
        "signal_label": label,
        "confidence": confidence,
        **scores,
        "valuation_label": valuation_label,
        "strengths": strengths or ["No major strengths identified from available data"],
        "weaknesses": weaknesses or ["No major weaknesses identified from available data"],
        "upgrade_triggers": ["Revenue growth improves", "Margins expand", "Balance sheet risk declines", "Valuation multiple compresses"],
        "downgrade_triggers": ["Revenue growth decelerates", "Cash burn accelerates", "Debt rises", "Price breaks below key moving averages"],
        "missing_data_warnings": missing,
        "data_completeness": round(completeness * 100, 1),
        "data_quality_note": "Confidence is based on weighted availability of financial, valuation, balance sheet, momentum, and catalyst inputs.",
        "technicals": technicals,
        "financials_status": financials.get("status"),
        "source": "Transparent V1 scoring engine",
    }


def signal_to_json(signal: dict) -> str:
    return json.dumps(signal, default=str)
