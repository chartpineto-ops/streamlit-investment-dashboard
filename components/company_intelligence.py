from __future__ import annotations

from html import escape

import pandas as pd

from data.financials import load_latest_company_financials
from pineterminal.components import money, percent, price, tone_for_signal, tone_for_value
from services.competitive_intelligence_service import fetch_competitive_intelligence
from utils.formatting import fmt_date, to_float
from utils.rendering import render_html


def _clean_values(frame: pd.DataFrame, key: str) -> list[tuple[str, float]]:
    if frame is None or frame.empty or key not in frame:
        return []
    rows: list[tuple[str, float]] = []
    for _, row in frame.tail(8).iterrows():
        value = to_float(row.get(key))
        if value is not None:
            rows.append((str(row.get("period") or "Period"), value))
    return rows


def _comparison(points: list[tuple[str, float]], quarterly: bool) -> tuple[float | None, str]:
    if len(points) < 2:
        return None, "History unavailable"
    comparison_index = -5 if quarterly and len(points) >= 5 else 0
    prior_label, prior = points[comparison_index]
    latest = points[-1][1]
    return latest - prior, f"vs {prior_label}"


def _trend(change: float | None, threshold: float, inverse: bool = False) -> tuple[str, str]:
    if change is None:
        return "Insufficient history", "neutral"
    adjusted = -change if inverse else change
    if adjusted > threshold:
        return "Improving", "good"
    if adjusted < -threshold:
        return "Deteriorating", "bad"
    return "Stable", "warn"


def _sparkline(points: list[tuple[str, float]], tone: str) -> str:
    values = [value for _, value in points[-6:]]
    if len(values) < 2:
        return '<div class="pt-trend-empty">No comparable history</div>'
    low, high = min(values), max(values)
    spread = high - low
    coords = []
    for index, value in enumerate(values):
        x = 4 + index * (92 / max(1, len(values) - 1))
        y = 30 if spread == 0 else 52 - ((value - low) / spread * 42)
        coords.append(f"{x:.1f},{y:.1f}")
    return f'<svg class="pt-trend-spark {tone}" viewBox="0 0 100 58" preserveAspectRatio="none" aria-hidden="true"><polyline points="{" ".join(coords)}"></polyline></svg>'


def _metric_card(label: str, current: str, comparison: str, status: str, tone: str, points: list[tuple[str, float]], interpretation: str) -> str:
    return f"""
    <div class="pt-lt-metric">
      <div class="pt-lt-metric-head"><span>{escape(label)}</span><b class="{tone}">{escape(status)}</b></div>
      <strong>{escape(current)}</strong>
      <small>{escape(comparison)}</small>
      {_sparkline(points, tone)}
      <p>{escape(interpretation)}</p>
    </div>
    """


def _format_margin(value: float | None) -> str:
    return percent(value, 1, signed=False) if value is not None else "N/A"


def _format_change(change: float | None, suffix: str, comparison_label: str) -> str:
    if change is None:
        return comparison_label
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}{suffix} {comparison_label}"


def _long_term_metrics(analysis, financials: dict) -> tuple[list[str], dict[str, int], str]:
    history = financials.get("quarterly_history")
    quarterly = isinstance(history, pd.DataFrame) and not history.empty
    if not quarterly:
        history = financials.get("annual_history")
    if not isinstance(history, pd.DataFrame):
        history = pd.DataFrame()
    cards: list[str] = []
    counts = {"good": 0, "warn": 0, "bad": 0, "neutral": 0}

    revenue = _clean_values(history, "revenue")
    revenue_change, revenue_compare = _comparison(revenue, quarterly)
    revenue_growth = (revenue_change / revenue[-5 if quarterly and len(revenue) >= 5 else 0][1] * 100) if revenue_change is not None and revenue[-5 if quarterly and len(revenue) >= 5 else 0][1] else None
    status, tone = _trend(revenue_growth, 5)
    counts[tone] += 1
    cards.append(_metric_card("Revenue", money(revenue[-1][1]) if revenue else "N/A", _format_change(revenue_growth, "%", revenue_compare), status, tone, revenue, "Sustained top-line growth expands the earnings base; small-base spikes need confirmation."))

    for label, key, threshold, interpretation in (
        ("Gross Margin", "gross_margin", 1.0, "Gross-margin expansion signals pricing power and improving unit economics."),
        ("Operating Margin", "operating_margin", 1.0, "Operating leverage matters more than revenue growth that never reaches the bottom line."),
        ("Free Cash Flow Margin", "fcf_margin", 1.0, "Positive and rising free cash flow reduces financing and dilution dependence."),
    ):
        points = _clean_values(history, key)
        change, compare = _comparison(points, quarterly)
        status, tone = _trend(change, threshold)
        counts[tone] += 1
        cards.append(_metric_card(label, _format_margin(points[-1][1]) if points else "N/A", _format_change(change, " pts", compare), status, tone, points, interpretation))

    net_cash_points = []
    cash = _clean_values(history, "cash")
    debt = _clean_values(history, "total_debt")
    debt_by_period = dict(debt)
    for period, cash_value in cash:
        if period in debt_by_period:
            net_cash_points.append((period, cash_value - debt_by_period[period]))
    net_cash_change, net_cash_compare = _comparison(net_cash_points, quarterly)
    status, tone = _trend(net_cash_change, max(abs(net_cash_points[-1][1]) * 0.05, 1.0) if net_cash_points else 1.0)
    counts[tone] += 1
    cards.append(_metric_card("Net Cash / Debt", money(net_cash_points[-1][1]) if net_cash_points else "N/A", (f"{money(net_cash_change)} {net_cash_compare}" if net_cash_change is not None else net_cash_compare), status, tone, net_cash_points, "Balance-sheet direction determines resilience and the need for outside capital."))

    shares = _clean_values(history, "shares_outstanding")
    current_shares = to_float(analysis.company.shares_outstanding)
    if current_shares is not None and (not shares or shares[-1][1] != current_shares):
        shares.append(("Current", current_shares))
    shares_change, shares_compare = _comparison(shares, quarterly=False)
    shares_growth = (shares_change / shares[0][1] * 100) if shares_change is not None and shares[0][1] else None
    status, tone = _trend(shares_growth, 3.0, inverse=True)
    counts[tone] += 1
    cards.append(_metric_card("Share Count", f"{current_shares / 1_000_000:.1f}M" if current_shares is not None else "N/A", _format_change(shares_growth, "%", shares_compare), status, tone, shares, "Per-share value can lag company growth when issuance persistently expands the share count."))

    period_label = str(history.iloc[-1].get("period") or "Latest filing") if not history.empty else "No reliable filing history"
    return cards, counts, period_label


def render_long_term_company_stats(analysis) -> None:
    financials = load_latest_company_financials(analysis.company.ticker)
    cards, counts, period_label = _long_term_metrics(analysis, financials)
    improving = counts["good"]
    deteriorating = counts["bad"]
    if improving > deteriorating:
        trend, trend_tone = "Progressing", "good"
    elif deteriorating > improving:
        trend, trend_tone = "Declining", "bad"
    else:
        trend, trend_tone = "Mixed", "warn"
    recommendation = analysis.investment_signal.signal
    recommendation_tone = tone_for_signal(recommendation)
    support = "supports" if trend_tone == "good" else "challenges" if trend_tone == "bad" else "does not yet fully confirm"
    source = (financials.get("source_metadata") or {}).get("financials") or "SEC XBRL / Yahoo Finance financial statements"
    render_html(
        f"""
        <div class="pt-shell pt-company-research-shell">
          <div class="pt-research-head">
            <div><span>LONG-TERM OPERATING TREND</span><h2>Progression That Matters</h2><p>Reported growth, margins, cash generation, balance-sheet direction, and per-share discipline.</p></div>
            <div class="pt-research-verdict"><span>Operating Evidence</span><b class="{trend_tone}">{trend}</b><small>{improving} improving / {deteriorating} deteriorating</small></div>
          </div>
          <div class="pt-lt-grid">{"".join(cards)}</div>
          <div class="pt-recommendation-read"><span>Read on Recommendation</span><strong class="{recommendation_tone}">{escape(recommendation)}</strong><p>The reported operating trend {support} the current recommendation. Valuation, catalysts, and risk controls remain separate inputs; social attention is not used as a standalone recommendation signal.</p></div>
          <div class="pt-source-foot">Through {escape(period_label)} | {escape(str(source))}</div>
        </div>
        """
    )


def _fmt_peer_percent(value: object, fractional: bool = False) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if fractional:
        number *= 100
    return percent(number, 1)


def _peer_tone(label: str) -> str:
    return "good" if label == "Leading" else "warn" if label == "Competitive" else "bad" if label == "Lagging" else "neutral"


def _peer_narrative(symbol: str, frame: pd.DataFrame) -> str:
    selected = frame.loc[frame["ticker"] == symbol]
    peers = frame.loc[frame["ticker"] != symbol]
    if selected.empty or peers.empty:
        return "Peer-relative evidence is incomplete. PineTerminal will show unavailable fields rather than infer missing performance."
    row = selected.iloc[0]
    parts = []
    for key, label, fractional in (("return_3m", "three-month price performance", False), ("revenue_growth", "revenue growth", True), ("gross_margin", "gross margin", True)):
        if key not in peers:
            continue
        value = to_float(row.get(key))
        median = pd.to_numeric(peers[key], errors="coerce").median()
        if value is None or pd.isna(median):
            continue
        display_value = value * 100 if fractional else value
        display_median = float(median) * 100 if fractional else float(median)
        relation = "above" if display_value > display_median else "below"
        parts.append(f"{label} is {relation} the peer median ({display_value:.1f}% vs {display_median:.1f}%)")
    return ("; ".join(parts) + ".") if parts else "Comparable peer metrics are not yet sufficiently complete for a reliable relative read."


def render_competitive_intelligence(analysis) -> None:
    company = analysis.company
    frame, status = fetch_competitive_intelligence(company.ticker, company.sector, company.industry, tuple(company.themes))
    if frame.empty:
        render_html('<div class="pt-shell pt-company-research-shell"><div class="pt-research-head"><div><span>COMPETITIVE INTELLIGENCE</span><h2>Peer Performance</h2></div></div><p class="pt-placeholder">No reliable peer data available.</p></div>')
        return
    rows = []
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker") or "")
        is_selected = ticker == company.ticker
        relative = str(row.get("relative_read") or "Insufficient data")
        valuation = to_float(row.get("forward_pe"))
        sales_multiple = to_float(row.get("price_to_sales"))
        operating_margin = to_float(row.get("operating_margin"))
        valuation_label = (
            f"{valuation:.1f}x P/E"
            if valuation is not None and valuation > 0 and operating_margin is not None and operating_margin > 0
            else f"{sales_multiple:.1f}x P/S"
            if sales_multiple is not None
            else "N/A"
        )
        rows.append(
            f"""
            <tr class="{'selected' if is_selected else ''}">
              <td><strong>{escape(ticker)}</strong><small>{escape(str(row.get('company') or ticker))}</small></td>
              <td class="{tone_for_value(to_float(row.get('return_1m')))}">{_fmt_peer_percent(row.get('return_1m'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_3m')))}">{_fmt_peer_percent(row.get('return_3m'))}</td>
              <td class="{tone_for_value(to_float(row.get('return_1y')))}">{_fmt_peer_percent(row.get('return_1y'))}</td>
              <td>{_fmt_peer_percent(row.get('revenue_growth'), True)}</td>
              <td>{_fmt_peer_percent(row.get('gross_margin'), True)}</td>
              <td>{_fmt_peer_percent(row.get('operating_margin'), True)}</td>
              <td>{escape(valuation_label)}</td>
              <td><span class="pt-peer-badge {_peer_tone(relative)}">{escape(relative)}</span></td>
            </tr>
            """
        )
    render_html(
        f"""
        <div class="pt-shell pt-company-research-shell pt-peer-shell">
          <div class="pt-research-head"><div><span>COMPETITIVE INTELLIGENCE</span><h2>Peer Performance</h2><p>Operating quality, valuation, and price confirmation against the closest available industry/theme cohort.</p></div><div class="pt-research-verdict"><span>Coverage</span><b>{status.get('symbols_loaded', 0)}/{status.get('symbols_requested', len(frame))}</b><small>{escape(str(status.get('status') or 'Unknown'))}</small></div></div>
          <div class="pt-peer-table-wrap"><table class="pt-peer-table"><thead><tr><th>Company</th><th>1M</th><th>3M</th><th>1Y</th><th>Rev Growth</th><th>Gross Mgn TTM</th><th>Op Mgn TTM</th><th>Valuation</th><th>Relative Read</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
          <div class="pt-peer-read"><span>Analyst Comparison</span><p>{escape(_peer_narrative(company.ticker, frame))}</p></div>
          <div class="pt-source-foot">{escape(str(status.get('source') or 'Yahoo Finance/yfinance'))} | refreshed {escape(fmt_date(status.get('last_updated')))}</div>
        </div>
        """
    )
