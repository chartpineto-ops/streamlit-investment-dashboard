from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.refresh_status import mark_fragment_refresh
from services.social_sentiment_service import (
    SOCIAL_WARNING,
    fetch_social_momentum,
    fetch_social_sentiment_leaders,
    fetch_social_theme_trends,
    fetch_social_trending_tickers,
)
from utils.formatting import fmt_compact, fmt_daily_move, fmt_percent, now_et, to_float
from utils.refresh_debug import is_refresh_stale, log_refresh, render_refresh_debug
from utils.rendering import render_html


def _tone(value: object) -> str:
    number = to_float(value) or 0.0
    return "good" if number > 0 else "bad" if number < 0 else "neutral"


def _badge(value: object) -> str:
    text = str(value or "Neutral")
    lowered = text.casefold()
    tone = "good" if "bull" in lowered or "confirmed" in lowered else "bad" if "bear" in lowered or "pump" in lowered else "warn" if "mixed" in lowered or "spike" in lowered else "neutral"
    return f'<span class="pt-social-badge {tone}">{escape(text)}</span>'


def _metric_cards(frame: pd.DataFrame, leaders: pd.DataFrame) -> str:
    if frame is None or frame.empty:
        cards = [
            ("Tracked mentions", "N/A"),
            ("Attention leader", "N/A"),
            ("Fastest riser", "N/A"),
            ("Crowding flags", "N/A"),
        ]
    else:
        top = frame.sort_values("mention_count", ascending=False).iloc[0]
        fastest = frame.sort_values("mention_change_pct", ascending=False).iloc[0]
        crowding_flags = int(frame["signal_label"].astype(str).str.contains("Pump|Squeeze", case=False, regex=True).sum()) if "signal_label" in frame else 0
        cards = [
            ("Tracked mentions", fmt_compact(frame["mention_count"].sum(), 1)),
            ("Attention leader", str(top.get("ticker") or "N/A")),
            ("Fastest riser", f"{fastest.get('ticker')} {fmt_percent(fastest.get('mention_change_pct'), 0, True)}"),
            ("Crowding flags", str(crowding_flags)),
        ]
    return '<div class="pt-social-metric-grid">' + "".join(
        f'<div class="pt-row-card"><span class="pt-mini-label">{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in cards
    ) + "</div>"


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], limit: int = 10) -> str:
    if frame is None or frame.empty:
        return '<p class="pt-placeholder">No reliable social data available.</p>'
    header = "".join(f"<th>{escape(label)}</th>" for label, _ in columns)
    rows = ""
    for rank, (_, row) in enumerate(frame.head(limit).iterrows(), start=1):
        cells = ""
        for _, key in columns:
            value = row.get(key)
            if key == "rank":
                rendered = str(rank)
            elif key in {"mention_count", "bullish_count", "bearish_count", "total_mentions"}:
                rendered = fmt_compact(value, 1)
            elif key in {"mention_change_pct", "price_change_pct", "volume_change_pct", "sentiment_score", "average_sentiment", "average_price_move"}:
                rendered = f'<span class="{_tone(value)}">{fmt_percent(value, 0 if key != "price_change_pct" else 2, True)}</span>'
            elif key in {"sentiment_label", "signal_label"}:
                rendered = _badge(value)
            elif key == "confidence_score":
                rendered = f"{to_float(value) or 0:.0f}/100"
            elif key == "social_momentum_score":
                rendered = f"{to_float(value) or 0:.0f}/100"
            else:
                rendered = escape(str(value if value not in (None, "") else "N/A"))
            cells += f"<td>{rendered}</td>"
        rows += f"<tr>{cells}</tr>"
    return f'<div class="pt-social-table-wrap"><table class="pt-social-table pt-social-market-table"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'


def _sentiment_leaders(leaders: pd.DataFrame) -> pd.DataFrame:
    if leaders is None or leaders.empty:
        return pd.DataFrame()
    bullish = leaders.sort_values(["sentiment_score", "mention_count"], ascending=False).head(5).copy()
    bullish["leader_type"] = "Bullish"
    bearish = leaders.sort_values(["sentiment_score", "mention_count"], ascending=[True, False]).head(5).copy()
    bearish["leader_type"] = "Bearish"
    combined = pd.concat([bullish, bearish], ignore_index=True)
    combined["sentiment_label"] = combined["leader_type"]
    return combined


def _divergence_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    rows = []
    for _, row in frame.iterrows():
        mention_change = to_float(row.get("mention_change_pct")) or 0
        sentiment = to_float(row.get("sentiment_score")) or 0
        price_move = to_float(row.get("price_change_pct")) or 0
        volume_move = to_float(row.get("volume_change_pct")) or 0
        signal = ""
        interpretation = ""
        if mention_change > 45 and price_move <= 0:
            signal = "Attention rising, price lagging"
            interpretation = "Social attention is building before price confirmation."
        elif price_move > 3 and mention_change < 15:
            signal = "Price rising, social quiet"
            interpretation = "Price strength is not yet crowded on social channels."
        elif sentiment < -18 and price_move > 0:
            signal = "Bearish chatter into strength"
            interpretation = "Price is holding despite rising bearish pressure."
        elif sentiment > 18 and price_move < -2:
            signal = "Bullish after selloff"
            interpretation = "Retail tone is improving after recent price weakness."
        if signal:
            rows.append({**row.to_dict(), "social_signal": signal, "interpretation": interpretation})
    return pd.DataFrame(rows).sort_values(["mention_change_pct", "volume_change_pct"], ascending=False).head(12).reset_index(drop=True) if rows else pd.DataFrame()


def _render_social_momentum_ui(frame: pd.DataFrame, trending: pd.DataFrame, leaders: pd.DataFrame, themes: pd.DataFrame) -> None:
    status = frame.attrs.get("status", {}) if isinstance(frame, pd.DataFrame) else {}
    status_label = str(status.get("Status") or "Unavailable")
    source = str(status.get("Source") or "Social providers")
    if frame is None or frame.empty:
        warning = '<p class="pt-placeholder">No reliable social data available until a provider is configured or reconnects.</p>'
    elif "provider not configured" in source.casefold() or "demo" in source.casefold():
        warning = '<p class="pt-placeholder">Provider not configured. Showing clearly labelled fallback social data until a social API key is configured.</p>'
    else:
        warning = ""
    header = f"""
    <div class="pt-social-section-head">
      <div>
        <strong>Retail Attention Radar</strong>
        <p>Social chatter translated into attention, perception, market confirmation, and crowding risk.</p>
      </div>
      <div class="pt-social-source">
        <b>{escape(status_label)}</b>
        <span>{escape(source)}</span>
        <em title="{escape(SOCIAL_WARNING)}">Not a standalone thesis</em>
      </div>
    </div>
    {warning}
    {_metric_cards(frame, leaders)}
    """
    render_html(f'<div class="pt-shell pt-social-market-shell">{header}</div>')

    render_html("<h3 class='pt-social-subhead'>Attention Tape</h3>")
    attention = trending.sort_values(["mention_count", "mention_change_pct"], ascending=False) if trending is not None and not trending.empty else pd.DataFrame()
    render_html(
        _table(
            attention,
            [
                ("Rank", "rank"),
                ("Ticker", "ticker"),
                ("Company", "company_name"),
                ("Mentions", "mention_count"),
                ("24h Delta", "mention_change_pct"),
                ("Perception", "sentiment_label"),
                ("Price", "price_change_pct"),
                ("Volume Delta", "volume_change_pct"),
                ("Score", "social_momentum_score"),
                ("Research Signal", "signal_label"),
            ],
            12,
        )
    )

    theme_col, divergence_col = st.columns([0.52, 0.48], gap="small")
    with theme_col:
        render_html("<h3 class='pt-social-subhead'>Narrative Tape</h3>")
        render_html(
            _table(
                themes,
                [("Theme", "theme"), ("Top Symbols", "top_tickers"), ("Mentions", "total_mentions"), ("Sentiment", "average_sentiment"), ("Price", "average_price_move")],
                6,
            )
        )
    with divergence_col:
        render_html("<h3 class='pt-social-subhead'>Perception / Price Divergence</h3>")
        render_html(
            _table(
                _divergence_frame(frame),
                [("Ticker", "ticker"), ("Read", "social_signal"), ("24h Delta", "mention_change_pct"), ("Perception", "sentiment_label"), ("Price", "price_change_pct"), ("Why It Matters", "interpretation")],
                6,
            )
        )


@st.fragment(run_every="5min")
def _social_momentum_fragment() -> None:
    try:
        frame = fetch_social_momentum()
        trending = fetch_social_trending_tickers()
        leaders = fetch_social_sentiment_leaders()
        themes = fetch_social_theme_trends()
        source = str(frame.attrs.get("status", {}).get("Source") or "Social provider") if isinstance(frame, pd.DataFrame) else "Social provider"
        status = frame.attrs.get("status", {}) if isinstance(frame, pd.DataFrame) else {}
        last_refresh = status.get("Last Updated") or (frame["last_updated"].iloc[0] if isinstance(frame, pd.DataFrame) and not frame.empty and "last_updated" in frame else now_et())
        stale = is_refresh_stale(last_refresh, 300)
        refresh_status = "Fallback" if "provider not configured" in source.casefold() or "demo" in source.casefold() else "OK"
        log_refresh("social", source)
        mark_fragment_refresh("social", 300, refresh_status, source, last_refresh=last_refresh, data_source=source, cache_ttl=300, rows=0 if frame is None else len(frame), is_stale=stale)
        _render_social_momentum_ui(frame, trending, leaders, themes)
        render_refresh_debug("social", last_refresh=last_refresh, data_source=source, cache_ttl=300, rows=0 if frame is None else len(frame), is_stale=stale)
    except Exception as exc:
        error = str(exc)[:180]
        mark_fragment_refresh("social", 300, "Error", error, last_refresh=now_et(), data_source="Social provider", cache_ttl=300, rows=0, is_stale=True, error=error)
        render_html(
            f"""
            <div class="pt-shell">
              <div class="pt-social-section-head"><div><strong>Retail Attention Radar</strong><p>Attention, perception, confirmation, and crowding risk.</p></div></div>
              <p class="pt-placeholder">Retail Attention Radar is temporarily unavailable: {escape(str(exc)[:180])}</p>
            </div>
            """
        )
        render_refresh_debug("social", last_refresh=now_et(), data_source="Social provider", cache_ttl=300, rows=0, is_stale=True, error=error)


def render_social_momentum_panel() -> None:
    _social_momentum_fragment()
