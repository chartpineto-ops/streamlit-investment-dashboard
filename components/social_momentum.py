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
            ("Total tracked mentions", "N/A"),
            ("Top trending ticker", "N/A"),
            ("Fastest rising ticker", "N/A"),
            ("Most bullish ticker", "N/A"),
            ("Most bearish ticker", "N/A"),
        ]
    else:
        top = frame.sort_values("mention_count", ascending=False).iloc[0]
        fastest = frame.sort_values("mention_change_pct", ascending=False).iloc[0]
        bullish = frame.sort_values("sentiment_score", ascending=False).iloc[0]
        bearish = frame.sort_values("sentiment_score", ascending=True).iloc[0]
        cards = [
            ("Total tracked mentions", fmt_compact(frame["mention_count"].sum(), 1)),
            ("Top trending ticker", str(top.get("ticker") or "N/A")),
            ("Fastest rising ticker", f"{fastest.get('ticker')} {fmt_percent(fastest.get('mention_change_pct'), 0, True)}"),
            ("Most bullish ticker", f"{bullish.get('ticker')} {fmt_percent(bullish.get('sentiment_score'), 0, True)}"),
            ("Most bearish ticker", f"{bearish.get('ticker')} {fmt_percent(bearish.get('sentiment_score'), 0, True)}"),
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
            elif key == "sentiment_label":
                rendered = _badge(value)
            elif key == "confidence_score":
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


def _theme_cards(themes: pd.DataFrame) -> str:
    if themes is None or themes.empty:
        return '<p class="pt-placeholder">No theme trends available.</p>'
    cards = ""
    for _, row in themes.head(8).iterrows():
        cards += f"""
        <div class="pt-social-theme-card">
          <strong>{escape(str(row.get("theme") or "Theme"))}</strong>
          <span>{escape(str(row.get("top_tickers") or "N/A"))}</span>
          <p>{escape(str(row.get("description") or ""))}</p>
          <em>{fmt_compact(row.get("total_mentions"), 1)} mentions | Sentiment {fmt_percent(row.get("average_sentiment"), 0, True)} | Price {fmt_daily_move(row.get("average_price_move"))}</em>
        </div>
        """
    return f'<div class="pt-social-theme-grid">{cards}</div>'


def _render_social_momentum_ui(frame: pd.DataFrame, trending: pd.DataFrame, leaders: pd.DataFrame, themes: pd.DataFrame) -> None:
    status = frame.attrs.get("status", {}) if isinstance(frame, pd.DataFrame) else {}
    status_label = str(status.get("Status") or "Unavailable")
    source = str(status.get("Source") or "Social providers")
    warning = "" if frame is not None and not frame.empty else '<p class="pt-placeholder">Social data is unavailable. Showing no market-wide social signals until the provider reconnects.</p>'
    header = f"""
    <div class="pt-social-section-head">
      <div>
        <strong>Social Momentum</strong>
        <p>Track the tickers, sectors, and themes gaining attention across social platforms.</p>
      </div>
      <div class="pt-social-source">
        <b>{escape(status_label)}</b>
        <span>{escape(source)}</span>
        <em title="{escape(SOCIAL_WARNING)}">Attention signal</em>
      </div>
    </div>
    {warning}
    {_metric_cards(frame, leaders)}
    """
    render_html(f'<div class="pt-shell pt-social-market-shell">{header}</div>')

    col1, col2 = st.columns(2)
    with col1:
        render_html("<h3 class='pt-social-subhead'>Most Mentioned Tickers</h3>")
        render_html(
            _table(
                trending.sort_values("mention_count", ascending=False) if trending is not None and not trending.empty else pd.DataFrame(),
                [("Rank", "rank"), ("Ticker", "ticker"), ("Company", "company_name"), ("Mentions", "mention_count"), ("Mention Change", "mention_change_pct"), ("Sentiment", "sentiment_label"), ("Price Move", "price_change_pct")],
                12,
            )
        )
    with col2:
        render_html("<h3 class='pt-social-subhead'>Fastest Rising Tickers</h3>")
        render_html(
            _table(
                frame.sort_values("mention_change_pct", ascending=False) if frame is not None and not frame.empty else pd.DataFrame(),
                [("Rank", "rank"), ("Ticker", "ticker"), ("Acceleration", "mention_change_pct"), ("Price Move", "price_change_pct"), ("Volume Move", "volume_change_pct"), ("Sentiment", "sentiment_score"), ("Confidence", "confidence_score")],
                12,
            )
        )

    col3, col4 = st.columns(2)
    with col3:
        render_html("<h3 class='pt-social-subhead'>Bullish / Bearish Sentiment Leaders</h3>")
        render_html(
            _table(
                _sentiment_leaders(leaders),
                [("Rank", "rank"), ("Side", "leader_type"), ("Ticker", "ticker"), ("Mentions", "mention_count"), ("Sentiment Score", "sentiment_score"), ("Price Move", "price_change_pct"), ("Confidence", "confidence_score")],
                10,
            )
        )
    with col4:
        render_html("<h3 class='pt-social-subhead'>Social + Price Divergence</h3>")
        render_html(
            _table(
                _divergence_frame(frame),
                [("Ticker", "ticker"), ("Social Signal", "social_signal"), ("Mention Change", "mention_change_pct"), ("Sentiment", "sentiment_label"), ("Price Move", "price_change_pct"), ("Volume Move", "volume_change_pct"), ("Interpretation", "interpretation")],
                10,
            )
        )

    render_html("<h3 class='pt-social-subhead'>Trending Themes</h3>")
    render_html(_theme_cards(themes))


@st.fragment(run_every="5min")
def _social_momentum_fragment() -> None:
    try:
        frame = fetch_social_momentum()
        trending = fetch_social_trending_tickers()
        leaders = fetch_social_sentiment_leaders()
        themes = fetch_social_theme_trends()
        source = str(frame.attrs.get("status", {}).get("Source") or "Social provider") if isinstance(frame, pd.DataFrame) else "Social provider"
        mark_fragment_refresh("social", 300, "OK", source)
        _render_social_momentum_ui(frame, trending, leaders, themes)
    except Exception as exc:
        mark_fragment_refresh("social", 300, "Error", str(exc)[:180])
        render_html(
            f"""
            <div class="pt-shell">
              <div class="pt-social-section-head"><div><strong>Social Momentum</strong><p>Track the tickers, sectors, and themes gaining attention across social platforms.</p></div></div>
              <p class="pt-placeholder">Social Momentum is temporarily unavailable: {escape(str(exc)[:180])}</p>
            </div>
            """
        )


def render_social_momentum_panel() -> None:
    _social_momentum_fragment()
