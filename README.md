# Research Terminal 2.0 - V1 MVP

A Bloomberg-style personal investment research terminal built with Streamlit.

V1 focuses on clean architecture, reliable fail-soft data flows, transparent scoring, SQLite-backed watchlists, in-app signal alerts, and optional OpenAI-powered due diligence summaries.

## Current Tab Structure

The cleanup pass consolidates the app into five primary tabs:

1. Home / Market Monitor
2. Company Analysis
3. Watchlist
4. AI Due Diligence
5. Data Health / Settings

Signal Center and Macro & Catalysts are now part of Company Analysis so a user can understand a company, its score, and recent catalysts in one workflow.

Volatility Radar is now part of Watchlist so options/implied-move monitoring lives next to watchlist signals and alerts.

## Features

- Dark market-terminal UI
- Global ticker search
- Home / Market Monitor with SPY, QQQ, DIA, IWM, VIX, BTC-USD, and 10Y proxy
- Company Analysis with quote, financials, valuation, balance sheet risk, filings, signal output, and catalysts
- Transparent signal model with factor scores, confidence, strengths, weaknesses, and triggers
- SQLite Watchlist with signal history and exact `Alert (D/D Change)` column
- In-app alert center for signal/score/confidence changes
- Watchlist options monitor with 7D and 30D implied move where options data exists
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

Terminology:

- Technical Entry Setup = a timing/technical setup indicator based on momentum, moving averages, RSI, and 52-week positioning. It is not a standalone buy/sell rating.
- Overall Research Signal = the broader investment research rating based on growth, profitability, balance sheet, valuation, momentum, catalysts, and data quality.

A stock can have a strong Technical Entry Setup while still remaining Hold / Watchlist if valuation, profitability, balance sheet risk, or data quality are not supportive.

Weights:

- Growth: 20%
- Profitability / margins: 15%
- Balance sheet / liquidity: 15%
- Valuation: 20%
- Momentum / technicals: 15%
- Catalysts / news: 15%

Signal labels:

- `80-100`: Buy
- `65-79`: Buy or Speculative Buy depending on risk
- `45-64`: Hold / Watchlist
- `25-44`: Sell / Trim
- `<25`: Avoid
- Sparse data: No Rating / Insufficient Data

Confidence is based on weighted data completeness and source quality:

- High: 80%+ weighted inputs available, valuation present, and financials valid
- Medium: 55-79% weighted inputs available
- Low: less than 55% weighted inputs available or major source gaps

Valuation and financial statement gaps reduce confidence. Momentum alone should not produce High confidence.

Signals are research indicators only, not investment advice.

## Financial Metric Quality

V1 suppresses misleading extreme ratios:

- Margins above 300% or below -300% are shown as `NM`
- Margins with tiny revenue denominators are shown as `NM`
- Revenue growth above 500% is shown as `NM / base effect`
- Missing values show `N/A`
- Not meaningful ratios show `NM`
- Raw `NaN`, `None`, `inf`, and long floats should not appear in the UI

Balance sheet risk now considers cash, debt, current ratio, free cash flow, debt/equity, and an approximate cash runway when FCF is negative. Cash greater than debt alone does not automatically mean Low risk.

## Options Statuses

The Watchlist options monitor uses friendlier statuses:

- OK
- No listed options
- Options unavailable from source
- No suitable expiration
- No suitable ATM strike
- Source error

Raw provider exceptions are kept in debug/data-health areas instead of being the main user-facing status.

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

The smoke test initializes SQLite, loads quotes, computes signals, checks options handling, verifies invalid ticker handling, and confirms the watchlist alert column exists.

## Known Limitations

- `yfinance` is MVP-grade and may be incomplete, delayed, or unreliable.
- Some tickers may lack options data.
- Some financial statement fields may be unavailable or provider-specific.
- Some valuation metrics are not meaningful for unprofitable companies.
- SEC filing lookup depends on SEC API availability and ticker-to-CIK mapping.
- In-app alerts only trigger when the app is opened/refreshed or when **Refresh Watchlist** is clicked.
- V1 is not investment advice.
- Signals are research indicators, not automatic trade instructions.
