# Market Intelligence Dashboard

A Streamlit dashboard with a sidebar tab switcher:

- **Home**: market dashboard landing page with index snapshot, sector performance, major news, quick stock snapshot, market catalysts, and a heuristic risk gauge.
- **Stock Due Diligence**: polished equity research dashboard with a top company selector, delayed quote module, intraday chart, compact financial KPI cards, themed charts/tables, stock-price performance ranges, target-year actuals vs analyst targets with Q1-Q4 breakouts, ratios, margins, cash flow, valuation, analyst EPS expectations vs actuals, public analyst report links where available, and raw financial tables.
- **Volatility Radar**: polished volatility analytics dashboard with scan-status badges, executive summary cards, stress chips, dark themed forecast tables, and integrated catalyst/news/social/data-health tabs across configurable stock universes.

The UI is tuned for a compact financial terminal workflow: dark market-screen styling, structured scan toolbars, compact summary cards, dense side filters, and integrated charts/tables.

The Volatility Radar ranks a stock universe by projected absolute volatility up to seven trading days ahead. It blends recent realized volatility with event-driven catalysts:

- Broad US exchange-listed universe loading from Nasdaq Trader symbol directories.
- Preset filters for S&P 500, Nasdaq-100, Dow 30, S&P MidCap 400, S&P SmallCap 600, all US listed stocks, and major exchanges.
- Market-cap, sector, price, liquidity, index, exchange, search, ETF, and random-sample filters.
- Earnings proximity from Yahoo Finance calendars.
- Options-implied volatility from near-horizon at-the-money chains, formatted as `+/-XX.XX%`.
- Side-by-side tactical and 30-day options-implied move benchmarks.
- Historical realized volatility windows for 20D, 60D, 90D, and 252D lookbacks.
- Same-horizon trailing realized move check for a quick forecast coverage/backtest view.
- Broad-universe scans sample across the full selected universe by default, then rank by options-implied move when available and projected move otherwise.
- User-selectable forecast sorting for option move, IV, ATR, volume spike, social engagement, or explicit ticker A-Z.
- Scheduled Reports pulls cached official/reputable economic-calendar sources where available, with clearly labeled fallback schedules for unavailable sources.
- Sidebar column selector for the Highest Projected Volatility table.
- Economic and socioeconomic stress from RSS headlines.
- Social mention volatility from configurable social RSS feeds, with optional Stocktwits symbol streams.
- Optional scheduled macro reports entered in the sidebar.
- Ticker-specific news, social chatter, volume shock, beta, ATR, momentum, gaps, and analyst target dispersion.

## Run

```powershell
$env:UV_CACHE_DIR = ".\.uv-cache"
uv run --python 3.12 --with-requirements requirements.txt streamlit run app.py
```

Or install the dependencies into an existing Python environment:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Notes

The forecast is an expected absolute move/risk ranking, not a price direction prediction or investment recommendation. The default forecast table pins Rank, Ticker, and Company, then shows Last Price, Options Move, and Direction Bias unless you choose more columns in the sidebar. Broad scans are capped in the sidebar because free data endpoints are too slow for thousands of tickers in one pass. Options IV and Stocktwits are optional live data sources because they add per-symbol requests. Feed URLs and free market-data endpoints can change, so the dashboard includes a Data Health tab for source status.

## Live Data And Refresh Strategy

The app has global Live Refresh controls in the sidebar. Auto-refresh reruns the Streamlit app on the chosen cadence, while `st.cache_data` TTLs prevent slow-moving data from being fetched too often.

Current data model:

- Quotes, sector ETFs, price charts, options chains, financial statements, analyst expectations, and analyst report links use Yahoo Finance/yfinance.
- Market and macro headlines use shared reputable RSS/API feeds and official sources, cached for 10 minutes.
- Scheduled Reports / Economic Calendar uses official or reputable public calendar sources, cached for 6 hours.
- Symbol universe and index membership data are cached daily.

Refresh cadence:

- Quotes and quick stock data refresh as frequently as the sidebar interval and quote cache allow.
- Sector performance refreshes on a short cache suitable for ETF quote snapshots.
- Volatility/options scans refresh on a slower cache to avoid excessive per-symbol option-chain calls.
- Fundamentals, analyst data, economic calendars, and universe data refresh less frequently because those sources move slowly.

Yahoo/yfinance is labeled as delayed or near-real-time fallback data, not true tick-by-tick market data. The dashboard is designed to feel live through safe refresh cadence and clear freshness indicators without changing the underlying data model.
