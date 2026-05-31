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

V2 currently uses demo data only. The code is structured so future integrations can be added for:

- Market prices
- Fundamentals
- News
- SEC filings
- Earnings transcripts
- Economic data
- Analyst estimates
- Portfolio holdings

PineTerminal is a research workflow prototype, not investment advice.

