# Research Terminal 2.0 — V1 MVP

A Bloomberg-style personal investment research terminal built with Streamlit.

V1 focuses on clean architecture, reliable fail-soft data flows, transparent scoring, SQLite-backed watchlists, in-app signal alerts, and optional OpenAI-powered due diligence summaries.

## Features

- Dark market-terminal UI
- Global ticker search
- Home / Market Monitor with major ETF/index proxies
- Company Analysis with quote, price chart, financials, valuation, balance sheet risk, filings, and options metrics
- Transparent Signal Center with category scores and explainable strengths/weaknesses
- SQLite Watchlist with signal history and exact `Alert (D/D Change)` column
- In-app alert center for signal/score/confidence changes
- Volatility Radar with 7D and 30D implied move where options data exists
- Macro & Catalysts headline view
- AI Due Diligence memo generation when `OPENAI_API_KEY` is configured
- Data Health / Settings panel

## Run Locally

Python version: `3.12`

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app stores watchlist, signal history, and alerts in a local SQLite file:

```text
research_terminal.db
```

This file is intentionally ignored by git.

## Streamlit Secrets

Create `.streamlit/secrets.toml` locally or add secrets in Streamlit Community Cloud.

Optional AI due diligence:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

If `OPENAI_API_KEY` is missing, the AI Due Diligence tab shows a clean disabled state and the rest of the app still works.

## V1 Data Sources

- Market quotes, history, financials, options, analyst metadata: Yahoo Finance via `yfinance`
- Headlines: Yahoo Finance plus public RSS feeds where available
- Filings: SEC EDGAR company submissions API
- Storage: local SQLite
- AI memo: OpenAI API only when configured through Streamlit secrets

## Signal Center Methodology

The signal engine is transparent and deterministic. It is not a black-box model.

Weights:

- Growth: 20%
- Profitability / margins: 15%
- Balance sheet / liquidity: 15%
- Valuation: 20%
- Momentum / technicals: 15%
- Catalysts / news: 15%

Signal labels:

- `80–100`: Buy
- `65–79`: Buy or Speculative Buy depending on risk
- `45–64`: Hold / Watchlist
- `25–44`: Sell / Trim
- `<25`: Avoid
- Sparse data: No Rating / Insufficient Data

Signals are research indicators only, not investment advice.

## Watchlist Alerts And D/D Change

The Watchlist tab persists tickers in SQLite. When you click **Refresh Watchlist**, the app:

1. Calculates the current signal for each ticker.
2. Compares it to the latest prior `signal_history` record.
3. Creates an alert when a material day-over-day change occurs.

Alert triggers:

- Signal label changed
- Composite score changed by 5+ points
- Confidence changed
- Score crossed a Buy threshold
- Score crossed a Sell/Avoid threshold

The watchlist table includes the required column:

```text
Alert (D/D Change)
```

## Smoke Test

```bash
python scripts/smoke_test.py
```

The smoke test initializes SQLite, loads a quote, computes a signal, checks options handling, and verifies the watchlist alert column exists.

## Known Limitations

- `yfinance` is MVP-grade and may be incomplete, delayed, or unreliable.
- Some tickers may lack options data.
- Some financial statement fields may be unavailable or provider-specific.
- Some valuation metrics are not meaningful for unprofitable companies.
- SEC filing lookup depends on SEC API availability and ticker-to-CIK mapping.
- In-app alerts only trigger when the app is opened/refreshed or when **Refresh Watchlist** is clicked.
- V1 is not investment advice.
- Signals are research indicators, not automatic trade instructions.
