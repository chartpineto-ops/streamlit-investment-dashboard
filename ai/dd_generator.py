from __future__ import annotations

import json
from typing import Any

import requests

from data.filings import fetch_sec_filings
from data.financials import load_latest_company_financials
from data.market_data import fetch_quote
from data.news import fetch_news
from data.options import fetch_options_summary
from signals.signal_engine import compute_signal
from utils.formatting import clean_ticker, fmt_compact, fmt_currency, fmt_percent, fmt_price


def _records(frame, limit: int = 8) -> list[dict[str, Any]]:
    try:
        return frame.head(limit).to_dict("records")
    except Exception:
        return []


def build_research_packet(ticker: str) -> dict:
    symbol = clean_ticker(ticker)
    quote = fetch_quote(symbol)
    financials = load_latest_company_financials(symbol)
    latest = financials.get("latest_financials", {})
    latest_release = financials.get("latest_quarterly_release", {})
    signal = compute_signal(symbol)
    options = fetch_options_summary(symbol, quote.get("price"))
    news, news_status = fetch_news(symbol, 10)
    filings, filing_status = fetch_sec_filings(symbol)
    return {
        "ticker": symbol,
        "company_snapshot": {
            "company_name": quote.get("company_name"),
            "sector": quote.get("sector"),
            "industry": quote.get("industry"),
            "logo_status": quote.get("logo_status"),
            "business_summary": quote.get("business_summary"),
        },
        "price_snapshot": {
            "last_price": fmt_price(quote.get("price")),
            "daily_move_pct": fmt_percent(quote.get("daily_change_pct"), signed=True),
            "market_cap": fmt_currency(quote.get("market_cap"), 1),
            "volume": fmt_compact(quote.get("volume")),
        },
        "financials": {
            "period": latest.get("period"),
            "revenue": fmt_currency(latest.get("revenue"), 1),
            "gross_margin": fmt_percent(latest.get("gross_margin")),
            "operating_margin": fmt_percent(latest.get("operating_margin")),
            "net_margin": fmt_percent(latest.get("net_margin")),
            "free_cash_flow": fmt_currency(latest.get("free_cash_flow"), 1),
            "cash": fmt_currency(latest.get("cash"), 1),
            "total_debt": fmt_currency(latest.get("total_debt"), 1),
        },
        "latest_quarterly_release": {
            "period": latest_release.get("reported_period_label") or latest_release.get("period_label"),
            "reported_period_label": latest_release.get("reported_period_label"),
            "filing_period_label": latest_release.get("filing_period_label"),
            "structured_values_period_label": latest_release.get("structured_values_period_label"),
            "structured_values_source": latest_release.get("structured_values_source"),
            "period_alignment_status": latest_release.get("period_alignment_status"),
            "filing_date": str(latest_release.get("filing_date") or latest_release.get("filing_or_release_date")),
            "filing_type": latest_release.get("form_type"),
            "filing_url": latest_release.get("filing_url"),
            "accession_number": latest_release.get("accession_number"),
            "fiscal_year": latest_release.get("fiscal_year"),
            "fiscal_period": latest_release.get("fiscal_period"),
            "period_end_date": str(latest_release.get("period_end_date")),
            "structured_values_date": str(latest_release.get("structured_values_date")),
            "source_status": latest_release.get("source_status"),
            "missing_fields": latest_release.get("missing_fields", []),
            "data_quality_note": latest_release.get("data_quality_note"),
            "revenue": fmt_currency(latest_release.get("revenue"), 1),
            "eps": latest_release.get("eps"),
            "net_income": fmt_currency(latest_release.get("net_income"), 1),
            "free_cash_flow": fmt_currency(latest_release.get("free_cash_flow"), 1),
            "cash": fmt_currency(latest_release.get("cash"), 1),
            "total_debt": fmt_currency(latest_release.get("total_debt"), 1),
        },
        "valuation": {
            "price_to_sales": quote.get("price_to_sales"),
            "trailing_pe": quote.get("trailing_pe"),
            "forward_pe": quote.get("forward_pe"),
            "price_to_book": quote.get("price_to_book"),
            "valuation_label": signal.get("valuation_label"),
        },
        "options": options,
        "news_catalysts": _records(news, 10),
        "filings": _records(filings, 5),
        "technical_entry_setup": {
            "description": "Technical setup signal based on momentum, moving averages, RSI, and 52-week positioning. Not a standalone buy/sell rating.",
            "technical_inputs": signal.get("technicals", {}),
            "price_52w_low": quote.get("fifty_two_week_low"),
            "price_52w_high": quote.get("fifty_two_week_high"),
        },
        "overall_research_signal": signal,
        "data_quality": {
            "financials_status": financials.get("status"),
            "missing_fields": financials.get("missing_fields", []),
            "warnings": financials.get("validation_warnings", []),
            "news_status": news_status,
            "filing_status": filing_status,
        },
    }


def openai_key_from_secrets(st_secrets) -> str | None:
    try:
        return st_secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def generate_dd_memo(packet: dict, api_key: str, model: str = "gpt-4o-mini") -> tuple[str, str]:
    if not api_key:
        return "", "AI DD is disabled until OPENAI_API_KEY is added to Streamlit secrets."
    prompt = f"""
You are preparing a concise, non-personalized investment research memo.
Use only the structured packet below. Do not invent missing facts.
The Recommendation must be derived from the Signal Center output, not a separate opinion.
Include these sections:
1. Executive Summary
2. Business Overview
3. Financial Snapshot
4. Valuation View
5. Overall Research Signal Explanation
6. Bull Case
7. Bear Case
8. Key Risks
9. Catalysts to Watch
10. Recommendation
11. Missing Data / Data Quality Notes

Research packet:
{json.dumps(packet, default=str, indent=2)}
"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You write concise equity research notes from provided data only. This is not personalized financial advice."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=45,
        )
        if response.status_code >= 400:
            return "", f"OpenAI request failed: {response.status_code} {response.text[:240]}"
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return content, ""
    except Exception as exc:
        return "", f"OpenAI request failed: {exc}"
