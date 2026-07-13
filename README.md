# PineTerminal

PineTerminal is a dark, institutional-style retail investment research terminal built with Streamlit.

This V2 demo rebuild focuses on an end-to-end investment dashboard:

- Business Quality / Fundamental Engine
- Bear, Base, and Bull future value modeling
- Probability-weighted expected value
- What Must Be True checklist
- Future Value Bridge
- Market-Implied Assumptions
- Market Read-Through / Indirect Catalyst Radar
- Latest Updates & Thesis Impact
- Top Risks to Thesis
- Sensitivity Table
- Final Investment Signal

The core product idea is:

```text
Business fundamentals + future valuation + market read-through + risk adjustment = investment signal
```

## Run Locally

Python version: `3.12`

```bash
pip install -r requirements.txt
streamlit run app.py
```

Or with `uv`:

```bash
uv run --python 3.12 --with-requirements requirements.txt streamlit run app.py
```

## App Structure

The app uses mock/demo data first and does not require live APIs.

Pages:

- Dashboard
- Home / Market Monitor
- Company Analysis
- Market Read-Through
- Screener
- Watchlist
- Thesis Tracker
- Portfolio
- News Feed
- Economic Data
- Calendar / Events
- Settings

AMPX is the default company, with reusable sample data for AMPX, MRVL, IONQ, MP, FBTC, NVDA, and CEG.

## Code Structure

- `app.py` wires the Streamlit shell and pages.
- `pineterminal/types.py` contains typed Python data models.
- `pineterminal/calculations.py` contains transparent scoring and valuation helpers.
- `pineterminal/demo_data.py` contains mock companies, theme exposures, thesis updates, and scenarios.
- `pineterminal/components.py` contains reusable rendering components.
- `pineterminal/styles.py` contains the PineTerminal dark terminal theme.
- `contracts/pineterminal.ts` mirrors the requested TypeScript interfaces and helper contracts for a future TS frontend.

## Data Sources

PineTerminal uses provider contracts and labels every live, delayed, partial, unavailable, or demo feed. Missing official data is never replaced with an unlabeled synthetic value.

- BLS Public Data API: CPI, unemployment, and total nonfarm payrolls
- BLS and BEA official calendars: scheduled economic release times
- FRED: supplementary macro series when `FRED_API_KEY` is configured
- SEC EDGAR: reported company facts and filings
- Finnhub: quotes, estimates, and news when `FINNHUB_API_KEY` is configured
- Yahoo Finance: explicitly labeled delayed or partial fallback data

Optional environment variables or Streamlit secrets:

```toml
BLS_API_KEY = "optional-key-for-higher-release-window-limits"
FRED_API_KEY = "required-for-pce-claims-rates-and-supplementary-macro-series"
MACRO_ALERT_WEBHOOK_URL = "optional-slack-discord-or-compatible-webhook"
DATA_USER_AGENT = "PineTerminal/2.0 contact@example.com"
```

The app conserves the public BLS quota between releases, schedules its next check for five minutes before a tracked event, polls every 60 seconds through the public release window, and polls every 15 seconds in that window when `BLS_API_KEY` is configured. In-app alerts are enabled by default. To keep webhook monitoring active independently of an open browser session, run the release worker alongside Streamlit:

```bash
uv run --python 3.12 --with-requirements requirements.txt python -m scripts.macro_release_monitor
```

PineTerminal is a research workflow prototype, not investment advice.
