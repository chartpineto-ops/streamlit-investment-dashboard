from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from data.market_data import DEFAULT_TICKERS, fetch_quote
from signals.signal_engine import compute_signal
from storage.db import connect, init_db
from utils.formatting import clean_ticker, fmt_compact, fmt_date, fmt_percent, fmt_price, now_et, to_float


def fmt_daily_move(value) -> str:
    return fmt_percent(value, decimals=2, signed=True)


def ensure_default_watchlist() -> None:
    init_db()
    with connect() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM watchlist").fetchone()["count"]
        if existing:
            return
        timestamp = now_et().isoformat()
        conn.executemany(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at, category, notes) VALUES (?, ?, ?, ?)",
            [(ticker, timestamp, "Default", "") for ticker in DEFAULT_TICKERS],
        )
        conn.commit()


def _quote_status(quote: dict) -> str:
    if quote.get("status") == "Error":
        return "Quote unavailable"
    if quote.get("price") is None and quote.get("volume") is None and str(quote.get("company_name") or "").upper() == str(quote.get("ticker") or "").upper():
        return "Invalid ticker"
    if quote.get("price") is None:
        return "Quote unavailable"
    return "OK"


def save_quote_snapshot(ticker: str, quote: dict | None = None) -> dict:
    symbol = clean_ticker(ticker)
    quote = quote or fetch_quote(symbol)
    status = _quote_status(quote)
    snapshot = {
        "ticker": symbol,
        "timestamp": now_et().isoformat(),
        "company": quote.get("company_name") or symbol,
        "price": to_float(quote.get("price")),
        "daily_move_pct": to_float(quote.get("daily_change_pct")),
        "volume": to_float(quote.get("volume")),
        "market_cap": to_float(quote.get("market_cap")),
        "source": quote.get("source", "Yahoo Finance/yfinance"),
        "status": status,
    }
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO quote_snapshot (
                ticker, timestamp, company, price, daily_move_pct, volume, market_cap, source, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["ticker"],
                snapshot["timestamp"],
                snapshot["company"],
                snapshot["price"],
                snapshot["daily_move_pct"],
                snapshot["volume"],
                snapshot["market_cap"],
                snapshot["source"],
                snapshot["status"],
            ),
        )
        conn.commit()
    return snapshot


def latest_quote_snapshot(ticker: str) -> dict | None:
    symbol = clean_ticker(ticker)
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM quote_snapshot WHERE ticker = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (symbol,),
        ).fetchone()
    return dict(row) if row else None


def add_ticker(ticker: str, category: str = "", notes: str = "") -> bool:
    symbol = clean_ticker(ticker)
    if not symbol:
        return False
    quote = fetch_quote(symbol)
    if _quote_status(quote) == "Invalid ticker":
        return False
    init_db()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at, category, notes) VALUES (?, ?, ?, ?)",
            (symbol, now_et().isoformat(), category, notes),
        )
        conn.commit()
    save_quote_snapshot(symbol, quote)
    return True


def remove_ticker(ticker: str) -> None:
    symbol = clean_ticker(ticker)
    if not symbol:
        return
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (symbol,))
        conn.commit()


def list_watchlist() -> pd.DataFrame:
    ensure_default_watchlist()
    with connect() as conn:
        rows = conn.execute("SELECT ticker, added_at, category, notes FROM watchlist ORDER BY ticker").fetchall()
    return pd.DataFrame([dict(row) for row in rows])


def latest_signal(ticker: str) -> dict | None:
    symbol = clean_ticker(ticker)
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM signal_history WHERE ticker = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (symbol,),
        ).fetchone()
    return dict(row) if row else None


def _insert_alert(ticker: str, alert_type: str, old_value, new_value, message: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO alerts (ticker, timestamp, alert_type, old_value, new_value, alert_message, dismissed) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (ticker, now_et().isoformat(), alert_type, str(old_value), str(new_value), message),
        )
        conn.commit()


def _material_change_alerts(ticker: str, prior: dict | None, current: dict) -> str:
    if prior is None:
        return "Initial signal recorded."
    messages: list[str] = []
    old_label = prior.get("signal_label")
    new_label = current.get("signal_label")
    if old_label != new_label:
        message = f"{ticker} signal changed from {old_label} to {new_label}."
        _insert_alert(ticker, "Signal Change", old_label, new_label, message)
        messages.append(message)
    old_score = prior.get("composite_score")
    new_score = current.get("composite_score")
    try:
        delta = float(new_score) - float(old_score)
    except Exception:
        delta = 0
    if abs(delta) >= 5:
        message = f"{ticker} score {'increased' if delta > 0 else 'decreased'} from {old_score:.1f} to {new_score:.1f}."
        _insert_alert(ticker, "Score Change", old_score, new_score, message)
        messages.append(message)
    if prior.get("confidence") != current.get("confidence"):
        message = f"{ticker} confidence changed from {prior.get('confidence')} to {current.get('confidence')}."
        _insert_alert(ticker, "Confidence Change", prior.get("confidence"), current.get("confidence"), message)
        messages.append(message)
    if old_score is not None and new_score is not None:
        if float(old_score) < 65 <= float(new_score):
            message = f"{ticker} crossed into a Buy/Speculative Buy threshold."
            _insert_alert(ticker, "Buy Threshold", old_score, new_score, message)
            messages.append(message)
        if float(old_score) >= 45 > float(new_score):
            message = f"{ticker} moved below the Hold threshold."
            _insert_alert(ticker, "Sell Threshold", old_score, new_score, message)
            messages.append(message)
    return " | ".join(messages) if messages else "No material change."


def record_signal(signal: dict) -> str:
    ticker = signal.get("ticker")
    if not ticker:
        return "No material change."
    prior = latest_signal(ticker)
    message = _material_change_alerts(ticker, prior, signal)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO signal_history (
                ticker, timestamp, composite_score, signal_label, confidence,
                growth_score, profitability_score, balance_sheet_score, valuation_score,
                momentum_score, catalyst_score, key_strengths, key_weaknesses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                now_et().isoformat(),
                signal.get("composite_score"),
                signal.get("signal_label"),
                signal.get("confidence"),
                signal.get("growth_score"),
                signal.get("profitability_score"),
                signal.get("balance_sheet_score"),
                signal.get("valuation_score"),
                signal.get("momentum_score"),
                signal.get("catalyst_score"),
                json.dumps(signal.get("strengths", [])),
                json.dumps(signal.get("weaknesses", [])),
            ),
        )
        conn.commit()
    return message


def _safe_signal(ticker: str) -> tuple[dict, str]:
    try:
        signal = compute_signal(ticker)
        return signal, "OK"
    except Exception as exc:
        return {
            "ticker": ticker,
            "signal_label": "No Rating / Insufficient Data",
            "composite_score": None,
            "confidence": "Low",
            "missing_data_warnings": [str(exc)],
        }, "Signal unavailable"


def _row_from_parts(ticker: str, quote: dict, signal: dict | None, alert: str, row_status: str, timestamp=None) -> dict:
    signal = signal or {}
    return {
        "Ticker": ticker,
        "Company": quote.get("company_name") or quote.get("company") or ticker,
        "Price": fmt_price(quote.get("price")),
        "Daily Move": fmt_daily_move(quote.get("daily_change_pct")),
        "Signal": signal.get("signal_label") or "No Rating / Insufficient Data",
        "Score": f"{float(signal.get('composite_score')):.1f}" if signal.get("composite_score") is not None else "N/A",
        "Confidence": signal.get("confidence") or "Low",
        "Volume": fmt_compact(quote.get("volume")),
        "Market Cap": fmt_compact(quote.get("market_cap"), prefix="$"),
        "Last Updated": fmt_date(timestamp or quote.get("last_updated") or now_et()),
        "Status": row_status,
        "Alert (D/D Change)": alert,
    }


def refresh_watchlist() -> pd.DataFrame:
    watch = list_watchlist()
    rows = []
    for ticker in watch.get("ticker", []):
        quote = fetch_quote(ticker)
        snapshot = save_quote_snapshot(ticker, quote)
        quote_status = snapshot.get("status", "Partial")
        signal, signal_status = _safe_signal(ticker)
        alert = "No material change."
        if signal_status == "OK":
            alert = record_signal(signal)
        row_status = quote_status if quote_status != "OK" else signal_status
        rows.append(_row_from_parts(ticker, {**quote, **snapshot}, signal, alert, row_status, now_et()))
    return pd.DataFrame(rows)


def latest_watchlist_table() -> pd.DataFrame:
    watch = list_watchlist()
    rows = []
    for ticker in watch.get("ticker", []):
        prior = latest_signal(ticker)
        snapshot = latest_quote_snapshot(ticker)
        if snapshot is None:
            quote = fetch_quote(ticker)
            snapshot = save_quote_snapshot(ticker, quote)
        signal = {
            "signal_label": prior.get("signal_label") if prior else "No Rating / Insufficient Data",
            "composite_score": prior.get("composite_score") if prior else None,
            "confidence": prior.get("confidence") if prior else "N/A",
        }
        alert = "Refresh watchlist to calculate." if prior is None else "No material change."
        row_status = snapshot.get("status", "Partial") if prior is None else snapshot.get("status", "OK")
        rows.append(_row_from_parts(ticker, snapshot, signal, alert, row_status, prior.get("timestamp") if prior else snapshot.get("timestamp")))
    return pd.DataFrame(rows)


def list_alerts(include_dismissed: bool = False) -> pd.DataFrame:
    init_db()
    query = "SELECT * FROM alerts"
    params: tuple = ()
    if not include_dismissed:
        query += " WHERE dismissed = 0"
    query += " ORDER BY timestamp DESC, id DESC LIMIT 100"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return pd.DataFrame([dict(row) for row in rows])


def dismiss_alert(alert_id: int) -> None:
    init_db()
    with connect() as conn:
        conn.execute("UPDATE alerts SET dismissed = 1 WHERE id = ?", (alert_id,))
        conn.commit()
