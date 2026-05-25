from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from data.company_identity import get_company_identity
from data.filings import fetch_sec_filings
from data.financials import get_latest_quarterly_release, load_latest_company_financials
from data.market_data import fetch_quote
from data.news import fetch_news
from data.options import fetch_options_summary
from signals.signal_engine import compute_signal
from utils.formatting import clean_ticker, fmt_compact, fmt_currency, fmt_date, fmt_eps, fmt_multiple, fmt_percent, fmt_price, safe_div, to_float


SYSTEM_PROMPT = (
    "You are an equity research assistant inside PineTerminal. Generate a concise, structured due diligence memo using only "
    "the provided research packet. Do not invent missing data. Do not create an investment recommendation that conflicts "
    "with PineTerminal's calculated signal. Clearly call out missing, partial, estimated, stale, or low-confidence data. "
    "This is research support, not financial advice."
)

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def _records(frame, limit: int = 8) -> list[dict[str, Any]]:
    try:
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            return []
        return frame.head(limit).where(pd.notna(frame), None).to_dict("records")
    except Exception:
        return []


def _clean(value) -> Any:
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except Exception:
        pass
    return value


def _value(raw, formatted: str | None = None) -> dict:
    return {"raw": _clean(raw), "formatted": formatted or str(_clean(raw))}


def _field(packet: dict, name: str) -> dict:
    fields = packet.get("fields") or {}
    detail = fields.get(name) or {}
    if not isinstance(detail, dict):
        return {}
    return detail


def _field_value(packet: dict, name: str):
    return _field(packet, name).get("value")


def _field_meta(packet: dict, name: str) -> dict:
    detail = _field(packet, name)
    return {
        "status": detail.get("status", "N/A"),
        "provider": detail.get("provider", "N/A"),
        "source": detail.get("source", "N/A"),
        "period": detail.get("period") or detail.get("period_label") or "N/A",
        "period_end_date": str(detail.get("period_end_date") or "N/A"),
        "concept_used": detail.get("concept_used") or detail.get("fallback_used") or "N/A",
        "formula": detail.get("calculation_formula") or detail.get("formula") or "N/A",
        "note": detail.get("note") or "N/A",
    }


def _range_position(quote: dict) -> float | None:
    price = to_float(quote.get("price"))
    low = to_float(quote.get("fifty_two_week_low"))
    high = to_float(quote.get("fifty_two_week_high"))
    if price is None or low is None or high is None or high <= low:
        return None
    return max(0, min(((price - low) / (high - low)) * 100, 100))


def _entry_label(quote: dict, latest: dict, signal: dict) -> str:
    price = to_float(quote.get("price"))
    tech = signal.get("technicals") or {}
    score = 0
    inputs = 0
    range_pct = _range_position(quote)
    if range_pct is not None:
        inputs += 1
        score += 2 if range_pct < 65 else 1 if range_pct < 85 else -2 if range_pct > 90 else 0
    rsi = to_float(tech.get("rsi"))
    if rsi is not None:
        inputs += 1
        score += 2 if rsi < 30 else 1 if rsi <= 60 else -2 if rsi > 70 else 0
    for key in ("sma50", "sma200"):
        avg = to_float(tech.get(key))
        if price is not None and avg is not None:
            inputs += 1
            score += 1 if price > avg else -1
    growth = to_float(latest.get("revenue_yoy_growth") or latest.get("revenue_qoq_growth"))
    if growth is not None:
        inputs += 1
        score += 1 if growth > 0 else -1
    if inputs == 0:
        return "N/A"
    if score >= 4:
        return "STRONG ENTRY"
    if score >= 2:
        return "WATCHLIST ENTRY"
    if score >= -1:
        return "NEUTRAL"
    if score >= -3:
        return "EXTENDED"
    return "WEAK SETUP"


def _source_quality(financials: dict) -> dict:
    packet = financials.get("financial_data_packet") or {}
    release = financials.get("latest_quarterly_release") or {}
    reconciliation = financials.get("reconciliation") or {}
    quality = packet.get("coverage_summary") or release.get("financial_data_quality") or reconciliation.get("data_quality") or {}
    return {
        "completeness_score": quality.get("completeness_score") or packet.get("completeness_score") or release.get("data_completeness_score"),
        "direct_fields": quality.get("found_direct", []),
        "fallback_fields": quality.get("fallback_used", []) or quality.get("fallback", []),
        "calculated_fields": quality.get("calculated", []),
        "estimated_fields": quality.get("estimated", []),
        "missing_fields": quality.get("missing", []) or release.get("missing_fields", []),
        "source_status": packet.get("source_status") or release.get("source_status") or financials.get("status"),
        "source_limitations": packet.get("warnings") or reconciliation.get("warnings") or financials.get("validation_warnings", []),
        "note": packet.get("data_quality_note") or release.get("compact_source_status_note") or release.get("data_quality_note"),
    }


def build_research_packet(
    ticker: str,
    company_identity: dict | None = None,
    quote_data: dict | None = None,
    financial_packet: dict | None = None,
    signal_output: dict | None = None,
    technical_output: dict | None = None,
    valuation_output: dict | None = None,
    options_data: dict | None = None,
    filings_data=None,
    news_data=None,
    data_health: dict | None = None,
) -> dict:
    symbol = clean_ticker(ticker)
    quote = quote_data or fetch_quote(symbol)
    identity = company_identity or get_company_identity(symbol)
    financials = financial_packet or load_latest_company_financials(symbol)
    latest = financials.get("latest_financials", {}) if isinstance(financials, dict) else {}
    latest_release = (financials.get("latest_quarterly_release") or get_latest_quarterly_release(symbol)) if isinstance(financials, dict) else {}
    canonical_packet = financials.get("financial_data_packet", {}) if isinstance(financials, dict) else {}
    signal = signal_output or compute_signal(symbol)
    technicals = technical_output or signal.get("technicals", {})
    valuation = valuation_output or {"valuation_view": signal.get("valuation_label")}
    options = options_data or fetch_options_summary(symbol, quote.get("price"))
    if news_data is None:
        news_frame, news_status = fetch_news(symbol, 10)
    elif isinstance(news_data, tuple) and len(news_data) == 2:
        news_frame, news_status = news_data
    else:
        news_frame, news_status = news_data, []
    if filings_data is None:
        filings_frame, filing_status = fetch_sec_filings(symbol)
    elif isinstance(filings_data, tuple) and len(filings_data) == 2:
        filings_frame, filing_status = filings_data
    else:
        filings_frame, filing_status = filings_data, {}
    quality = data_health or _source_quality(financials if isinstance(financials, dict) else {})
    return {
        "packet_version": "PineTerminal AI DD V1",
        "ticker": symbol,
        "company_identity": {
            "ticker": symbol,
            "company_name": identity.get("company_name") or quote.get("company_name") or symbol,
            "sector": identity.get("sector") or quote.get("sector") or "N/A",
            "industry": identity.get("industry") or quote.get("industry") or "N/A",
            "market_cap": _value(quote.get("market_cap"), fmt_currency(quote.get("market_cap"), 1)),
            "company_description": quote.get("business_summary") or "N/A",
        },
        "price_snapshot": {
            "current_price": _value(quote.get("price"), fmt_price(quote.get("price"))),
            "daily_move_pct": _value(quote.get("daily_change_pct"), fmt_percent(quote.get("daily_change_pct"), decimals=2, signed=True)),
            "daily_dollar_move": _value(quote.get("daily_change"), fmt_price(quote.get("daily_change")) if to_float(quote.get("daily_change")) is not None else "N/A"),
            "fifty_two_week_low": _value(quote.get("fifty_two_week_low"), fmt_price(quote.get("fifty_two_week_low"))),
            "fifty_two_week_high": _value(quote.get("fifty_two_week_high"), fmt_price(quote.get("fifty_two_week_high"))),
            "fifty_two_week_position": _value(_range_position(quote), fmt_percent(_range_position(quote))),
            "volume": _value(quote.get("volume"), fmt_compact(quote.get("volume"))),
            "average_volume": _value(quote.get("average_volume"), fmt_compact(quote.get("average_volume"))),
            "source": quote.get("source", "Yahoo Finance/yfinance"),
            "status": quote.get("status", "N/A"),
            "last_updated": fmt_date(quote.get("last_updated")),
        },
        "pineterminal_signal": {
            "overall_research_signal": signal.get("signal_label", "No Rating / Insufficient Data"),
            "market_stance": "Bullish" if signal.get("signal_label") in {"Buy", "Speculative Buy"} else "Bearish" if signal.get("signal_label") in {"Sell / Trim", "Avoid"} else "Neutral",
            "composite_score": signal.get("composite_score"),
            "confidence": signal.get("confidence"),
            "data_completeness": signal.get("data_completeness"),
            "factor_scores": {
                "growth": signal.get("growth_score"),
                "profitability_margins": signal.get("profitability_score"),
                "balance_sheet_liquidity": signal.get("balance_sheet_score"),
                "valuation": signal.get("valuation_score"),
                "momentum_technicals": signal.get("momentum_score"),
                "catalysts_news": signal.get("catalyst_score"),
            },
            "strengths": signal.get("strengths", []),
            "weaknesses": signal.get("weaknesses", []),
            "upgrade_triggers": signal.get("upgrade_triggers", []),
            "downgrade_triggers": signal.get("downgrade_triggers", []),
            "missing_data_warnings": signal.get("missing_data_warnings", []),
            "source": signal.get("source", "Transparent V1 scoring engine"),
        },
        "technical_entry_setup": {
            "entry_setup_label": _entry_label(quote, latest, signal),
            "rsi": technicals.get("rsi"),
            "price_vs_50d_ma": safe_div(to_float(quote.get("price")) - to_float(technicals.get("sma50")) if to_float(quote.get("price")) is not None and to_float(technicals.get("sma50")) is not None else None, technicals.get("sma50"), 100),
            "price_vs_200d_ma": safe_div(to_float(quote.get("price")) - to_float(technicals.get("sma200")) if to_float(quote.get("price")) is not None and to_float(technicals.get("sma200")) is not None else None, technicals.get("sma200"), 100),
            "fifty_two_week_position": _value(_range_position(quote), fmt_percent(_range_position(quote))),
            "technical_inputs": technicals,
            "technical_rationale": "Technical setup uses momentum, moving averages, RSI, and 52-week positioning. It is separate from the overall research signal.",
        },
        "latest_quarterly_release": {
            "reported_period": latest_release.get("reported_period_label") or latest_release.get("period_label") or "N/A",
            "period_end_date": str(latest_release.get("period_end_date") or "N/A"),
            "filing_release_date": str(latest_release.get("filing_date") or latest_release.get("filing_or_release_date") or "N/A"),
            "form_type": latest_release.get("form_type") or "N/A",
            "filing_url": latest_release.get("filing_url") or "N/A",
            "revenue": _value(latest_release.get("revenue"), fmt_currency(latest_release.get("revenue"), 1)),
            "revenue_growth": _value(latest_release.get("revenue_yoy_growth"), fmt_percent(latest_release.get("revenue_yoy_growth"), signed=True)),
            "gross_profit": _value(_field_value(canonical_packet, "gross_profit"), fmt_currency(_field_value(canonical_packet, "gross_profit"), 1)),
            "operating_income": _value(_field_value(canonical_packet, "operating_income") or latest_release.get("operating_income"), fmt_currency(_field_value(canonical_packet, "operating_income") or latest_release.get("operating_income"), 1)),
            "net_income": _value(latest_release.get("net_income"), fmt_currency(latest_release.get("net_income"), 1)),
            "eps": _value(latest_release.get("eps"), fmt_eps(latest_release.get("eps"))),
            "cash": _value(latest_release.get("cash"), fmt_currency(latest_release.get("cash"), 1)),
            "debt": _value(latest_release.get("total_debt"), fmt_currency(latest_release.get("total_debt"), 1)),
            "operating_cash_flow": _value(latest_release.get("operating_cash_flow"), fmt_currency(latest_release.get("operating_cash_flow"), 1)),
            "capex": _value(latest_release.get("capex"), fmt_currency(latest_release.get("capex"), 1)),
            "free_cash_flow": _value(latest_release.get("free_cash_flow"), fmt_currency(latest_release.get("free_cash_flow"), 1)),
            "source_status": latest_release.get("source_status") or "N/A",
            "data_quality_note": latest_release.get("compact_source_status_note") or latest_release.get("data_quality_note") or "N/A",
        },
        "financial_summary": {
            "period": latest.get("period") or "N/A",
            "revenue": _value(latest.get("revenue"), fmt_currency(latest.get("revenue"), 1)),
            "revenue_growth": _value(latest.get("revenue_yoy_growth"), fmt_percent(latest.get("revenue_yoy_growth"), signed=True)),
            "gross_margin": _value(latest.get("gross_margin"), fmt_percent(latest.get("gross_margin"))),
            "operating_margin": _value(latest.get("operating_margin"), fmt_percent(latest.get("operating_margin"))),
            "net_margin": _value(latest.get("net_margin"), fmt_percent(latest.get("net_margin"))),
            "fcf_margin": _value(latest.get("fcf_margin"), fmt_percent(latest.get("fcf_margin"))),
            "cash": _value(latest.get("cash"), fmt_currency(latest.get("cash"), 1)),
            "debt": _value(latest.get("total_debt"), fmt_currency(latest.get("total_debt"), 1)),
            "net_cash_debt": _value(_field_value(canonical_packet, "net_cash_or_debt"), fmt_currency(_field_value(canonical_packet, "net_cash_or_debt"), 1)),
            "cash_runway": _value(_field_value(canonical_packet, "cash_runway"), f"{_field_value(canonical_packet, 'cash_runway'):.1f} quarters" if to_float(_field_value(canonical_packet, "cash_runway")) is not None else "N/A"),
            "balance_sheet_risk": latest.get("balance_sheet_risk") or "N/A",
        },
        "valuation": {
            "market_cap": _value(quote.get("market_cap"), fmt_currency(quote.get("market_cap"), 1)),
            "enterprise_value": _value(quote.get("enterprise_value"), fmt_currency(quote.get("enterprise_value"), 1)),
            "price_sales": _value(quote.get("price_to_sales"), fmt_multiple(quote.get("price_to_sales"))),
            "ev_sales": _value(safe_div(quote.get("enterprise_value"), latest.get("revenue")), fmt_multiple(safe_div(quote.get("enterprise_value"), latest.get("revenue")))),
            "pe": _value(quote.get("trailing_pe"), fmt_multiple(quote.get("trailing_pe"))),
            "forward_pe": _value(quote.get("forward_pe"), fmt_multiple(quote.get("forward_pe"))),
            "price_book": _value(quote.get("price_to_book"), fmt_multiple(quote.get("price_to_book"))),
            "ev_ebitda": _value(quote.get("ev_to_ebitda"), fmt_multiple(quote.get("ev_to_ebitda"))),
            "valuation_view": valuation.get("valuation_view") or valuation.get("valuation_label") or signal.get("valuation_label") or "Not meaningful / insufficient data",
        },
        "options_volatility": {
            "seven_day_implied_move": _value((options.get("seven_day") or {}).get("implied_move_pct"), fmt_percent((options.get("seven_day") or {}).get("implied_move_pct"))),
            "seven_day_iv": _value((options.get("seven_day") or {}).get("annual_iv"), fmt_percent((options.get("seven_day") or {}).get("annual_iv"))),
            "thirty_day_implied_move": _value((options.get("thirty_day") or {}).get("implied_move_pct"), fmt_percent((options.get("thirty_day") or {}).get("implied_move_pct"))),
            "thirty_day_iv": _value((options.get("thirty_day") or {}).get("annual_iv"), fmt_percent((options.get("thirty_day") or {}).get("annual_iv"))),
            "options_status": options.get("status", "N/A"),
        },
        "sec_filings": {
            "latest_filings": _records(filings_frame, 6),
            "source_status": filing_status,
        },
        "news_catalysts": {
            "headlines": _records(news_frame, 10),
            "source_status": news_status,
        },
        "data_quality": {
            **quality,
            "field_metadata": {
                key: _field_meta(canonical_packet, key)
                for key in (
                    "revenue",
                    "gross_profit",
                    "operating_income",
                    "net_income",
                    "eps",
                    "cash",
                    "total_debt",
                    "operating_cash_flow",
                    "capex",
                    "free_cash_flow",
                    "shares_outstanding",
                )
            },
        },
    }


def openai_key_from_secrets(st_secrets) -> str | None:
    try:
        return st_secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def _config_value(key: str, default=None, secrets=None):
    env_value = os.environ.get(key)
    if env_value not in (None, ""):
        return env_value
    if secrets is not None:
        try:
            value = secrets.get(key)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    secret_paths = [Path.home() / ".streamlit" / "secrets.toml", Path.cwd() / ".streamlit" / "secrets.toml"]
    if any(path.exists() for path in secret_paths):
        try:
            import streamlit as st

            value = st.secrets.get(key)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    return default


def _normalize_provider(provider: str | None) -> str:
    text = str(provider or "").strip().lower()
    if text in {"", "auto"}:
        return "auto"
    if "ollama" in text or "llama" in text:
        return "ollama"
    if "openai" in text:
        return "openai"
    if "disabled" in text or text == "none":
        return "disabled"
    return text


def _ollama_health(base_url: str, model: str | None = None) -> dict:
    clean_base = (base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    try:
        response = requests.get(f"{clean_base}/api/tags", timeout=2)
        if response.status_code >= 400:
            return {
                "status": "Unavailable",
                "message": f"Ollama returned status {response.status_code} from /api/tags.",
                "models": [],
            }
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if item.get("name")]
        if model and models and model not in models:
            return {
                "status": "OK",
                "message": f"Ollama is reachable, but {model} was not listed by /api/tags. Generation may fail until the model is pulled.",
                "models": models,
            }
        return {"status": "OK", "message": "Ollama is reachable.", "models": models}
    except Exception as exc:
        return {
            "status": "Unavailable",
            "message": "Local Llama is unavailable. Make sure Ollama is installed, running, and the selected model is pulled.",
            "models": [],
            "error": str(exc)[:240],
        }


def detect_ai_provider(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    secrets=None,
) -> dict:
    """Detect the active AI memo provider without exposing secrets."""
    configured_provider = provider or _config_value("AI_PROVIDER", "auto", secrets)
    selected_provider = _normalize_provider(configured_provider)
    ollama_base_url = base_url or _config_value("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL, secrets)
    ollama_model = model or _config_value("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL, secrets)
    openai_key = api_key or _config_value("OPENAI_API_KEY", None, secrets)
    openai_model = _config_value("OPENAI_MODEL", DEFAULT_OPENAI_MODEL, secrets)

    if selected_provider == "disabled":
        return {
            "provider": "disabled",
            "provider_label": "Disabled",
            "model": "N/A",
            "status": "Disabled",
            "message": "AI memo generation is disabled. The research packet preview is still available.",
            "base_url": "",
            "openai_available": bool(openai_key),
            "ollama_available": False,
        }

    if selected_provider == "openai":
        if not openai_key:
            return {
                "provider": "openai",
                "provider_label": "OpenAI",
                "model": openai_model,
                "status": "Disabled",
                "message": "OPENAI_API_KEY is not configured. OpenAI generation is unavailable.",
                "base_url": "",
                "openai_available": False,
                "ollama_available": False,
            }
        return {
            "provider": "openai",
            "provider_label": "OpenAI",
            "model": openai_model,
            "status": "OK",
            "message": "OpenAI is configured.",
            "base_url": "",
            "openai_available": True,
            "ollama_available": False,
        }

    if selected_provider == "ollama":
        health = _ollama_health(ollama_base_url, ollama_model)
        return {
            "provider": "ollama",
            "provider_label": "Ollama / Local Llama",
            "model": ollama_model,
            "status": health.get("status"),
            "message": health.get("message"),
            "base_url": ollama_base_url,
            "openai_available": bool(openai_key),
            "ollama_available": health.get("status") == "OK",
            "available_models": health.get("models", []),
        }

    health = _ollama_health(ollama_base_url, ollama_model)
    if health.get("status") == "OK":
        return {
            "provider": "ollama",
            "provider_label": "Ollama / Local Llama",
            "model": ollama_model,
            "status": "OK",
            "message": health.get("message"),
            "base_url": ollama_base_url,
            "openai_available": bool(openai_key),
            "ollama_available": True,
            "available_models": health.get("models", []),
        }
    if openai_key:
        return {
            "provider": "openai",
            "provider_label": "OpenAI",
            "model": openai_model,
            "status": "OK",
            "message": "Ollama was unavailable, so PineTerminal will use optional OpenAI.",
            "base_url": "",
            "openai_available": True,
            "ollama_available": False,
            "ollama_message": health.get("message"),
        }
    return {
        "provider": "disabled",
        "provider_label": "Disabled",
        "model": "N/A",
        "status": "Disabled",
        "message": "No AI provider is available. Ollama is unavailable and OPENAI_API_KEY is not configured.",
        "base_url": ollama_base_url,
        "openai_available": False,
        "ollama_available": False,
        "ollama_message": health.get("message"),
    }


def _memo_instructions(memo_length: str, tone: str, include_risks: bool, include_data_quality_notes: bool) -> str:
    length_map = {
        "Short": "Keep the memo brief, roughly 500-800 words.",
        "Standard": "Use a balanced memo length, roughly 900-1,300 words.",
        "Detailed": "Use a more detailed memo, roughly 1,500-2,200 words.",
    }
    tone_map = {
        "Analyst style": "Use a professional equity research analyst tone.",
        "Executive brief": "Use a concise executive briefing tone with clear takeaways.",
        "Blog draft": "Use a clear investor-education tone while remaining grounded and non-promotional.",
    }
    risk_instruction = "Include key risks and watch items." if include_risks else "Keep risk discussion brief and state that detailed risks were omitted by user option."
    quality_instruction = "Include a Data Quality / Missing Data Notes section." if include_data_quality_notes else "Do not include a standalone data quality section, but do not hide material missing data."
    return " ".join([length_map.get(memo_length, length_map["Standard"]), tone_map.get(tone, tone_map["Analyst style"]), risk_instruction, quality_instruction])


def _memo_prompt(research_packet: dict, memo_length: str, tone: str, include_risks: bool, include_data_quality_notes: bool) -> str:
    signal = (research_packet.get("pineterminal_signal") or {}).get("overall_research_signal") or "No Rating / Insufficient Data"
    return f"""
Generate a grounded PineTerminal due diligence memo from the JSON research packet below.

Required memo sections:
1. Executive Summary
2. Company Overview
3. Price Action and Technical Setup
4. Financial Snapshot
5. Valuation View
6. Balance Sheet and Cash Flow Risk
7. Signal Center Explanation
8. Bull Case
9. Bear Case
10. Key Catalysts
11. Key Risks
12. Watch Items
13. PineTerminal Recommendation
14. Data Quality / Missing Data Notes

PineTerminal calculated signal: {signal}
Recommendation rule: The PineTerminal Recommendation section must use this calculated signal and must not create a separate AI rating.
Style options: {_memo_instructions(memo_length, tone, include_risks, include_data_quality_notes)}

Research packet:
{json.dumps(research_packet, default=str, indent=2)}
"""


def generate_due_diligence_memo_openai(
    research_packet: dict,
    api_key: str,
    model: str = DEFAULT_OPENAI_MODEL,
    memo_length: str = "Standard",
    tone: str = "Analyst style",
    include_risks: bool = True,
    include_data_quality_notes: bool = True,
) -> str:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing.")
    prompt = _memo_prompt(research_packet, memo_length, tone, include_risks, include_data_quality_notes)
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI request failed with status {response.status_code}: {response.text[:240]}")
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def generate_due_diligence_memo_ollama(
    research_packet: dict,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    memo_length: str = "Standard",
    tone: str = "Analyst style",
    include_risks: bool = True,
    include_data_quality_notes: bool = True,
) -> str:
    clean_base = (base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    prompt = _memo_prompt(research_packet, memo_length, tone, include_risks, include_data_quality_notes)
    try:
        response = requests.post(
            f"{clean_base}/api/chat",
            json={
                "model": model or DEFAULT_OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=180,
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama request failed: {str(exc)[:240]}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"Ollama request failed with status {response.status_code}: {response.text[:240]}")
    payload = response.json()
    content = ((payload.get("message") or {}).get("content") or payload.get("response") or "").strip()
    if not content:
        raise RuntimeError("Ollama returned an empty memo response.")
    return content


def generate_due_diligence_memo(
    research_packet: dict,
    api_key: str | None = None,
    model: str | None = None,
    memo_length: str = "Standard",
    tone: str = "Analyst style",
    include_risks: bool = True,
    include_data_quality_notes: bool = True,
    provider_info: dict | None = None,
    base_url: str | None = None,
) -> str:
    provider = provider_info or detect_ai_provider(model=model, base_url=base_url, api_key=api_key)
    if provider.get("status") != "OK":
        raise RuntimeError(provider.get("message") or "AI provider is unavailable.")
    if provider.get("provider") == "ollama":
        return generate_due_diligence_memo_ollama(
            research_packet,
            model=provider.get("model") or model or DEFAULT_OLLAMA_MODEL,
            base_url=provider.get("base_url") or base_url or DEFAULT_OLLAMA_BASE_URL,
            memo_length=memo_length,
            tone=tone,
            include_risks=include_risks,
            include_data_quality_notes=include_data_quality_notes,
        )
    if provider.get("provider") == "openai":
        key = api_key or _config_value("OPENAI_API_KEY")
        return generate_due_diligence_memo_openai(
            research_packet,
            key,
            model=provider.get("model") or model or DEFAULT_OPENAI_MODEL,
            memo_length=memo_length,
            tone=tone,
            include_risks=include_risks,
            include_data_quality_notes=include_data_quality_notes,
        )
    raise RuntimeError(provider.get("message") or "AI memo generation is disabled.")


def generate_dd_memo(packet: dict, api_key: str, model: str = "gpt-4o-mini") -> tuple[str, str]:
    try:
        return generate_due_diligence_memo(packet, api_key, model=model), ""
    except Exception as exc:
        return "", str(exc)
