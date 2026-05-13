from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.financials import load_latest_company_financials
from data.market_data import fetch_quote
from data.options import fetch_options_summary
from signals.signal_engine import compute_signal
from storage.db import init_db
from storage.watchlist import add_ticker, latest_watchlist_table, list_watchlist


def main() -> None:
    init_db()
    add_ticker("SPY")
    quote = fetch_quote("SPY")
    signal = compute_signal("SPY")
    financials = load_latest_company_financials("SPY")
    options = fetch_options_summary("SPY", quote.get("price"))
    invalid = fetch_quote("NOTAREALTICKERXYZ")
    watch = list_watchlist()
    latest = latest_watchlist_table()
    assert isinstance(quote, dict)
    assert "signal_label" in signal
    assert isinstance(financials, dict)
    assert isinstance(options, dict)
    assert isinstance(invalid, dict)
    assert "ticker" in watch.columns
    assert "Alert (D/D Change)" in latest.columns
    print("Research Terminal V1 smoke test completed.")


if __name__ == "__main__":
    main()
