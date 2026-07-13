from __future__ import annotations

from html import escape
from typing import Any, Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.economic_data_service import (
    audit_macro_dashboard,
    macro_poll_interval_seconds,
    next_scheduled_macro_release,
)
from services.macro_alert_service import list_macro_alerts, macro_notification_status, process_macro_updates
from storage.watchlist import add_ticker, list_alerts, list_watchlist, remove_ticker
from terminal_v2.data_hub import (
    benchmark_quotes,
    macro_dashboard,
    market_news,
    market_quotes,
    market_session,
    movers_packet,
    sector_quotes,
    security_packet,
    social_market,
    social_themes,
)
from terminal_v2.integrity import classify_frame, freshness_label, provider_health, status_tone
from utils.formatting import clean_ticker, now_et, to_float


SECTOR_NAMES = {
    "XLK": "Technology",
    "XLC": "Communication",
    "XLY": "Cons. Discretionary",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLP": "Cons. Staples",
    "XLU": "Utilities",
}


def _html(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _number(value: object) -> float | None:
    return to_float(value)


def _money(value: object, decimals: int = 1) -> str:
    number = _number(value)
    if number is None:
        return "N/A"
    absolute = abs(number)
    if absolute >= 1_000_000_000_000:
        return f"${number / 1_000_000_000_000:.{decimals}f}T"
    if absolute >= 1_000_000_000:
        return f"${number / 1_000_000_000:.{decimals}f}B"
    if absolute >= 1_000_000:
        return f"${number / 1_000_000:.{decimals}f}M"
    return f"${number:,.2f}"


def _count(value: object) -> str:
    number = _number(value)
    if number is None:
        return "N/A"
    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:,.0f}"


def _pct(value: object, decimals: int = 1, fractional: bool = False) -> str:
    number = _number(value)
    if number is None:
        return "N/A"
    if fractional:
        number *= 100
    return f"{number:+.{decimals}f}%"


def _return_pct(value: object, decimals: int = 1) -> str:
    number = _number(value)
    if number is None:
        return "N/A"
    if abs(number) <= 3:
        number *= 100
    return f"{number:+.{decimals}f}%"


def _multiple(value: object) -> str:
    number = _number(value)
    return f"{number:.1f}x" if number is not None else "N/A"


def _tone(value: object) -> str:
    number = _number(value)
    if number is None or abs(number) < 0.01:
        return "pt-flat"
    return "pt-up" if number > 0 else "pt-down"


def _badge(text: object, tone: str = "info") -> str:
    return f'<span class="pt-badge {tone}">{_html(text)}</span>'


def _panel(title: str, body: str, meta: str = "", tight: bool = False) -> str:
    panel_class = "pt-panel-tight" if tight else "pt-panel"
    return (
        f'<section class="{panel_class}">'
        f'<div class="pt-section-head"><span class="pt-section-title">{_html(title)}</span>'
        f'<span class="pt-section-meta">{_html(meta)}</span></div>{body}</section>'
    )


def render_page_header(code: str, title: str, subtitle: str) -> None:
    current = now_et().strftime("%H:%M:%S ET")
    st.markdown(
        f'<div class="pt-command-row"><span class="pt-page-code">{_html(code)}</span>'
        f'<span class="pt-page-title">{_html(title)}</span><span class="pt-page-sub">{_html(subtitle)}</span>'
        f'<span class="pt-asof">AS OF {current}</span></div>',
        unsafe_allow_html=True,
    )


@st.fragment(run_every="10s")
def render_market_tape(selected_ticker: str = "") -> None:
    quotes = market_quotes(selected_ticker)
    if quotes.empty:
        st.markdown('<div class="pt-tape"><span class="pt-tape-item pt-muted">QUOTE FEED UNAVAILABLE</span></div>', unsafe_allow_html=True)
        return
    items: list[str] = []
    for _, row in quotes.iterrows():
        symbol = str(row.get("ticker") or "")
        price = _number(row.get("price"))
        move = _number(row.get("change_pct"))
        price_label = f"{price:,.2f}" if price is not None else "N/A"
        items.append(
            f'<span class="pt-tape-item"><span class="pt-strong">{_html(symbol)}</span> '
            f'<span class="pt-muted">{price_label}</span> <span class="{_tone(move)}">{_pct(move, 2)}</span></span>'
        )
    track = "".join(items + items)
    st.markdown(f'<div class="pt-tape"><div class="pt-tape-track">{track}</div></div>', unsafe_allow_html=True)


def _kpi_grid(items: Iterable[tuple[str, str, str, str]]) -> str:
    cards = []
    for label, value, note, tone in items:
        cards.append(
            f'<div class="pt-kpi"><div class="pt-kpi-label">{_html(label)}</div>'
            f'<div class="pt-kpi-value {tone}">{_html(value)}</div><div class="pt-kpi-note">{_html(note)}</div></div>'
        )
    return f'<div class="pt-kpi-grid">{"".join(cards)}</div>'


def _sector_strip(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<div class="pt-sector-strip"><div class="pt-sector"><span class="pt-sector-name">Sector feed</span><span class="pt-sector-move pt-flat">N/A</span></div></div>'
    quote_map = {str(row.get("ticker")): row for _, row in frame.iterrows()}
    short_names = {
        "XLK": "Tech", "XLC": "Comm", "XLY": "Discret.", "XLF": "Financials", "XLI": "Industrials",
        "XLE": "Energy", "XLV": "Health", "XLB": "Materials", "XLRE": "Real Est.", "XLP": "Staples", "XLU": "Utilities",
    }
    cells = []
    for ticker in SECTOR_NAMES:
        row = quote_map.get(ticker, {})
        move = _number(row.get("change_pct"))
        cells.append(
            f'<div class="pt-sector" title="{_html(SECTOR_NAMES.get(ticker, ticker))}"><span class="pt-sector-name">{_html(short_names.get(ticker, ticker))}</span>'
            f'<span class="pt-sector-move {_tone(move)}">{_pct(move, 1)}</span></div>'
        )
    return f'<div class="pt-sector-strip">{"".join(cells)}</div>'


def _mover_table(frame: pd.DataFrame, limit: int = 8) -> str:
    if frame is None or frame.empty:
        return '<div class="pt-muted">No market-wide observations available.</div>'
    rows = []
    for _, row in frame.head(limit).iterrows():
        move = _number(row.get("Daily Move %"))
        rows.append(
            "<tr>"
            f'<td class="pt-strong pt-mono">{_html(row.get("Ticker"))}</td>'
            f'<td>{_html(str(row.get("Company") or row.get("Ticker"))[:26])}</td>'
            f'<td class="pt-mono">{_money(row.get("Price"), 2)}</td>'
            f'<td class="pt-mono {_tone(move)}">{_pct(move, 2)}</td>'
            f'<td class="pt-mono">{_count(row.get("Volume"))}</td>'
            f'<td class="pt-mono">{_multiple(row.get("Relative Volume"))}</td>'
            "</tr>"
        )
    return (
        '<table class="pt-table"><thead><tr><th style="width:13%">Ticker</th><th>Name</th>'
        '<th style="width:16%">Last</th><th style="width:15%">Move</th><th style="width:15%">Volume</th>'
        f'<th style="width:13%">Rel Vol</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _macro_table(frame: pd.DataFrame, limit: int = 8) -> str:
    if frame.empty:
        return '<div class="pt-muted">Official macro feed unavailable. Synthetic values are disabled.</div>'

    def stamp(value: object, include_time: bool = False) -> str:
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return "N/A"
        local = pd.Timestamp(parsed).tz_convert("America/New_York")
        return local.strftime("%m/%d %H:%M ET" if include_time else "%m/%d/%y")

    rows = []
    for _, row in frame.head(limit).iterrows():
        change = _number(row.get("change"))
        source_url = str(row.get("source_url") or "")
        source = _html(row.get("source") or row.get("data_source") or "Official source")
        source_link = f'<a class="pt-source-link" href="{_html(source_url)}" target="_blank">{source}</a>' if source_url.startswith("https://") else source
        next_release = stamp(row.get("next_release_at"), include_time=True)
        rows.append(
            "<tr>"
            f'<td><span class="pt-strong">{_html(row.get("indicator"))}</span><br><span class="pt-micro">{source_link}</span></td>'
            f'<td class="pt-mono pt-strong">{_html(row.get("display_value"))}</td>'
            f'<td class="pt-mono {_tone(change)}">{_html(row.get("display_change"))}</td>'
            f'<td class="pt-mono">{_html(row.get("observation_period"))}</td>'
            f'<td class="pt-mono pt-muted">{stamp(row.get("official_release_at"), include_time=True)}</td>'
            f'<td class="pt-mono pt-warn">{next_release}</td>'
            "</tr>"
        )
    return (
        '<table class="pt-table pt-macro-table"><thead><tr><th>Series / Source</th><th style="width:13%">Latest</th>'
        '<th style="width:13%">Change</th><th style="width:14%">Period</th><th style="width:18%">Published</th>'
        f'<th style="width:18%">Next Release</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _macro_audit_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<div class="pt-muted">No macro audit result available.</div>'
    rows = []
    for _, row in frame.iterrows():
        status = str(row.get("audit_status") or "REVIEW")
        tone = "ok" if status == "VERIFIED" else "bad" if status == "BLOCKED" else "warn"
        next_release = pd.to_datetime(row.get("next_release_at"), errors="coerce", utc=True)
        next_label = pd.Timestamp(next_release).tz_convert("America/New_York").strftime("%m/%d %H:%M ET") if not pd.isna(next_release) else "N/A"
        source_url = str(row.get("source_url") or "")
        source = _html(row.get("source") or "Official source")
        source_link = f'<a class="pt-source-link" href="{_html(source_url)}" target="_blank">{source}</a>' if source_url.startswith("https://") else source
        rows.append(
            "<tr>"
            f'<td class="pt-strong">{_html(row.get("indicator"))}</td><td>{_badge(status, tone)}</td>'
            f'<td>{_html(row.get("audit_message"))}</td><td class="pt-mono">{_html(row.get("observation_period"))}</td>'
            f'<td class="pt-mono pt-warn">{next_label}</td><td>{source_link}</td>'
            "</tr>"
        )
    return (
        '<table class="pt-table"><thead><tr><th style="width:17%">Series</th><th style="width:10%">Audit</th>'
        '<th>Finding</th><th style="width:12%">Period</th><th style="width:16%">Next</th>'
        f'<th style="width:16%">Authority</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


@st.fragment(run_every="15s")
def render_macro_release_monitor() -> None:
    frame = macro_dashboard()
    alerts = process_macro_updates(frame)
    shown = st.session_state.setdefault("shown_macro_alerts", set())
    for alert in alerts:
        alert_id = int(alert.get("id") or 0)
        if alert_id and alert_id not in shown:
            st.toast(str(alert.get("message") or "Official macro data updated."))
            shown.add(alert_id)
    upcoming = next_scheduled_macro_release()
    release_at = pd.to_datetime(upcoming.get("release_at"), errors="coerce", utc=True)
    if pd.isna(release_at):
        return
    local = pd.Timestamp(release_at).tz_convert("America/New_York")
    hours = (local - pd.Timestamp(now_et())).total_seconds() / 3_600
    if hours > 48:
        return
    cadence = macro_poll_interval_seconds()
    cadence_label = f"{cadence}s POLL" if cadence <= 300 else "WAKE 5M PRE-RELEASE"
    st.markdown(
        '<div class="pt-release-bar">'
        '<span class="pt-release-kicker">NEXT OFFICIAL MACRO</span>'
        f'<span class="pt-release-name">{_html(upcoming.get("release_name"))}</span>'
        f'<span class="pt-mono">{local.strftime("%a %m/%d %I:%M %p ET")}</span>'
        f'<span class="pt-release-state">ALERTS ARMED / {cadence_label}</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _news_wire(frame: pd.DataFrame, limit: int = 9) -> str:
    if frame.empty:
        return '<div class="pt-muted">No verified headlines available.</div>'
    rows = ['<div class="pt-wire pt-wire-head"><span>Time</span><span>Scope</span><span>Headline</span><span>Impact</span><span>Source</span></div>']
    for _, row in frame.head(limit).iterrows():
        stamp = pd.to_datetime(row.get("published_at"), errors="coerce")
        time_label = stamp.strftime("%m/%d %H:%M") if not pd.isna(stamp) else "N/A"
        sentiment = str(row.get("sentiment") or "Neutral")
        badge_tone = "ok" if sentiment.casefold() == "bullish" else "bad" if sentiment.casefold() == "bearish" else "warn"
        rows.append(
            '<div class="pt-wire">'
            f'<span class="pt-mono pt-muted">{_html(time_label)}</span>'
            f'<span class="pt-mono pt-strong">{_html(row.get("ticker") or "MACRO")}</span>'
            f'<span>{_html(row.get("headline"))}</span><span>{_badge(sentiment, badge_tone)}</span>'
            f'<span class="pt-muted">{_html(row.get("source"))}</span></div>'
        )
    return "".join(rows)


def _social_table(frame: pd.DataFrame, limit: int = 8) -> str:
    if frame.empty:
        return '<div class="pt-muted">No reliable social observations available.</div>'
    rows = []
    sorted_frame = frame.sort_values("mention_count", ascending=False).head(limit)
    for rank, (_, row) in enumerate(sorted_frame.iterrows(), 1):
        sentiment = str(row.get("sentiment_label") or "Neutral")
        sentiment_tone = "ok" if sentiment.casefold() == "bullish" else "bad" if sentiment.casefold() == "bearish" else "warn"
        score = _number(row.get("social_momentum_score"))
        if score is None:
            score = _number(row.get("confidence_score"))
        signal = str(row.get("signal_label") or row.get("social_signal") or "Attention")
        rows.append(
            "<tr>"
            f'<td class="pt-mono pt-muted">{rank}</td><td class="pt-mono pt-strong">{_html(row.get("ticker"))}</td>'
            f'<td class="pt-mono">{_count(row.get("mention_count"))}</td>'
            f'<td class="pt-mono {_tone(row.get("mention_change_pct"))}">{_pct(row.get("mention_change_pct"), 0)}</td>'
            f'<td>{_badge(sentiment, sentiment_tone)}</td><td class="pt-mono">{score:.0f}</td><td>{_html(signal)}</td>'
            "</tr>"
        )
    return (
        '<table class="pt-table"><thead><tr><th style="width:6%">#</th><th style="width:12%">Ticker</th>'
        '<th style="width:17%">Mentions</th><th style="width:15%">24H</th><th style="width:17%">Sentiment</th>'
        f'<th style="width:10%">Score</th><th>Read</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _market_brief(quotes: pd.DataFrame, sectors: pd.DataFrame, movers: dict, macro: pd.DataFrame) -> str:
    if quotes.empty:
        return "Market regime cannot be assessed because the benchmark quote feed is unavailable."
    equity = quotes[quotes["ticker"].isin(["SPY", "QQQ", "IWM", "DIA"])].copy()
    moves = pd.to_numeric(equity.get("change_pct"), errors="coerce").dropna()
    avg_move = float(moves.mean()) if not moves.empty else 0.0
    sector_moves = pd.to_numeric(sectors.get("change_pct"), errors="coerce") if not sectors.empty else pd.Series(dtype=float)
    positive_sectors = int((sector_moves > 0).sum())
    breadth = "broad" if positive_sectors >= 8 else "narrow" if positive_sectors <= 4 else "mixed"
    leaders = []
    if not sectors.empty:
        ranked = sectors.assign(_move=pd.to_numeric(sectors["change_pct"], errors="coerce")).sort_values("_move", ascending=False)
        leaders = [SECTOR_NAMES.get(str(item), str(item)) for item in ranked.get("ticker", pd.Series(dtype=str)).head(2)]
    ten_year = macro[macro["indicator"].astype(str).str.contains("10Y", case=False, na=False)] if not macro.empty else pd.DataFrame()
    rate_note = "Rates signal unavailable."
    if not ten_year.empty:
        change = _number(ten_year.iloc[0].get("change"))
        rate_note = "Long yields are rising, a valuation headwind." if change and change > 0 else "Long yields are stable-to-lower, easing duration pressure."
    direction = "risk-on" if avg_move > 0.35 else "risk-off" if avg_move < -0.35 else "range-bound"
    leader_copy = ", ".join(leaders) if leaders else "sector leadership unavailable"
    return (
        f"The tape is <strong>{direction}</strong> with <strong>{breadth} breadth</strong>: major equity benchmarks average "
        f"<span class=\"{_tone(avg_move)}\">{_pct(avg_move, 2)}</span> and leadership is concentrated in {escape(leader_copy)}. "
        f"{escape(rate_note)} Treat index direction as confirmed only if sector breadth and market-wide volume continue to agree."
    )


@st.fragment(run_every="60s")
def _render_market_pulse() -> None:
    quotes = benchmark_quotes()
    sectors = sector_quotes()
    packet = movers_packet()
    macro = macro_dashboard()
    quote_map = {str(row.get("ticker")): row for _, row in quotes.iterrows()}
    kpis = []
    for symbol, label in (("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("IWM", "Small Caps"), ("TLT", "Long Duration")):
        row = quote_map.get(symbol, {})
        price = _number(row.get("price"))
        move = _number(row.get("change_pct"))
        kpis.append((label, f"{price:,.2f}" if price is not None else "N/A", f"{symbol}  {_pct(move, 2)}", _tone(move)))
    st.markdown(_kpi_grid(kpis), unsafe_allow_html=True)
    st.markdown(_sector_strip(sectors), unsafe_allow_html=True)
    breadth_frame = packet.get("all_scanned", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
    advancers = int((pd.to_numeric(breadth_frame.get("Daily Move %"), errors="coerce") > 0).sum()) if not breadth_frame.empty else 0
    breadth_total = len(breadth_frame)
    meta = f"{advancers}/{breadth_total} ADVANCING" if breadth_total else "BREADTH UNAVAILABLE"
    st.markdown(_panel("Analyst Market Brief", f'<div class="pt-brief">{_market_brief(quotes, sectors, packet, macro)}</div>', meta), unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])
    with left:
        gainers = packet.get("gainers", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
        losers = packet.get("losers", pd.DataFrame()) if isinstance(packet, dict) else pd.DataFrame()
        tabs = st.tabs(["Upside Dislocation", "Downside Dislocation"])
        with tabs[0]:
            st.markdown(_panel("Market Movers", _mover_table(gainers), "PRICE + VOLUME CONFIRMATION"), unsafe_allow_html=True)
        with tabs[1]:
            st.markdown(_panel("Market Movers", _mover_table(losers), "PRICE + VOLUME CONFIRMATION"), unsafe_allow_html=True)
    with right:
        macro_status = classify_frame(macro)
        st.markdown(_panel("Macro Regime Monitor", _macro_table(macro), macro_status.upper()), unsafe_allow_html=True)


@st.fragment(run_every="2min")
def _render_market_news() -> None:
    news = market_news()
    status = classify_frame(news)
    st.markdown(_panel("Catalyst Wire", _news_wire(news), f"{status.upper()} / 120S"), unsafe_allow_html=True)


@st.fragment(run_every="5min")
def _render_social_market() -> None:
    social = social_market()
    status = classify_frame(social, "source")
    themes = social_themes()
    left, right = st.columns([1.45, 0.75])
    with left:
        st.markdown(_panel("Retail Attention Radar", _social_table(social), f"{status.upper()} / 300S"), unsafe_allow_html=True)
    with right:
        rows = []
        for _, row in themes.head(7).iterrows():
            rows.append(
                f'<div class="risk-row"><div class="pt-risk-row"><span class="pt-strong">{_html(row.get("theme"))}</span>'
                f'<span class="pt-mono pt-up">{_count(row.get("total_mentions"))}</span>'
                f'<span class="pt-muted">{_html(row.get("top_tickers"))}</span></div></div>'
            )
        warning = '<div class="pt-muted" style="font-size:.63rem;margin-top:9px">Attention is a positioning input, not a standalone investment thesis.</div>'
        st.markdown(_panel("Narrative Concentration", "".join(rows) + warning, "CROSS-PLATFORM"), unsafe_allow_html=True)


def render_market_page() -> None:
    render_page_header("MKT <GO>", "Market Monitor", "Regime, breadth, liquidity, catalysts, and positioning")
    render_market_tape(st.session_state.get("ticker", ""))
    _render_market_pulse()
    _render_social_market()
    _render_market_news()


def _signal_copy(signal: dict, quote: dict, analysis: Any) -> tuple[str, str]:
    label = str(signal.get("signal_label") or getattr(getattr(analysis, "investment_signal", None), "signal", None) or "No Rating")
    growth = _number(signal.get("growth_score"))
    valuation = _number(signal.get("valuation_score"))
    risk_items = list(signal.get("bearish_drivers") or signal.get("weaknesses") or [])
    positive = list(signal.get("bullish_drivers") or signal.get("strengths") or [])
    lead = positive[0] if positive else "Available evidence does not establish a durable positive edge."
    risk = risk_items[0] if risk_items else "The principal risk is not resolved by the available dataset."
    if label.casefold() in {"hold", "neutral", "market weight"} or "hold" in label.casefold():
        first = "Fundamentals are improving, but the current price already discounts much of the upside."
        second = "New evidence matters more than headline valuation from here."
    elif any(word in label.casefold() for word in ("buy", "bullish", "accumulate")):
        first = f"The evidence is constructive: {lead}"
        second = f"The call still depends on execution because {risk}"
    elif any(word in label.casefold() for word in ("sell", "avoid", "bearish", "trim")):
        first = f"Risk-reward is unfavorable: {risk}"
        second = "A better entry requires either lower expectations or evidence that the operating trajectory has changed."
    else:
        first = "The available evidence is not complete enough for a high-conviction recommendation."
        second = "Use the missing-data flags and upcoming catalysts as the next research checklist."
    if growth is not None and valuation is not None and growth - valuation > 25:
        second += " Operating momentum is materially stronger than valuation support."
    return label, f"{first} {second}"


def _score_bars(signal: dict) -> str:
    metrics = (
        ("Growth", signal.get("growth_score")),
        ("Profitability", signal.get("profitability_score")),
        ("Balance Sheet", signal.get("balance_sheet_score")),
        ("Valuation", signal.get("valuation_score")),
        ("Momentum", signal.get("momentum_score")),
        ("Catalyst", signal.get("catalyst_score")),
    )
    rows = []
    for label, raw in metrics:
        score = _number(raw)
        width = max(0, min(100, score or 0))
        tone = "ok" if (score or 0) >= 65 else "warn" if (score or 0) >= 45 else "bad"
        rows.append(
            f'<div class="pt-score"><span class="pt-score-label">{_html(label)}</span>'
            f'<span class="pt-score-track"><span class="pt-score-fill {tone}" style="display:block;width:{width:.0f}%"></span></span>'
            f'<span class="pt-score-value">{score:.0f}</span></div>' if score is not None else
            f'<div class="pt-score"><span class="pt-score-label">{_html(label)}</span><span class="pt-score-track"></span><span class="pt-score-value">N/A</span></div>'
        )
    return "".join(rows)


def _price_figure(history: pd.DataFrame, ticker: str) -> go.Figure:
    figure = go.Figure()
    if history is not None and not history.empty and "Close" in history:
        close = pd.to_numeric(history["Close"], errors="coerce")
        figure.add_trace(go.Scatter(x=history.index, y=close, mode="lines", line={"color": "#f4b942", "width": 1.5}, name=ticker))
        if "Volume" in history:
            volume = pd.to_numeric(history["Volume"], errors="coerce")
            max_volume = volume.max()
            if pd.notna(max_volume) and max_volume:
                price_min = close.min()
                price_range = max(float(close.max() - price_min), 1)
                scaled = price_min - price_range * 0.16 + (volume / max_volume) * price_range * 0.13
                figure.add_trace(go.Bar(x=history.index, y=scaled, base=price_min - price_range * 0.18, marker_color="#223344", name="Volume", opacity=0.65))
    figure.update_layout(
        height=320,
        margin={"l": 8, "r": 12, "t": 12, "b": 5},
        paper_bgcolor="#0b1118",
        plot_bgcolor="#0b1118",
        font={"color": "#9eabba", "size": 10},
        xaxis={"showgrid": False, "rangeslider": {"visible": False}},
        yaxis={"gridcolor": "#1b2633", "side": "right", "tickformat": ",.2f"},
        showlegend=False,
        hovermode="x unified",
    )
    return figure


def _history_frame(financials: dict) -> pd.DataFrame:
    quarterly = financials.get("quarterly_history")
    if isinstance(quarterly, pd.DataFrame) and not quarterly.empty:
        return quarterly.tail(10).copy()
    annual = financials.get("annual_history")
    return annual.tail(8).copy() if isinstance(annual, pd.DataFrame) else pd.DataFrame()


def _financial_figure(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    if frame.empty:
        return figure
    labels = []
    for index, row in frame.iterrows():
        label = row.get("period_label") or row.get("period") or row.get("date") or index
        labels.append(str(label)[:10])
    revenue = pd.to_numeric(frame.get("revenue"), errors="coerce") if "revenue" in frame else pd.Series(index=frame.index, dtype=float)
    margin = pd.to_numeric(frame.get("gross_margin"), errors="coerce") if "gross_margin" in frame else pd.Series(index=frame.index, dtype=float)
    if revenue.notna().any():
        figure.add_trace(go.Bar(x=labels, y=revenue / 1_000_000, name="Revenue ($M)", marker_color="#2f7cc5"))
    if margin.notna().any():
        margin_display = margin * 100 if margin.abs().median() <= 1.5 else margin
        figure.add_trace(go.Scatter(x=labels, y=margin_display, name="Gross margin %", yaxis="y2", line={"color": "#43c981", "width": 2}, mode="lines+markers"))
    figure.update_layout(
        height=320,
        margin={"l": 8, "r": 12, "t": 12, "b": 5},
        paper_bgcolor="#0b1118",
        plot_bgcolor="#0b1118",
        font={"color": "#9eabba", "size": 10},
        xaxis={"showgrid": False},
        yaxis={"gridcolor": "#1b2633", "title": "$M"},
        yaxis2={"overlaying": "y", "side": "right", "showgrid": False, "title": "%"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        hovermode="x unified",
    )
    return figure


def _progression_tiles(frame: pd.DataFrame, quote: dict) -> str:
    latest = frame.iloc[-1] if not frame.empty else {}
    prior = frame.iloc[-2] if len(frame) > 1 else {}

    def delta(key: str) -> float | None:
        current = _number(latest.get(key)) if hasattr(latest, "get") else None
        previous = _number(prior.get(key)) if hasattr(prior, "get") else None
        return ((current / previous) - 1) * 100 if current is not None and previous not in (None, 0) else None

    revenue = _number(latest.get("revenue")) if hasattr(latest, "get") else None
    gross_margin = _number(latest.get("gross_margin")) if hasattr(latest, "get") else _number(quote.get("gross_margin"))
    operating_margin = _number(latest.get("operating_margin")) if hasattr(latest, "get") else _number(quote.get("operating_margin"))
    fcf = _number(latest.get("free_cash_flow")) if hasattr(latest, "get") else _number(quote.get("free_cash_flow"))
    if gross_margin is not None and abs(gross_margin) <= 1.5:
        gross_margin *= 100
    if operating_margin is not None and abs(operating_margin) <= 1.5:
        operating_margin *= 100
    tiles = (
        ("Revenue", _money(revenue), f"Sequential change {_pct(delta('revenue'), 1)}", "blue"),
        ("Gross Margin", f"{gross_margin:.1f}%" if gross_margin is not None else "N/A", f"Progression {_pct(delta('gross_margin'), 1)}", "green"),
        ("Operating Margin", f"{operating_margin:.1f}%" if operating_margin is not None else "N/A", "Operating leverage checkpoint", "amber"),
        ("Free Cash Flow", _money(fcf), "Self-funding and dilution checkpoint", "red" if fcf is not None and fcf < 0 else "green"),
    )
    return '<div class="pt-grid-2">' + "".join(
        f'<div class="pt-stat {tone}"><div class="pt-stat-label">{_html(label)}</div><div class="pt-stat-value">{_html(value)}</div><div class="pt-stat-note">{_html(note)}</div></div>'
        for label, value, note, tone in tiles
    ) + "</div>"


def _scenario_table(analysis: Any) -> str:
    scenarios = list(getattr(analysis, "valuation_scenarios", []) or [])
    if not scenarios:
        return '<div class="pt-muted">No decision-grade valuation scenarios available.</div>'
    rows = []
    for scenario in scenarios:
        ret = _number(getattr(scenario, "implied_return", None))
        quality = str(getattr(scenario, "assumption_quality", "Model") or "Model")
        rows.append(
            "<tr>"
            f'<td class="pt-strong">{_html(getattr(scenario, "name", "Scenario"))}</td>'
            f'<td class="pt-mono">{_money(getattr(scenario, "future_share_price", None), 2)}</td>'
            f'<td class="pt-mono {_tone(ret)}">{_return_pct(ret, 1)}</td>'
            f'<td class="pt-mono">{_pct((_number(getattr(scenario, "probability", None)) or 0), 0, fractional=True)}</td>'
            f'<td class="pt-mono">{_multiple(getattr(scenario, "valuation_multiple", None) or getattr(scenario, "ev_sales_multiple", None))}</td>'
            f'<td>{_html(quality)}</td></tr>'
        )
    return (
        '<table class="pt-table"><thead><tr><th>Case</th><th>Value</th><th>Return</th><th>Weight</th><th>Multiple</th><th>Input quality</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _peer_table(frame: pd.DataFrame, selected: str) -> str:
    if frame.empty:
        return '<div class="pt-muted">Peer fundamentals are unavailable.</div>'
    rows = []
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker") or "")
        selected_class = "pt-warn" if ticker == selected else ""
        rows.append(
            "<tr>"
            f'<td class="pt-mono pt-strong {selected_class}">{_html(ticker)}</td><td>{_html(str(row.get("company") or ticker)[:24])}</td>'
            f'<td class="pt-mono">{_money(row.get("market_cap"))}</td><td class="pt-mono">{_pct(row.get("revenue_growth"), 1, fractional=True)}</td>'
            f'<td class="pt-mono">{_pct(row.get("gross_margin"), 1, fractional=True)}</td><td class="pt-mono">{_multiple(row.get("ev_to_sales"))}</td>'
            f'<td class="pt-mono {_tone(row.get("return_3m"))}">{_pct(row.get("return_3m"), 1)}</td><td>{_html(row.get("relative_read"))}</td></tr>'
        )
    return (
        '<table class="pt-table"><thead><tr><th>Ticker</th><th>Company</th><th>Mkt Cap</th><th>Rev Growth</th>'
        f'<th>Gross Mgn</th><th>EV/Sales</th><th>3M Rel.</th><th>Position</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _risk_table(analysis: Any, signal: dict) -> str:
    risks = list(getattr(analysis, "risks", []) or [])[:3]
    if risks:
        rows = []
        for risk in risks:
            severity = str(getattr(risk, "severity", "Monitor"))
            tone = "bad" if severity.casefold() == "high" else "warn"
            rows.append(
                '<div class="pt-risk-row">'
                f'<span class="pt-strong">{_html(getattr(risk, "risk_name", "Risk"))}</span><span>{_badge(severity, tone)}</span>'
                f'<span><span>{_html(getattr(risk, "description", ""))}</span><br><span class="pt-muted">Risk reducer: {_html(getattr(risk, "mitigant", "No mitigant identified"))}</span></span></div>'
            )
        return "".join(rows)
    weaknesses = list(signal.get("weaknesses") or [])[:3]
    return "".join(f'<div class="pt-risk-row"><span class="pt-strong">Risk {idx}</span><span>{_badge("Monitor", "warn")}</span><span>{_html(item)}</span></div>' for idx, item in enumerate(weaknesses, 1))


def _social_readthrough(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<div class="pt-muted">No reliable social data available.</div>'
    row = frame.iloc[0]
    source_status = frame.attrs.get("status", {}) if hasattr(frame, "attrs") else {}
    status_text = str(source_status.get("Mode") or source_status.get("Status") or row.get("source") or "Social data")
    mention_change = _number(row.get("mention_change_pct"))
    sentiment = str(row.get("sentiment_label") or "Neutral")
    score = _number(row.get("social_momentum_score")) or _number(row.get("confidence_score"))
    narrative = str(row.get("theme") or "Broad retail attention")
    sentiment_tile = (
        f'<div class="pt-stat blue"><div class="pt-stat-label">Sentiment</div><div class="pt-stat-value">{_html(sentiment)}</div><div class="pt-stat-note">Score {score:.0f} / 100</div></div>'
        if score is not None
        else f'<div class="pt-stat blue"><div class="pt-stat-label">Sentiment</div><div class="pt-stat-value">{_html(sentiment)}</div><div class="pt-stat-note">Score unavailable</div></div>'
    )
    return (
        '<div class="pt-grid-3">'
        f'<div class="pt-stat amber"><div class="pt-stat-label">Mentions</div><div class="pt-stat-value">{_count(row.get("mention_count"))}</div><div class="pt-stat-note"><span class="{_tone(mention_change)}">{_pct(mention_change, 0)}</span> in 24h</div></div>'
        f'{sentiment_tile}'
        f'<div class="pt-stat red"><div class="pt-stat-label">Narrative / Risk</div><div class="pt-stat-value">{_html(narrative)}</div><div class="pt-stat-note">{_html(status_text)}</div></div></div>'
        '<div class="pt-muted" style="font-size:.65rem;margin-top:9px">Social momentum is an attention signal, not a standalone investment thesis. Confirm with price, volume, catalyst, fundamentals, and risk controls.</div>'
    )


def _filings_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<div class="pt-muted">No recent SEC filing metadata available.</div>'
    rows = []
    for _, row in frame.head(4).iterrows():
        url = str(row.get("Link") or "")
        form = _html(row.get("Form"))
        link = f'<a href="{_html(url)}" target="_blank" style="color:#76b7ff;text-decoration:none">{form}</a>' if url.startswith("http") else form
        rows.append(f'<tr><td class="pt-mono pt-strong">{link}</td><td class="pt-mono">{_html(row.get("Filing Date"))}</td><td class="pt-mono pt-muted">{_html(row.get("Accession"))}</td></tr>')
    return f'<table class="pt-table"><thead><tr><th>Form</th><th>Filed</th><th>Accession</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def render_security_page(ticker: str) -> None:
    symbol = clean_ticker(ticker) or "SPY"
    render_page_header(f"{symbol} <GO>", "Security Underwriting", "Recommendation, earnings progression, valuation, peers, and catalysts")
    render_market_tape(symbol)
    with st.spinner(f"Loading decision-grade packet for {symbol}..."):
        packet = security_packet(symbol)
    analysis = packet.get("analysis")
    financials = packet.get("financials") or {}
    signal = packet.get("signal") or {}
    company = getattr(analysis, "company", None)
    quote = financials.get("latest_quote") or {}
    company_name = getattr(company, "company_name", None) or (financials.get("company_profile") or {}).get("company_name") or symbol
    sector = getattr(company, "sector", None) or quote.get("sector") or "N/A"
    industry = getattr(company, "industry", None) or quote.get("industry") or "N/A"
    label, call_copy = _signal_copy(signal, quote, analysis)
    score = _number(signal.get("composite_score"))
    confidence = str(signal.get("confidence") or "Low")
    data_complete = _number(signal.get("data_completeness"))
    current_price = _number(quote.get("price")) or _number(getattr(company, "current_price", None))
    target = _number(quote.get("target_mean_price"))
    expected_return = ((target / current_price) - 1) * 100 if target is not None and current_price not in (None, 0) else _number(getattr(analysis, "expected_value_detail", None) and getattr(analysis.expected_value_detail, "expected_return", None))
    if expected_return is not None and abs(expected_return) <= 3:
        expected_return *= 100
    signal_lower = label.casefold()
    call_tone = (
        "ok" if any(word in signal_lower for word in ("buy", "bullish", "accumulate"))
        else "bad" if any(word in signal_lower for word in ("sell", "avoid", "bearish", "trim"))
        else "warn"
    )
    quality_label = str(financials.get("status") or "Partial")

    identity = (
        f'<div class="pt-panel"><div class="pt-section-head"><span class="pt-section-title">{_html(symbol)} / { _html(company_name)}</span>'
        f'<span class="pt-section-meta">{_html(sector)} / {_html(industry)}</span></div>'
        + _kpi_grid(
            [
                ("Last Price", f"${current_price:,.2f}" if current_price is not None else "N/A", _pct(quote.get("daily_change_pct"), 2), _tone(quote.get("daily_change_pct"))),
                ("Market Cap", _money(quote.get("market_cap")), "Equity value", ""),
                ("Street Target", f"${target:,.2f}" if target is not None else "N/A", f"Implied {_pct(expected_return, 1)}" if expected_return is not None else "Consensus unavailable", _tone(expected_return)),
                (
                    "Data Quality",
                    quality_label,
                    f"Coverage {data_complete:.0f}%" if data_complete is not None else "Coverage unavailable",
                    "pt-up" if quality_label.casefold() in {"ok", "valid"} else "pt-warn",
                ),
            ]
        ) + "</div>"
    )
    st.markdown(identity, unsafe_allow_html=True)

    left, right = st.columns([1.2, 0.8])
    with left:
        score_copy = f'<span>Composite {score:.0f}/100</span>' if score is not None else '<span>Composite score unavailable</span>'
        call_html = (
            f'<div class="pt-call {call_tone}"><div class="pt-call-label">PineTerminal Recommendation</div>'
            f'<div class="pt-call-value">{_html(label)}</div><div class="pt-call-copy">{_html(call_copy)}</div>'
            f'<div class="pt-source-line" style="margin-top:10px">{_badge(confidence + " conviction", "warn")}'
            f'{score_copy}'
        ) + "</div></div>"
        st.markdown(_panel("Investment View", call_html, "RECOMMENDATION FIRST"), unsafe_allow_html=True)
    with right:
        st.markdown(_panel("Factor Attribution", _score_bars(signal), "0-100"), unsafe_allow_html=True)

    chart_col, progression_col = st.columns([1.35, 1])
    with chart_col:
        with st.container(border=True):
            st.markdown('<div class="pt-section-head"><span class="pt-section-title">Price / Volume</span><span class="pt-section-meta">2Y DAILY</span></div>', unsafe_allow_html=True)
            st.plotly_chart(_price_figure(packet.get("history", pd.DataFrame()), symbol), use_container_width=True, config={"displayModeBar": False})
    history = _history_frame(financials)
    with progression_col:
        with st.container(border=True):
            st.markdown('<div class="pt-section-head"><span class="pt-section-title">Operating Progression</span><span class="pt-section-meta">REPORTED PERIODS</span></div>', unsafe_allow_html=True)
            st.plotly_chart(_financial_figure(history), use_container_width=True, config={"displayModeBar": False})

    st.markdown(_panel("Long-Term Decision Metrics", _progression_tiles(history, quote), "TREND + LEVEL"), unsafe_allow_html=True)

    valuation_col, peer_col = st.columns([0.9, 1.45])
    with valuation_col:
        model = getattr(analysis, "valuation_model", None)
        model_status = str(getattr(model, "data_status", "Model") if model else "Unavailable")
        st.markdown(_panel("Valuation Scenarios", _scenario_table(analysis), model_status.upper()), unsafe_allow_html=True)
    with peer_col:
        peer_meta = packet.get("peer_status") or {}
        st.markdown(_panel("Competitive Intelligence", _peer_table(packet.get("peers", pd.DataFrame()), symbol), str(peer_meta.get("status") or "Partial").upper()), unsafe_allow_html=True)

    risk_col, social_col = st.columns([1, 1])
    with risk_col:
        st.markdown(_panel("Top Underwriting Risks", _risk_table(analysis, signal), "TOP 3"), unsafe_allow_html=True)
    with social_col:
        social = packet.get("social", pd.DataFrame())
        st.markdown(_panel("Social Read-Through", _social_readthrough(social), classify_frame(social, "source").upper()), unsafe_allow_html=True)

    filings_col, news_col = st.columns([0.75, 1.45])
    with filings_col:
        filing_status = packet.get("filing_status") or {}
        st.markdown(_panel("Regulatory Filings", _filings_table(packet.get("filings", pd.DataFrame())), str(filing_status.get("Status") or "SEC EDGAR").upper()), unsafe_allow_html=True)
    with news_col:
        news = packet.get("news", pd.DataFrame())
        st.markdown(_panel("Company Catalyst Wire", _news_wire(news, 6), classify_frame(news).upper()), unsafe_allow_html=True)

    with st.expander("Model assumptions, missing data, and provenance", expanded=False):
        warnings = list(financials.get("validation_warnings") or []) + list(signal.get("missing_data_warnings") or [])
        source_meta = financials.get("source_metadata") or {}
        st.write("Warnings:", warnings or ["No validation warning returned."])
        st.json(source_meta, expanded=False)


def _intelligence_rows(news: pd.DataFrame, social: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, item in news.head(30).iterrows():
        sentiment = str(item.get("sentiment") or "Neutral")
        rows.append(
            {
                "timestamp": item.get("published_at"),
                "type": "Company" if item.get("ticker") else "Market",
                "scope": item.get("ticker") or "Macro",
                "event": item.get("headline"),
                "impact": sentiment,
                "transmission": "Revenue / expectations" if item.get("ticker") else "Discount rate / risk appetite",
                "source": item.get("source"),
                "data_status": item.get("data_source"),
            }
        )
    for _, item in social.sort_values("mention_count", ascending=False).head(15).iterrows() if not social.empty else []:
        velocity = _number(item.get("mention_change_pct")) or 0
        rows.append(
            {
                "timestamp": item.get("last_updated"),
                "type": "Positioning",
                "scope": item.get("ticker"),
                "event": f"Retail mentions {_pct(velocity, 0)}; {item.get('theme') or 'broad narrative'}",
                "impact": item.get("sentiment_label") or "Neutral",
                "transmission": "Attention / liquidity / squeeze risk",
                "source": item.get("source") or "Social provider",
                "data_status": (social.attrs.get("status") or {}).get("Mode") if hasattr(social, "attrs") else "Social",
            }
        )
    for _, item in macro.head(12).iterrows():
        rows.append(
            {
                "timestamp": item.get("official_release_at") or item.get("observation_date"),
                "type": "Macro",
                "scope": item.get("indicator"),
                "event": f"{item.get('display_value')} for {item.get('observation_period')} ({item.get('display_change')} vs prior)",
                "impact": "Tightening" if (_number(item.get("change")) or 0) > 0 else "Easing",
                "transmission": "Rates / margins / growth expectations",
                "source": item.get("data_source"),
                "data_status": item.get("data_source"),
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["_sort"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        frame = frame.sort_values("_sort", ascending=False, na_position="last").drop(columns="_sort").reset_index(drop=True)
    return frame


def _intelligence_wire(frame: pd.DataFrame, limit: int = 35) -> str:
    if frame.empty:
        return '<div class="pt-muted">No intelligence observations available.</div>'
    rows = ['<div class="pt-wire pt-wire-head"><span>Time</span><span>Type</span><span>Event / Analyst Read</span><span>Impact</span><span>Transmission</span></div>']
    for _, row in frame.head(limit).iterrows():
        stamp = pd.to_datetime(row.get("timestamp"), errors="coerce")
        time_label = stamp.strftime("%m/%d %H:%M") if not pd.isna(stamp) else str(row.get("timestamp") or "N/A")[:12]
        impact = str(row.get("impact") or "Neutral")
        lower = impact.casefold()
        tone = "ok" if any(item in lower for item in ("bull", "positive", "easing")) else "bad" if any(item in lower for item in ("bear", "negative", "tightening")) else "warn"
        event = f"{row.get('scope')}: {row.get('event')}"
        rows.append(
            '<div class="pt-wire">'
            f'<span class="pt-mono pt-muted">{_html(time_label)}</span><span>{_badge(row.get("type"), "info")}</span>'
            f'<span><span class="pt-strong">{_html(event)}</span><br><span class="pt-muted">{_html(row.get("source"))}</span></span>'
            f'<span>{_badge(impact, tone)}</span><span class="pt-muted">{_html(row.get("transmission"))}</span></div>'
        )
    return "".join(rows)


@st.fragment(run_every="2min")
def _render_intelligence_feed() -> None:
    news = market_news()
    social = social_market()
    macro = macro_dashboard()
    frame = _intelligence_rows(news, social, macro)
    filter_cols = st.columns([1, 1, 1.4, 3])
    types = ["All"] + sorted(frame.get("type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    impacts = ["All"] + sorted(frame.get("impact", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    with filter_cols[0]:
        type_filter = st.selectbox("Event type", types, label_visibility="collapsed", key="intel_type")
    with filter_cols[1]:
        impact_filter = st.selectbox("Impact", impacts, label_visibility="collapsed", key="intel_impact")
    with filter_cols[2]:
        query = st.text_input("Search intelligence", placeholder="Ticker, theme, catalyst...", label_visibility="collapsed", key="intel_query")
    if type_filter != "All":
        frame = frame[frame["type"] == type_filter]
    if impact_filter != "All":
        frame = frame[frame["impact"] == impact_filter]
    if query:
        mask = frame.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        frame = frame[mask]
    meta = f"NEWS {classify_frame(news).upper()} / SOCIAL {classify_frame(social, 'source').upper()} / MACRO {classify_frame(macro).upper()}"
    st.markdown(_panel("Cross-Asset Catalyst Wire", _intelligence_wire(frame), meta), unsafe_allow_html=True)

    themes = social_themes()
    theme_rows = []
    for _, row in themes.head(8).iterrows():
        sentiment = _number(row.get("average_sentiment"))
        sentiment_cell = f'<td class="pt-mono {_tone(sentiment)}">{sentiment:+.0f}</td>' if sentiment is not None else '<td class="pt-mono">N/A</td>'
        theme_rows.append(
            "<tr>"
            f'<td class="pt-strong">{_html(row.get("theme"))}</td><td class="pt-mono">{_count(row.get("total_mentions"))}</td>'
            f'{sentiment_cell}'
        )
        theme_rows[-1] += f'<td>{_html(row.get("top_tickers"))}</td><td class="pt-muted">{_html(row.get("description"))}</td></tr>'
    theme_table = (
        '<table class="pt-table"><thead><tr><th>Theme</th><th>Mentions</th><th>Sentiment</th><th>Tickers</th><th>Investment read</th></tr></thead>'
        f'<tbody>{"".join(theme_rows)}</tbody></table>'
    ) if theme_rows else '<div class="pt-muted">Theme concentration unavailable.</div>'
    st.markdown(_panel("Narrative Map", theme_table, "SOCIAL ATTENTION + MARKET TRANSMISSION"), unsafe_allow_html=True)


def render_intelligence_page() -> None:
    render_page_header("INTL <GO>", "Intelligence", "One event stream for news, macro, positioning, and market transmission")
    render_market_tape(st.session_state.get("ticker", ""))
    _render_intelligence_feed()


def _scanner_frame(packet: dict, social: pd.DataFrame) -> pd.DataFrame:
    frame = packet.get("all_scanned", pd.DataFrame()).copy() if isinstance(packet, dict) else pd.DataFrame()
    if frame.empty:
        return frame
    if not social.empty and "Ticker" in frame and "ticker" in social:
        social_cols = [column for column in ("ticker", "mention_change_pct", "sentiment_label", "confidence_score", "theme") if column in social]
        frame = frame.merge(social[social_cols].drop_duplicates("ticker"), left_on="Ticker", right_on="ticker", how="left")
    return frame


def _scanner_table(frame: pd.DataFrame, limit: int = 40) -> str:
    if frame.empty:
        return '<div class="pt-muted">Scanner feed unavailable.</div>'
    rows = []
    for _, row in frame.head(limit).iterrows():
        move = _number(row.get("Daily Move %"))
        rel_volume = _number(row.get("Relative Volume"))
        social_velocity = _number(row.get("mention_change_pct"))
        signal = "Confirmed" if rel_volume and rel_volume >= 2 and move is not None and abs(move) >= 3 else "Monitor"
        if social_velocity and social_velocity >= 100 and (not rel_volume or rel_volume < 1.5):
            signal = "Attention / no volume"
        signal_tone = "ok" if signal == "Confirmed" else "warn"
        rows.append(
            "<tr>"
            f'<td class="pt-mono pt-strong">{_html(row.get("Ticker"))}</td><td>{_html(str(row.get("Company") or "")[:25])}</td>'
            f'<td class="pt-mono">{_money(row.get("Price"), 2)}</td><td class="pt-mono {_tone(move)}">{_pct(move, 2)}</td>'
            f'<td class="pt-mono">{_count(row.get("Volume"))}</td><td class="pt-mono">{_multiple(rel_volume)}</td>'
            f'<td>{_html(row.get("Sector") or row.get("theme") or "N/A")}</td><td class="pt-mono {_tone(social_velocity)}">{_pct(social_velocity, 0)}</td>'
            f'<td>{_badge(signal, signal_tone)}</td></tr>'
        )
    return (
        '<table class="pt-table"><thead><tr><th>Ticker</th><th>Company</th><th>Last</th><th>Move</th><th>Volume</th>'
        f'<th>Rel Vol</th><th>Sector / Theme</th><th>Social 24H</th><th>Analyst Read</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


@st.fragment(run_every="60s")
def _render_screener() -> None:
    packet = movers_packet()
    social = social_market()
    frame = _scanner_frame(packet, social)
    controls = st.columns([1, 1, 1, 1, 2])
    with controls[0]:
        min_move = st.number_input("Min abs move %", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
    with controls[1]:
        min_rel = st.number_input("Min rel volume", min_value=0.0, max_value=20.0, value=1.2, step=0.2)
    with controls[2]:
        direction = st.selectbox("Direction", ["Both", "Gainers", "Losers"])
    sectors = ["All"] + sorted(frame.get("Sector", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()) if not frame.empty else ["All"]
    with controls[3]:
        sector = st.selectbox("Sector", sectors)
    with controls[4]:
        query = st.text_input("Ticker or company", placeholder="Search ticker or company")
    if not frame.empty:
        move_series = pd.to_numeric(frame.get("Daily Move %"), errors="coerce")
        rel_series = pd.to_numeric(frame.get("Relative Volume"), errors="coerce")
        frame = frame[(move_series.abs() >= min_move) & (rel_series >= min_rel)]
        if direction == "Gainers":
            frame = frame[pd.to_numeric(frame["Daily Move %"], errors="coerce") > 0]
        elif direction == "Losers":
            frame = frame[pd.to_numeric(frame["Daily Move %"], errors="coerce") < 0]
        if sector != "All":
            frame = frame[frame["Sector"] == sector]
        if query:
            mask = frame[[column for column in ("Ticker", "Company") if column in frame]].astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
            frame = frame[mask]
        frame = frame.assign(_rank=pd.to_numeric(frame["Relative Volume"], errors="coerce") * pd.to_numeric(frame["Daily Move %"], errors="coerce").abs()).sort_values("_rank", ascending=False)
    source_status = packet.get("source_status", {}) if isinstance(packet, dict) else {}
    meta = f"{len(frame)} MATCHES / {source_status.get('status', 'UNAVAILABLE')} / 60S"
    st.markdown(_panel("Price / Volume Dislocation Scanner", _scanner_table(frame), meta), unsafe_allow_html=True)


def render_screener_page() -> None:
    render_page_header("SCR <GO>", "Screener", "Liquidity-first discovery with price, volume, and social confirmation")
    render_market_tape(st.session_state.get("ticker", ""))
    _render_screener()


def _watchlist_quotes() -> tuple[pd.DataFrame, pd.DataFrame]:
    watch = list_watchlist()
    symbols = watch.get("ticker", pd.Series(dtype=str)).astype(str).tolist() if not watch.empty else []
    quotes = market_quotes("")
    quotes = quotes[quotes["ticker"].isin(symbols)].copy() if not quotes.empty else quotes
    return watch, quotes


def _watchlist_table(watch: pd.DataFrame, quotes: pd.DataFrame) -> str:
    if watch.empty:
        return '<div class="pt-muted">Watchlist is empty.</div>'
    quote_map = {str(row.get("ticker")): row for _, row in quotes.iterrows()}
    rows = []
    for _, item in watch.iterrows():
        symbol = str(item.get("ticker"))
        quote = quote_map.get(symbol, {})
        rows.append(
            "<tr>"
            f'<td class="pt-mono pt-strong">{_html(symbol)}</td><td class="pt-mono">{_money(quote.get("price"), 2)}</td>'
            f'<td class="pt-mono {_tone(quote.get("change_pct"))}">{_pct(quote.get("change_pct"), 2)}</td>'
            f'<td>{_html(item.get("category") or "Research")}</td><td class="pt-muted">{_html(item.get("notes") or "")}</td>'
            f'<td>{_badge(quote.get("status") or "Unavailable", status_tone(str(quote.get("status") or "")))}</td></tr>'
        )
    return (
        '<table class="pt-table"><thead><tr><th>Ticker</th><th>Last</th><th>Day</th><th>Book</th><th>Notes</th><th>Feed</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _position_metrics(frame: pd.DataFrame, quotes: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str, str, str]]]:
    positions = frame.copy()
    quote_map = {str(row.get("ticker")): _number(row.get("price")) for _, row in quotes.iterrows()}
    positions["Last"] = positions["Ticker"].map(quote_map)
    positions["Market Value"] = pd.to_numeric(positions["Quantity"], errors="coerce").fillna(0) * pd.to_numeric(positions["Last"], errors="coerce").fillna(0)
    positions["Cost Basis"] = pd.to_numeric(positions["Quantity"], errors="coerce").fillna(0) * pd.to_numeric(positions["Average Cost"], errors="coerce").fillna(0)
    positions["P&L"] = positions["Market Value"] - positions["Cost Basis"]
    total_value = float(positions["Market Value"].sum())
    total_cost = float(positions["Cost Basis"].sum())
    pnl = total_value - total_cost
    concentration = float(positions["Market Value"].max() / total_value * 100) if total_value > 0 and not positions.empty else 0
    invested = positions[positions["Quantity"] > 0]
    metrics = [
        ("Gross Exposure", _money(total_value), f"{len(invested)} active positions", ""),
        ("Unrealized P&L", _money(pnl), _pct((pnl / total_cost * 100) if total_cost else None, 1), _tone(pnl)),
        ("Largest Position", f"{concentration:.1f}%", "Concentration checkpoint", "pt-warn" if concentration > 25 else "pt-up"),
        ("Watchlist", str(len(positions)), "Tracked securities", ""),
    ]
    return positions, metrics


@st.fragment(run_every="10s")
def _render_portfolio_monitor() -> None:
    watch, quotes = _watchlist_quotes()
    symbols = watch.get("ticker", pd.Series(dtype=str)).astype(str).tolist() if not watch.empty else []
    if "portfolio_positions" not in st.session_state:
        st.session_state.portfolio_positions = pd.DataFrame({"Ticker": symbols, "Quantity": [0.0] * len(symbols), "Average Cost": [0.0] * len(symbols)})
    positions = st.session_state.portfolio_positions.copy()
    for symbol in symbols:
        if symbol not in positions.get("Ticker", pd.Series(dtype=str)).astype(str).tolist():
            positions = pd.concat([positions, pd.DataFrame([{"Ticker": symbol, "Quantity": 0.0, "Average Cost": 0.0}])], ignore_index=True)
    positions = positions[positions["Ticker"].isin(symbols)].reset_index(drop=True)
    calculated, metrics = _position_metrics(positions, quotes)
    st.markdown(_kpi_grid(metrics), unsafe_allow_html=True)
    left, right = st.columns([1.45, 0.8])
    with left:
        st.markdown(_panel("Live Watchlist", _watchlist_table(watch, quotes), "10S QUOTE LOOP"), unsafe_allow_html=True)
    with right:
        st.markdown(_panel("Risk Summary", (
            '<div class="pt-brief"><strong>Concentration:</strong> position weights above 25% should be treated as thesis-level risks.<br><br>'
            '<strong>Integrity:</strong> missing quote rows are excluded from market value rather than imputed.<br><br>'
            '<strong>Next step:</strong> connect a broker or custodial export for authoritative tax lots and cash.</div>'
        ), "PRE-TRADE CONTROL"), unsafe_allow_html=True)
    st.markdown('<div class="pt-section-head"><span class="pt-section-title">Position Inputs</span><span class="pt-section-meta">SESSION WORKSPACE</span></div>', unsafe_allow_html=True)
    edited = st.data_editor(
        positions,
        hide_index=True,
        use_container_width=True,
        disabled=["Ticker"],
        column_config={
            "Ticker": st.column_config.TextColumn(width="small"),
            "Quantity": st.column_config.NumberColumn(min_value=0.0, step=1.0),
            "Average Cost": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="$%.2f"),
        },
        key="position_editor",
    )
    st.session_state.portfolio_positions = edited
    display = calculated[["Ticker", "Quantity", "Average Cost", "Last", "Market Value", "P&L"]].copy()
    st.dataframe(display, hide_index=True, use_container_width=True)


def render_portfolio_page() -> None:
    render_page_header("PORT <GO>", "Portfolio", "Watchlist, position exposure, P&L, concentration, and alerts")
    render_market_tape(st.session_state.get("ticker", ""))
    action_cols = st.columns([1.2, 0.5, 1.2, 0.5, 3])
    with action_cols[0]:
        add_symbol = st.text_input("Add ticker", placeholder="Ticker", label_visibility="collapsed", key="portfolio_add")
    with action_cols[1]:
        if st.button("Add", use_container_width=True, key="portfolio_add_btn") and add_symbol:
            if add_ticker(add_symbol, category="Portfolio"):
                st.success(f"Added {clean_ticker(add_symbol)}")
                st.rerun()
            else:
                st.error("Ticker could not be validated.")
    with action_cols[2]:
        watch = list_watchlist()
        options = watch.get("ticker", pd.Series(dtype=str)).astype(str).tolist() if not watch.empty else []
        remove_symbol = st.selectbox("Remove ticker", options or [""], label_visibility="collapsed", key="portfolio_remove")
    with action_cols[3]:
        if st.button("Remove", use_container_width=True, key="portfolio_remove_btn") and remove_symbol:
            remove_ticker(remove_symbol)
            st.rerun()
    _render_portfolio_monitor()
    alerts = list_alerts()
    if not alerts.empty:
        st.markdown(_panel("Research Alerts", alerts.head(12).to_html(index=False, escape=True, classes="pt-table", border=0), "MATERIAL CHANGES"), unsafe_allow_html=True)


def _integrity_table(frame: pd.DataFrame) -> str:
    rows = ['<div class="pt-integrity head"><span>Domain</span><span>Feed / Provider</span><span>Status</span><span>Cadence</span><span>Configured</span></div>']
    for _, row in frame.iterrows():
        status = str(row.get("status") or "Unavailable")
        source = f"{row.get('feed')} / {row.get('primary')}"
        rows.append(
            '<div class="pt-integrity">'
            f'<span class="pt-strong">{_html(row.get("domain"))}</span><span>{_html(source)}<br><span class="pt-muted">Fallback: {_html(row.get("fallback"))}</span></span>'
            f'<span>{_badge(status, status_tone(status))}</span><span class="pt-mono">{int(row.get("refresh_seconds") or 0)}s</span>'
            f'<span class="pt-mono">{"YES" if row.get("configured") else "NO"}</span></div>'
        )
    return "".join(rows)


def render_data_page() -> None:
    render_page_header("DATA <GO>", "Data Integrity", "Provider health, freshness contracts, fallbacks, and audit controls")
    render_market_tape(st.session_state.get("ticker", ""))
    health = provider_health()
    live_count = int(health["status"].astype(str).str.contains("Live|Official|Authoritative", case=False, regex=True).sum())
    demo_count = int((health["status"] == "Demo").sum())
    delayed_count = int(health["status"].astype(str).str.contains("Delayed|Mixed|Partial|mirror", case=False, regex=True).sum())
    st.markdown(
        _kpi_grid(
            [
                ("Data Contracts", str(len(health)), "Monitored feeds", ""),
                ("Official / Live", str(live_count), "Configured or public official", "pt-up"),
                ("Delayed / Partial", str(delayed_count), "Visible fallback state", "pt-warn"),
                ("Demo", str(demo_count), "Never labeled live", "pt-down" if demo_count else "pt-up"),
            ]
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_panel("Provider Registry", _integrity_table(health), "SECRETS MASKED"), unsafe_allow_html=True)

    macro = macro_dashboard()
    macro_audit = audit_macro_dashboard(macro)
    verified = int((macro_audit["audit_status"] == "VERIFIED").sum()) if not macro_audit.empty else 0
    blocked = int((macro_audit["audit_status"] == "BLOCKED").sum()) if not macro_audit.empty else 0
    notification = macro_notification_status()
    cadence = macro_poll_interval_seconds()
    cadence_note = (
        f"Next check in {cadence}s; release cadence is active."
        if cadence <= 300
        else "Background checks remain armed and wake five minutes before the next official release."
    )
    alert_mode = "In-app + webhook" if notification.get("webhook_configured") else "In-app"
    st.markdown(
        _panel(
            "Macro Data Audit",
            _macro_audit_table(macro_audit),
            f"{verified} VERIFIED / {blocked} BLOCKED / RELEASE-AWARE",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pt-grid-3">'
        f'<div class="pt-stat green"><div class="pt-stat-label">Release Monitor</div><div class="pt-stat-value">Active</div><div class="pt-stat-note">{_html(cadence_note)}</div></div>'
        f'<div class="pt-stat blue"><div class="pt-stat-label">Alert Delivery</div><div class="pt-stat-value">{_html(alert_mode)}</div><div class="pt-stat-note">Webhook delivery activates when MACRO_ALERT_WEBHOOK_URL is configured.</div></div>'
        '<div class="pt-stat amber"><div class="pt-stat-label">Embargo Guard</div><div class="pt-stat-value">Enforced</div><div class="pt-stat-note">Scheduled releases remain upcoming until the official observation period changes.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    macro_alerts = list_macro_alerts(limit=12)
    if not macro_alerts.empty:
        display_alerts = macro_alerts[["detected_at", "indicator", "observation_period", "alert_message", "delivery_status"]].copy()
        display_alerts.columns = ["Detected", "Series", "Period", "Alert", "Delivery"]
        st.markdown(_panel("Macro Release Alerts", display_alerts.to_html(index=False, escape=True, classes="pt-table", border=0), "DEDUPLICATED"), unsafe_allow_html=True)

    policy = (
        '<div class="pt-grid-3">'
        '<div class="pt-stat green"><div class="pt-stat-label">Financial Data</div><div class="pt-stat-value">Filed facts first</div><div class="pt-stat-note">SEC companyfacts anchors reported metrics. Estimates remain separately labeled and fiscal periods are reconciled.</div></div>'
        '<div class="pt-stat amber"><div class="pt-stat-label">Social Data</div><div class="pt-stat-value">Attention, not truth</div><div class="pt-stat-note">Minimum samples, cross-source diversity, catalyst confirmation, and pump-risk penalties govern signal quality.</div></div>'
        '<div class="pt-stat blue"><div class="pt-stat-label">Economic Data</div><div class="pt-stat-value">Vintage aware</div><div class="pt-stat-note">Release dates and revisions are retained so latest values are not mistaken for what the market knew historically.</div></div>'
        '</div>'
    )
    st.markdown(_panel("Integrity Policy", policy, "NO SILENT IMPUTATION"), unsafe_allow_html=True)

    refresh_rows = (
        '<table class="pt-table"><thead><tr><th>Domain</th><th>Refresh loop</th><th>Why</th><th>Failure behavior</th></tr></thead><tbody>'
        '<tr><td>Quotes</td><td class="pt-mono">10 seconds</td><td>Price, spread, and session monitoring</td><td>Retain row, mark unavailable, never invent price</td></tr>'
        '<tr><td>Market scan</td><td class="pt-mono">60 seconds</td><td>Price and volume dislocations</td><td>Show scan universe and fallback status</td></tr>'
        '<tr><td>News</td><td class="pt-mono">120 seconds</td><td>Catalyst discovery</td><td>Label demo fallback when provider is absent</td></tr>'
        '<tr><td>Social</td><td class="pt-mono">300 seconds</td><td>Attention velocity and narrative shifts</td><td>Demo label or no reliable data</td></tr>'
        f'<tr><td>Macro</td><td class="pt-mono">{cadence}s release-aware</td><td>Accelerates around official scheduled times</td><td>Use last verified snapshot with REVIEW; never synthesize a value</td></tr>'
        '<tr><td>Filings</td><td class="pt-mono">Daily + event refresh</td><td>Authoritative reported fundamentals</td><td>Keep missing concepts explicit</td></tr>'
        '</tbody></table>'
    )
    st.markdown(_panel("Refresh Architecture", refresh_rows, "INDEPENDENT FRAGMENTS"), unsafe_allow_html=True)

    with st.expander("Credential names and connector requirements", expanded=False):
        credentials = health[["domain", "feed", "credential_names", "integrity_rule"]].copy()
        credentials["credential_names"] = credentials["credential_names"].apply(lambda values: ", ".join(values) if values else "Public endpoint / no key")
        st.dataframe(credentials, hide_index=True, use_container_width=True)
