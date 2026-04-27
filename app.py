from __future__ import annotations

import calendar
import html
import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import StringIO
from typing import Iterable, Sequence
from urllib.parse import quote as url_quote, urlparse
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import altair as alt
import pandas as pd
import requests
import streamlit as st

try:
    import feedparser
except ModuleNotFoundError:
    feedparser = None

try:
    import yfinance as yf
    YFINANCE_IMPORT_ERROR = ""
except ModuleNotFoundError as exc:
    yf = None
    YFINANCE_IMPORT_ERROR = str(exc)
except Exception as exc:
    yf = None
    YFINANCE_IMPORT_ERROR = str(exc)

try:
    import plotly.graph_objects as go
except Exception:
    go = None


def plotly_go():
    global go
    if go is not None:
        return go
    try:
        import plotly.graph_objects as plotly_graph_objects
    except Exception:
        return None
    go = plotly_graph_objects
    return go


try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


DEFAULT_UNIVERSE = (
    "AAPL, MSFT, NVDA, AMD, AVGO, AMZN, GOOGL, META, TSLA, NFLX, JPM, XOM, "
    "UNH, LLY, PLTR, SMCI, COIN, MSTR"
)

DEFAULT_FEEDS = (
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("Nasdaq Markets", "https://www.nasdaq.com/feed/rssoutbound?category=Markets"),
    ("Nasdaq Stocks", "https://www.nasdaq.com/feed/rssoutbound?category=Stocks"),
    ("Investing.com Stocks", "https://www.investing.com/rss/news_25.rss"),
    ("Investing.com Economy", "https://www.investing.com/rss/news_14.rss"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("BLS Releases", "https://www.bls.gov/feed/news_release/all.rss"),
)

HOME_NEWS_FEEDS = (
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Nasdaq Markets", "https://www.nasdaq.com/feed/rssoutbound?category=Markets"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("BLS Releases", "https://www.bls.gov/feed/news_release/all.rss"),
)

MARKET_MACRO_FEEDS = tuple(dict.fromkeys(DEFAULT_FEEDS + HOME_NEWS_FEEDS))

GLOBAL_REFRESH_INTERVALS = {
    "30 seconds": 30,
    "1 minute": 60,
    "5 minutes": 300,
    "15 minutes": 900,
}

DATA_REFRESH_TTLS = {
    "Quotes / Market Snapshot": "30-75 seconds",
    "Quick Stock Snapshot": "60 seconds",
    "Sector Performance": "5 minutes",
    "Volatility / Options Signals": "5 minutes",
    "News / Headlines": "10 minutes",
    "Social Pulse": "10 minutes",
    "Analyst / Fundamentals": "6 hours",
    "Statement Sankey Charts": "6 hours",
    "Scheduled Reports / Economic Calendar": "6 hours",
    "Symbol Universe": "24 hours",
}

PROVIDER_HIERARCHY = {
    "Market Quotes": ["Yahoo Finance/yfinance", "Cached last successful Streamlit data"],
    "Quick Stock Snapshot": ["Yahoo Finance/yfinance quote, fast_info, and basic info", "Cached last successful Streamlit data"],
    "Stock Due Diligence": ["Yahoo Finance/yfinance financial statements and company info", "Cached/empty state"],
    "3-Statement Analysis": ["Yahoo Finance/yfinance financial statement matrices", "Cached/empty state"],
    "Analyst Expectations": ["Yahoo Finance/yfinance analyst estimates and public news links", "Clean empty state"],
    "Volatility Radar": ["Yahoo Finance/yfinance price history and option chains", "Cached/empty state"],
    "Sector Performance": ["Yahoo Finance/yfinance sector ETF quotes", "Cached last successful Streamlit data"],
    "News Headlines": ["Reputable RSS/API and official feeds", "Yahoo Finance only after relevance filters", "Cached last successful feed set"],
    "Economic Calendar": ["Official and reputable public sources", "Cached fallback"],
}

DEFAULT_SOCIAL_FEEDS = (
    ("Reddit WallStreetBets", "https://www.reddit.com/r/wallstreetbets/new.rss"),
    ("Reddit Stocks", "https://www.reddit.com/r/stocks/new.rss"),
    ("Reddit Investing", "https://www.reddit.com/r/investing/new.rss"),
    ("Reddit StockMarket", "https://www.reddit.com/r/StockMarket/new.rss"),
)

HOME_MARKET_SYMBOLS = (
    {"label": "S&P 500", "symbol": "^GSPC", "type": "index"},
    {"label": "Nasdaq 100", "symbol": "^NDX", "type": "index"},
    {"label": "Dow Jones", "symbol": "^DJI", "type": "index"},
    {"label": "Russell 2000", "symbol": "^RUT", "type": "index"},
    {"label": "VIX", "symbol": "^VIX", "type": "index"},
    {"label": "10Y Treasury", "symbol": "^TNX", "type": "yield"},
)

SECTOR_ETFS = (
    ("Technology", "XLK"),
    ("Communication Services", "XLC"),
    ("Consumer Discretionary", "XLY"),
    ("Consumer Staples", "XLP"),
    ("Financials", "XLF"),
    ("Healthcare", "XLV"),
    ("Industrials", "XLI"),
    ("Energy", "XLE"),
    ("Utilities", "XLU"),
    ("Real Estate", "XLRE"),
    ("Materials", "XLB"),
)

DEFAULT_MACRO_EVENTS = ""

ECONOMIC_CALENDAR_SOURCES = {
    "BLS": "https://www.bls.gov/schedule/news_release/bls.ics",
    "BEA": "https://www.bea.gov/news/schedule",
    "Census": "https://www.census.gov/economic-indicators/calendar-listview.html",
    "Federal Reserve": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "ISM": "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/release-schedule/",
    "Treasury": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/auctions_query",
    "EIA": "https://www.eia.gov/petroleum/supply/weekly/",
    "DOL ETA": "https://oui.doleta.gov/unemploy/claims.asp",
    "Conference Board": "https://www.conference-board.org/topics/consumer-confidence",
}

ECONOMIC_RELEASE_KEYWORDS = {
    "cpi",
    "consumer price",
    "ppi",
    "producer price",
    "employment situation",
    "nonfarm",
    "payroll",
    "unemployment",
    "average hourly earnings",
    "jobless claims",
    "gross domestic product",
    "gdp",
    "personal income",
    "personal outlays",
    "personal consumption expenditures",
    "pce",
    "retail sales",
    "housing starts",
    "new residential construction",
    "new home sales",
    "durable goods",
    "trade",
    "international trade",
    "ism",
    "manufacturing pmi",
    "services pmi",
    "consumer confidence",
    "fomc",
    "federal open market committee",
    "treasury auction",
    "petroleum status",
    "natural gas",
    "crude oil",
}

PERFORMANCE_RANGES = {
    "MAX": {"period": "max", "interval": "1d", "label": "Max history"},
    "5Y": {"period": "5y", "interval": "1d", "label": "5 year"},
    "1Y": {"period": "1y", "interval": "1d", "label": "1 year"},
    "1M": {"period": "1mo", "interval": "1d", "label": "1 month"},
    "YTD": {"period": "ytd", "interval": "1d", "label": "Year to date"},
    "5D": {"period": "5d", "interval": "15m", "label": "5 day"},
    "1D": {"period": "1d", "interval": "5m", "label": "1 day"},
}

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

INDEX_SOURCES = {
    "S&P 500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "columns": ("Symbol", "Ticker", "Ticker symbol"),
    },
    "Nasdaq-100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "columns": ("Ticker", "Symbol"),
    },
    "Dow 30": {
        "url": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        "columns": ("Symbol", "Ticker"),
    },
    "S&P MidCap 400": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "columns": ("Ticker symbol", "Symbol", "Ticker"),
    },
    "S&P SmallCap 600": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        "columns": ("Ticker symbol", "Symbol", "Ticker"),
    },
}

EXCHANGE_CODE_MAP = {
    "A": "NYSE American",
    "N": "NYSE",
    "P": "NYSE Arca",
    "Z": "Cboe BZX",
    "V": "IEX",
}

UNIVERSE_PRESETS = [
    "S&P 500",
    "Nasdaq-100",
    "Dow 30",
    "S&P MidCap 400",
    "S&P SmallCap 600",
    "All major indexes",
    "All US listed",
    "NASDAQ listed",
    "NYSE listed",
    "NYSE American",
    "NYSE Arca",
    "Cboe/IEX listed",
    "Custom list",
]

MARKET_CAP_BUCKETS = {
    "Mega cap ($200B+)": (200_000_000_000, None),
    "Large cap ($10B-$200B)": (10_000_000_000, 200_000_000_000),
    "Mid cap ($2B-$10B)": (2_000_000_000, 10_000_000_000),
    "Small cap ($300M-$2B)": (300_000_000, 2_000_000_000),
    "Micro cap (<$300M)": (0, 300_000_000),
    "Unknown market cap": (None, None),
}

SECTOR_OPTIONS = [
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Financial Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
    "Unknown",
]

POSITIVE_TERMS = {
    "advance",
    "beat",
    "beats",
    "boost",
    "bullish",
    "buyback",
    "climb",
    "gain",
    "growth",
    "higher",
    "improve",
    "jump",
    "outperform",
    "profit",
    "rally",
    "rebound",
    "record",
    "recover",
    "rise",
    "strong",
    "surge",
    "upgrade",
    "upside",
}

NEGATIVE_TERMS = {
    "bearish",
    "cut",
    "cuts",
    "decline",
    "downgrade",
    "drop",
    "fall",
    "fear",
    "loss",
    "lower",
    "miss",
    "pressure",
    "recession",
    "risk",
    "selloff",
    "sell-off",
    "slump",
    "slowdown",
    "tumble",
    "volatility",
    "warning",
    "weak",
}

VOLATILITY_TERMS = {
    "activist",
    "antitrust",
    "bankruptcy",
    "breakout",
    "class action",
    "downgrade",
    "earnings",
    "forecast",
    "guidance",
    "halt",
    "investigation",
    "lawsuit",
    "merger",
    "probe",
    "recall",
    "restructuring",
    "rumor",
    "short seller",
    "spinoff",
    "upgrade",
}

MARKET_HEADLINE_RELEVANCE_TERMS = {
    "analyst",
    "bank",
    "bond",
    "cpi",
    "credit",
    "dow",
    "earnings",
    "economy",
    "etf",
    "fed",
    "federal reserve",
    "fomc",
    "gdp",
    "inflation",
    "ipo",
    "jobs",
    "market",
    "markets",
    "nasdaq",
    "oil",
    "payroll",
    "pce",
    "portfolio",
    "price target",
    "rate",
    "rates",
    "recession",
    "retail sales",
    "russell",
    "s&p",
    "shares",
    "stock",
    "stocks",
    "treasury",
    "unemployment",
    "vix",
    "wall street",
    "yield",
}

LOW_QUALITY_HEADLINE_TERMS = {
    "astrology",
    "celebrity",
    "coupon",
    "diet",
    "grocery",
    "horoscope",
    "lottery",
    "net worth",
    "recipe",
    "retirement quiz",
    "shopping",
    "travel hack",
    "weight loss",
}

OFFICIAL_OR_MARKET_SOURCES = {
    "AP",
    "Associated Press",
    "BLS Releases",
    "CNBC Markets",
    "Federal Reserve",
    "Investing.com Economy",
    "Investing.com Stocks",
    "MarketWatch",
    "Nasdaq Markets",
    "Nasdaq Stocks",
    "Reuters",
    "Yahoo Finance",
}

ANALYST_REPORT_TERMS = (
    "analyst",
    "analyst report",
    "research report",
    "broker note",
    "price target",
    "rating",
    "upgrade",
    "downgrade",
    "initiates",
    "initiate",
    "reiterates",
    "maintains",
    "raises",
    "lowers",
    "outperform",
    "underperform",
    "overweight",
    "underweight",
    "buy rating",
    "sell rating",
    "hold rating",
)

MACRO_FACTOR_TERMS: dict[str, dict[str, float]] = {
    "Rates & Inflation": {
        "cpi": 5.0,
        "pce": 4.5,
        "inflation": 4.0,
        "fomc": 5.0,
        "fed": 2.8,
        "federal reserve": 4.0,
        "rate cut": 4.0,
        "rate hike": 4.0,
        "interest rate": 3.5,
        "treasury yield": 3.2,
        "bond yield": 2.8,
    },
    "Labor & Consumer": {
        "jobs": 3.4,
        "payroll": 4.0,
        "unemployment": 4.0,
        "jobless claims": 4.0,
        "wages": 2.8,
        "consumer confidence": 3.0,
        "retail sales": 3.6,
        "household": 2.2,
    },
    "Growth & Housing": {
        "gdp": 4.0,
        "pmi": 3.2,
        "ism": 3.2,
        "manufacturing": 2.8,
        "services": 2.5,
        "housing starts": 3.4,
        "home sales": 3.0,
        "construction": 2.0,
    },
    "Credit & Liquidity": {
        "credit": 3.4,
        "liquidity": 3.4,
        "default": 4.2,
        "debt ceiling": 4.0,
        "bank stress": 4.5,
        "loan": 2.2,
        "delinquency": 3.4,
        "funding": 2.6,
    },
    "Geopolitics & Policy": {
        "tariff": 4.0,
        "sanction": 3.8,
        "war": 4.5,
        "conflict": 3.7,
        "election": 3.0,
        "shutdown": 3.6,
        "regulation": 2.8,
        "export control": 4.0,
        "trade": 2.4,
    },
    "Energy & Supply": {
        "oil": 3.4,
        "opec": 3.8,
        "natural gas": 3.0,
        "supply chain": 3.4,
        "shipping": 2.6,
        "semiconductor": 2.8,
        "commodity": 2.8,
    },
}

STANDARD_MACRO_CATEGORIES = [
    "Inflation",
    "Labor",
    "Fed / Rates",
    "Growth & Housing",
    "Credit & Liquidity",
    "Energy",
    "Consumer",
    "Geopolitical / Macro Risk",
]

MACRO_CATEGORY_ALIASES = {
    "Rates & Inflation": "Fed / Rates",
    "Fed": "Fed / Rates",
    "Rates": "Fed / Rates",
    "Inflation": "Inflation",
    "Labor & Consumer": "Labor",
    "Labor": "Labor",
    "Consumer": "Consumer",
    "Growth": "Growth & Housing",
    "Housing": "Growth & Housing",
    "Growth & Housing": "Growth & Housing",
    "Credit & Liquidity": "Credit & Liquidity",
    "Energy & Supply": "Energy",
    "Energy": "Energy",
    "Geopolitics & Policy": "Geopolitical / Macro Risk",
    "Geopolitical / Macro Risk": "Geopolitical / Macro Risk",
    "Macro": "Geopolitical / Macro Risk",
    "Scheduled Reports": "Geopolitical / Macro Risk",
}

SECTOR_FACTOR_WEIGHTS: dict[str, dict[str, float]] = {
    "Technology": {
        "Rates & Inflation": 1.25,
        "Geopolitics & Policy": 1.2,
        "Energy & Supply": 1.1,
        "Credit & Liquidity": 1.05,
    },
    "Communication Services": {
        "Rates & Inflation": 1.1,
        "Labor & Consumer": 1.15,
        "Geopolitics & Policy": 1.05,
    },
    "Consumer Cyclical": {
        "Rates & Inflation": 1.25,
        "Labor & Consumer": 1.35,
        "Growth & Housing": 1.15,
    },
    "Consumer Defensive": {
        "Rates & Inflation": 1.05,
        "Labor & Consumer": 1.05,
    },
    "Financial Services": {
        "Rates & Inflation": 1.35,
        "Credit & Liquidity": 1.45,
        "Growth & Housing": 1.15,
    },
    "Energy": {
        "Energy & Supply": 1.55,
        "Geopolitics & Policy": 1.3,
        "Rates & Inflation": 1.05,
    },
    "Industrials": {
        "Growth & Housing": 1.25,
        "Energy & Supply": 1.15,
        "Geopolitics & Policy": 1.1,
    },
    "Healthcare": {
        "Geopolitics & Policy": 1.15,
        "Credit & Liquidity": 1.0,
    },
    "Real Estate": {
        "Rates & Inflation": 1.45,
        "Credit & Liquidity": 1.25,
        "Growth & Housing": 1.25,
    },
    "Utilities": {
        "Rates & Inflation": 1.35,
        "Energy & Supply": 1.15,
    },
    "Basic Materials": {
        "Energy & Supply": 1.25,
        "Growth & Housing": 1.2,
        "Geopolitics & Policy": 1.1,
    },
}

FORECAST_COLUMNS = [
    "Rank",
    "Ticker",
    "Company",
    "Exchange",
    "Index Membership",
    "Sector",
    "Size",
    "Market Cap",
    "Last Price",
    "Avg Dollar Volume",
    "Projected Move %",
    "Options Move %",
    "Options IV %",
    "Options Expiry",
    "30D Options Move %",
    "30D Options IV %",
    "30D Options Expiry",
    "20D Hist Move %",
    "60D Hist Move %",
    "90D Hist Move %",
    "252D Hist Move %",
    "Backtest Move %",
    "Backtest Error %",
    "Backtest Result",
    "Volatility Score",
    "Confidence",
    "Direction Bias",
    "Base Move %",
    "Earnings Risk",
    "Macro Risk",
    "News Risk",
    "Social Risk",
    "Social Mentions",
    "Social Engagement",
    "Social Sentiment",
    "Volume Risk",
    "Analyst Dispersion",
    "Beta",
    "Volume Shock",
    "ATR Move %",
    "Ann. Realized Vol %",
    "Earnings Date",
    "Days To Earnings",
    "Main Drivers",
    "Data Notes",
]

PINNED_FORECAST_COLUMNS = ["Rank", "Ticker", "Company"]
DEFAULT_FORECAST_DISPLAY_COLUMNS = ["Last Price", "Options Move %", "Direction Bias"]
HISTORICAL_WINDOW_COLUMNS = {
    "20D": "20D Hist Move %",
    "60D": "60D Hist Move %",
    "90D": "90D Hist Move %",
    "252D": "252D Hist Move %",
}
BENCHMARK_30D_COLUMNS = ["30D Options Move %", "30D Options IV %", "30D Options Expiry"]
BACKTEST_COLUMNS = ["Backtest Move %", "Backtest Error %", "Backtest Result"]

FINANCIAL_LINE_ITEMS = {
    "Revenue": ("Total Revenue", "Operating Revenue"),
    "Gross Profit": ("Gross Profit",),
    "Operating Income": ("Operating Income", "Operating Income Loss"),
    "Net Income": ("Net Income", "Net Income Common Stockholders"),
    "EBITDA": ("EBITDA", "Normalized EBITDA"),
    "Diluted EPS": ("Diluted EPS", "Basic EPS"),
    "Total Assets": ("Total Assets",),
    "Total Debt": ("Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"),
    "Cash": ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"),
    "Stockholders Equity": ("Stockholders Equity", "Total Equity Gross Minority Interest"),
    "Current Assets": ("Current Assets",),
    "Current Liabilities": ("Current Liabilities",),
    "Operating Cash Flow": ("Operating Cash Flow", "Total Cash From Operating Activities"),
    "Capital Expenditure": ("Capital Expenditure", "Capital Expenditures"),
    "Free Cash Flow": ("Free Cash Flow",),
}

INCOME_SANKEY_FIELDS = {
    "Revenue": ("revenue", "totalRevenue", "revenues", "Total Revenue", "Operating Revenue"),
    "Cost of Revenue": ("costOfRevenue", "costRevenue", "Cost Of Revenue", "Cost Revenue", "Cost Of Goods Sold"),
    "Gross Profit": ("grossProfit", "Gross Profit"),
    "R&D": ("researchAndDevelopmentExpenses", "Research And Development", "Research Development"),
    "Sales & Marketing": ("sellingAndMarketingExpenses", "Selling And Marketing Expense", "Selling And Marketing"),
    "SG&A": ("sellingGeneralAndAdministrativeExpenses", "Selling General And Administration", "Selling General Administrative"),
    "G&A": ("generalAndAdministrativeExpenses", "General And Administrative Expense", "General And Administrative"),
    "Operating Expenses": ("operatingExpenses", "Operating Expense", "Total Operating Expenses"),
    "Other Operating Expenses": ("otherOperatingExpenses", "Other Operating Expenses", "Other Operating Expense"),
    "Operating Income": ("operatingIncome", "Operating Income", "Operating Income Loss"),
    "Interest Expense": ("interestExpense", "Interest Expense", "Interest Expense Non Operating"),
    "Interest Income": ("interestIncome", "Interest Income", "Interest Income Non Operating"),
    "Other Income / Expense": ("otherIncomeExpense", "Other Income Expense", "Other Non Operating Income Expenses"),
    "Pretax Income": ("incomeBeforeTax", "Pretax Income", "Income Before Tax"),
    "Taxes": ("incomeTaxExpense", "Tax Provision", "Income Tax Expense"),
    "Net Income": ("netIncome", "Net Income", "Net Income Common Stockholders"),
    "EPS": ("eps", "dilutedEPS", "Diluted EPS", "Basic EPS"),
}

BALANCE_SANKEY_FIELDS = {
    "Total Assets": ("totalAssets", "Total Assets"),
    "Current Assets": ("totalCurrentAssets", "Current Assets", "Total Current Assets"),
    "Cash": (
        "cashAndCashEquivalents",
        "cashAndCashEquivalentsAtCarryingValue",
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ),
    "Accounts Receivable": ("netReceivables", "accountsReceivable", "Accounts Receivable", "Receivables"),
    "Inventory": ("inventory", "Inventory"),
    "PP&E": ("propertyPlantEquipmentNet", "Net PPE", "Property Plant Equipment", "Properties"),
    "Goodwill / Intangibles": ("goodwillAndIntangibleAssets", "Goodwill And Other Intangible Assets", "Goodwill", "Other Intangible Assets"),
    "Other Current Assets": ("otherCurrentAssets", "Other Current Assets"),
    "Non-current Assets": ("totalNonCurrentAssets", "Non Current Assets", "Total Non Current Assets"),
    "Total Liabilities": ("totalLiabilities", "Total Liabilities Net Minority Interest", "Total Liabilities"),
    "Current Liabilities": ("totalCurrentLiabilities", "Current Liabilities", "Total Current Liabilities"),
    "Long-term Debt": ("longTermDebt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"),
    "Short-term Debt": ("shortTermDebt", "Current Debt", "Short Term Debt"),
    "Total Debt": ("totalDebt", "Total Debt"),
    "Other Liabilities": ("otherLiabilities", "Other Liabilities", "Other Non Current Liabilities"),
    "Shareholders' Equity": (
        "totalStockholdersEquity",
        "totalShareholderEquity",
        "stockholdersEquity",
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
    ),
}

CASH_FLOW_SANKEY_FIELDS = {
    "Net Income": ("netIncome", "Net Income", "Net Income From Continuing Operations"),
    "D&A": ("depreciationAndAmortization", "Depreciation And Amortization", "Depreciation Amortization Depletion"),
    "Change in Working Capital": ("changeInWorkingCapital", "Change In Working Capital", "Changes In Working Capital"),
    "Operating Cash Flow": ("operatingCashFlow", "netCashProvidedByOperatingActivities", "Operating Cash Flow", "Total Cash From Operating Activities"),
    "Capital Expenditures": ("capitalExpenditure", "capitalExpenditures", "Capital Expenditure", "Capital Expenditures"),
    "Free Cash Flow": ("freeCashFlow", "Free Cash Flow"),
    "Investing Cash Flow": ("netCashUsedForInvestingActivities", "netCashProvidedByInvestingActivities", "Investing Cash Flow", "Total Cash From Investing Activities"),
    "Financing Cash Flow": ("netCashProvidedByFinancingActivities", "netCashUsedProvidedByFinancingActivities", "Financing Cash Flow", "Total Cash From Financing Activities"),
    "Dividends": ("dividendsPaid", "Cash Dividends Paid", "Dividends Paid"),
    "Buybacks": ("commonStockRepurchased", "repurchasesOfStock", "Repurchase Of Capital Stock", "Common Stock Repurchased"),
    "Debt Issuance": ("debtIssuance", "Issuance Of Debt", "Long Term Debt Issuance"),
    "Debt Repayment": ("debtRepayment", "debtRepayments", "Repayment Of Debt", "Long Term Debt Payments"),
    "Net Change in Cash": ("netChangeInCash", "changeInCash", "Changes In Cash", "Net Change In Cash"),
}


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    summary: str
    source: str
    published: datetime | None
    sentiment: str
    sentiment_score: float
    mentions: tuple[str, ...]
    macro_score: float
    macro_factors: tuple[str, ...]


@dataclass(frozen=True)
class SocialMention:
    title: str
    body: str
    link: str
    source: str
    published: datetime | None
    sentiment: str
    sentiment_score: float
    mentions: tuple[str, ...]
    engagement: int


@dataclass(frozen=True)
class MacroEvent:
    event_date: date | None
    name: str
    importance: int
    notes: str
    days_until: int | None
    in_horizon: bool
    factor: str
    event_datetime: datetime | None = None
    release_time: str = "N/A"
    source: str = "User"
    category: str = "Macro"
    impact: str = "Medium"
    previous: str = "N/A"
    forecast: str = "N/A"
    actual: str = "N/A"
    last_updated: datetime | None = None
    source_url: str = ""


@dataclass(frozen=True)
class ProviderMetadata:
    provider_name: str
    data_type: str
    freshness_status: str
    last_updated: datetime
    is_realtime: bool = False
    is_delayed: bool = True
    is_cached: bool = False
    delay_disclaimer: str = ""
    rate_limit_notes: str = ""
    source_label: str = ""
    source_url: str = ""
    error: str = ""


@dataclass(frozen=True)
class MacroContext:
    stress_score: float
    factor_scores: tuple[tuple[str, float], ...]
    events: tuple[MacroEvent, ...]
    top_headlines: tuple[Article, ...]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_watchlist(raw_value: str) -> list[str]:
    tickers = []
    seen = set()
    for token in re.split(r"[\s,;]+", raw_value.upper()):
        ticker = token.strip().replace("$", "")
        if not ticker or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker):
            continue
        if ticker not in seen:
            tickers.append(ticker)
            seen.add(ticker)
    return tickers


def normalize_symbol(value: object) -> str:
    text = clean_text(str(value or "")).upper()
    text = text.replace("/", "-").replace(".", "-")
    text = re.sub(r"\s+", "-", text)
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{0,12}", text):
        return ""
    return text


def looks_like_common_stock(name: object, is_etf: bool) -> bool:
    if is_etf:
        return False
    lowered = clean_text(str(name or "")).lower()
    non_common_terms = (
        "warrant",
        "right",
        "unit",
        "preferred",
        "preference",
        "depositary share",
        "note due",
        "senior notes",
        "subordinated notes",
        "baby bond",
    )
    return not any(term in lowered for term in non_common_terms)


def request_text(url: str, source: str) -> tuple[str, dict]:
    status = {
        "source": source,
        "url": url,
        "status": "OK",
        "rows": 0,
        "message": "",
    }
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "volatility-radar/1.0 (+https://streamlit.io)"},
            timeout=15,
        )
        response.raise_for_status()
        return response.text, status
    except requests.RequestException as exc:
        status["status"] = "Error"
        status["message"] = str(exc)
        return "", status


def parse_pipe_table(text: str) -> pd.DataFrame:
    if not text:
        return pd.DataFrame()
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.startswith("File Creation Time")
    ]
    if not lines:
        return pd.DataFrame()
    return pd.read_csv(StringIO("\n".join(lines)), sep="|")


def normalize_directory_frame(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    if source == "NASDAQ Listed":
        normalized = pd.DataFrame(
            {
                "Ticker": frame.get("Symbol", pd.Series(dtype=object)).map(normalize_symbol),
                "Security Name": frame.get("Security Name", ""),
                "Exchange": "NASDAQ",
                "Listing Group": "NASDAQ Listed",
                "Is ETF": frame.get("ETF", "").astype(str).str.upper().eq("Y"),
                "Test Issue": frame.get("Test Issue", "").astype(str).str.upper().eq("Y"),
            }
        )
    else:
        raw_symbol = frame.get("NASDAQ Symbol")
        if raw_symbol is None:
            raw_symbol = frame.get("ACT Symbol", pd.Series(dtype=object))
        exchange = frame.get("Exchange", "").astype(str).str.upper().map(EXCHANGE_CODE_MAP).fillna("Other")
        normalized = pd.DataFrame(
            {
                "Ticker": raw_symbol.map(normalize_symbol),
                "Security Name": frame.get("Security Name", ""),
                "Exchange": exchange,
                "Listing Group": "Other Listed",
                "Is ETF": frame.get("ETF", "").astype(str).str.upper().eq("Y"),
                "Test Issue": frame.get("Test Issue", "").astype(str).str.upper().eq("Y"),
            }
        )

    normalized = normalized[normalized["Ticker"].astype(bool)]
    normalized = normalized[~normalized["Test Issue"]]
    normalized["Is Stock"] = normalized.apply(
        lambda row: looks_like_common_stock(row["Security Name"], bool(row["Is ETF"])),
        axis=1,
    )
    normalized["Index Membership"] = ""
    return normalized


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_us_listed_symbols() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    statuses = []
    for source, url in (
        ("NASDAQ Listed", NASDAQ_LISTED_URL),
        ("Other Listed", OTHER_LISTED_URL),
    ):
        text, status = request_text(url, source)
        parsed = parse_pipe_table(text)
        normalized = normalize_directory_frame(parsed, source)
        status["rows"] = len(normalized)
        rows.append(normalized)
        statuses.append(status)

    if rows:
        universe = pd.concat(rows, ignore_index=True)
    else:
        universe = pd.DataFrame()
    if not universe.empty:
        universe = universe.drop_duplicates("Ticker").sort_values("Ticker").reset_index(drop=True)
    return universe, pd.DataFrame(statuses)


def flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    flattened = frame.copy()
    if isinstance(flattened.columns, pd.MultiIndex):
        flattened.columns = [
            " ".join(str(part) for part in column if str(part) != "nan").strip()
            for column in flattened.columns
        ]
    else:
        flattened.columns = [str(column).strip() for column in flattened.columns]
    return flattened


def parse_html_tables(text: str) -> list[pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    for table_html in re.findall(r"<table\b.*?</table>", text, flags=re.IGNORECASE | re.DOTALL):
        parsed_rows: list[list[str]] = []
        for row_html in re.findall(r"<tr\b.*?</tr>", table_html, flags=re.IGNORECASE | re.DOTALL):
            cells = re.findall(r"<t[dh]\b.*?</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)
            values = [clean_text(cell) for cell in cells]
            if values:
                parsed_rows.append(values)
        if len(parsed_rows) < 2:
            continue
        header = parsed_rows[0]
        data_rows = []
        for row in parsed_rows[1:]:
            padded = row + [""] * max(len(header) - len(row), 0)
            data_rows.append(padded[: len(header)])
        if data_rows:
            tables.append(pd.DataFrame(data_rows, columns=header))
    return tables


def read_index_symbols(url: str, columns: tuple[str, ...]) -> list[str]:
    text, status = request_text(url, urlparse(url).netloc or "Index source")
    if status["status"] != "OK":
        return []
    try:
        tables = pd.read_html(StringIO(text))
    except (ImportError, ValueError):
        tables = parse_html_tables(text)

    for table in tables:
        table = flatten_columns(table)
        column_lookup = {column.lower(): column for column in table.columns}
        for wanted in columns:
            column = column_lookup.get(wanted.lower())
            if column:
                symbols = [normalize_symbol(value) for value in table[column].dropna().tolist()]
                symbols = [symbol for symbol in symbols if symbol]
                if symbols:
                    return symbols
        for column in table.columns:
            lowered = str(column).lower()
            if "symbol" in lowered or "ticker" in lowered:
                symbols = [normalize_symbol(value) for value in table[column].dropna().tolist()]
                symbols = [symbol for symbol in symbols if symbol]
                if symbols:
                    return symbols
    return []


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_index_memberships() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    statuses = []
    for index_name, config in INDEX_SOURCES.items():
        status = {
            "source": index_name,
            "url": config["url"],
            "status": "OK",
            "rows": 0,
            "message": "",
        }
        symbols = read_index_symbols(config["url"], config["columns"])
        if not symbols:
            status["status"] = "Warning"
            status["message"] = "No symbols parsed; install lxml/html5lib if this source is needed."
        status["rows"] = len(symbols)
        statuses.append(status)
        rows.extend({"Ticker": symbol, "Index": index_name} for symbol in symbols)
    membership = pd.DataFrame(rows)
    if not membership.empty:
        membership = membership.drop_duplicates().sort_values(["Index", "Ticker"]).reset_index(drop=True)
    return membership, pd.DataFrame(statuses)


@st.cache_data(ttl=86_400, show_spinner=False)
def load_symbol_universe(include_etfs: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    listed, listed_status = fetch_us_listed_symbols()
    memberships, index_status = fetch_index_memberships()

    if listed.empty:
        listed = pd.DataFrame(
            {
                "Ticker": parse_watchlist(DEFAULT_UNIVERSE),
                "Security Name": parse_watchlist(DEFAULT_UNIVERSE),
                "Exchange": "Unknown",
                "Listing Group": "Fallback",
                "Is ETF": False,
                "Test Issue": False,
                "Is Stock": True,
                "Index Membership": "",
            }
        )

    universe = listed.copy()
    if not memberships.empty:
        index_map = memberships.groupby("Ticker")["Index"].apply(lambda values: ", ".join(sorted(set(values))))
        universe["Index Membership"] = universe["Ticker"].map(index_map).fillna("")
        missing_index_symbols = sorted(set(memberships["Ticker"]) - set(universe["Ticker"]))
        if missing_index_symbols:
            extras = pd.DataFrame(
                {
                    "Ticker": missing_index_symbols,
                    "Security Name": missing_index_symbols,
                    "Exchange": "Unknown",
                    "Listing Group": "Index Only",
                    "Is ETF": False,
                    "Test Issue": False,
                    "Is Stock": True,
                    "Index Membership": [
                        index_map.get(symbol, "") for symbol in missing_index_symbols
                    ],
                }
            )
            universe = pd.concat([universe, extras], ignore_index=True)

    if not include_etfs:
        universe = universe[universe["Is Stock"]]

    status = pd.concat([listed_status, index_status], ignore_index=True)
    universe = universe.drop_duplicates("Ticker").sort_values("Ticker").reset_index(drop=True)
    return universe, status


def apply_universe_preset(frame: pd.DataFrame, preset: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    if preset in INDEX_SOURCES:
        return frame[frame["Index Membership"].str.contains(re.escape(preset), na=False)]
    if preset == "All major indexes":
        return frame[frame["Index Membership"].astype(str).str.len() > 0]
    if preset == "NASDAQ listed":
        return frame[frame["Exchange"].eq("NASDAQ")]
    if preset == "NYSE listed":
        return frame[frame["Exchange"].eq("NYSE")]
    if preset == "NYSE American":
        return frame[frame["Exchange"].eq("NYSE American")]
    if preset == "NYSE Arca":
        return frame[frame["Exchange"].eq("NYSE Arca")]
    if preset == "Cboe/IEX listed":
        return frame[frame["Exchange"].isin(["Cboe BZX", "IEX"])]
    return frame


def spread_sample_frame(frame: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if frame.empty or len(frame) <= max_rows:
        return frame.reset_index(drop=True)
    if max_rows <= 1:
        return frame.head(max(max_rows, 0)).reset_index(drop=True)
    last_index = len(frame) - 1
    selected: list[int] = []
    seen: set[int] = set()
    for position in range(max_rows):
        index = round(position * last_index / (max_rows - 1))
        if index not in seen:
            selected.append(index)
            seen.add(index)
    if len(selected) < max_rows:
        for index in range(len(frame)):
            if index not in seen:
                selected.append(index)
                seen.add(index)
                if len(selected) == max_rows:
                    break
    return frame.iloc[sorted(selected[:max_rows])].reset_index(drop=True)


def select_scan_universe(
    universe: pd.DataFrame,
    preset: str,
    exchange_filters: list[str],
    index_filters: list[str],
    symbol_query: str,
    custom_tickers: list[str],
    scan_strategy: str,
    max_symbols: int,
    random_seed: int,
) -> pd.DataFrame:
    if preset == "Custom list":
        base = pd.DataFrame(
            {
                "Ticker": custom_tickers,
                "Security Name": custom_tickers,
                "Exchange": "Custom",
                "Listing Group": "Custom",
                "Is ETF": False,
                "Test Issue": False,
                "Is Stock": True,
                "Index Membership": "",
            }
        )
    else:
        base = apply_universe_preset(universe, preset).copy()
        if exchange_filters:
            base = base[base["Exchange"].isin(exchange_filters)]
        if index_filters:
            pattern = "|".join(re.escape(item) for item in index_filters)
            base = base[base["Index Membership"].str.contains(pattern, na=False)]
        query = symbol_query.strip().upper()
        if query:
            haystack = (
                base["Ticker"].astype(str)
                + " "
                + base["Security Name"].astype(str).str.upper()
                + " "
                + base["Exchange"].astype(str).str.upper()
            )
            base = base[haystack.str.contains(re.escape(query), na=False)]
        if custom_tickers:
            existing = set(base["Ticker"])
            additions = pd.DataFrame(
                {
                    "Ticker": [ticker for ticker in custom_tickers if ticker not in existing],
                    "Security Name": [ticker for ticker in custom_tickers if ticker not in existing],
                    "Exchange": "Custom",
                    "Listing Group": "Custom",
                    "Is ETF": False,
                    "Test Issue": False,
                    "Is Stock": True,
                    "Index Membership": "",
                }
            )
            base = pd.concat([additions, base], ignore_index=True)

    base = base.drop_duplicates("Ticker").sort_values("Ticker").reset_index(drop=True)
    if len(base) <= max_symbols:
        return base.reset_index(drop=True)
    if scan_strategy == "Random sample":
        return base.sample(n=max_symbols, random_state=random_seed).sort_values("Ticker").reset_index(drop=True)
    if scan_strategy == "Ticker A-Z":
        return base.head(max_symbols).reset_index(drop=True)
    return spread_sample_frame(base, max_symbols)


def parse_feed_lines(raw_value: str) -> tuple[tuple[str, str], ...]:
    feeds: list[tuple[str, str]] = []
    seen = set()
    for line in raw_value.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if "|" in candidate:
            name, url = [part.strip() for part in candidate.split("|", 1)]
        else:
            url = candidate
            parsed = urlparse(url)
            name = parsed.netloc.replace("www.", "") or "RSS feed"
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        key = url.lower()
        if key not in seen:
            feeds.append((name or parsed.netloc, url))
            seen.add(key)
    return tuple(feeds)


def add_ticker_feeds(
    feeds: Iterable[tuple[str, str]],
    tickers: Iterable[str],
    enabled: bool,
) -> tuple[tuple[str, str], ...]:
    feed_list = list(feeds)
    if enabled:
        for ticker in list(tickers)[:15]:
            feed_list.append(
                (
                    f"Yahoo {ticker}",
                    f"https://finance.yahoo.com/rss/headline?s={ticker}",
                )
            )
    return tuple(feed_list)


def default_social_feed_text() -> str:
    return "\n".join(f"{name} | {url}" for name, url in DEFAULT_SOCIAL_FEEDS)


def sentiment_for(text: str) -> tuple[str, float]:
    words = re.findall(r"[a-z][a-z-]+", text.lower())
    if not words:
        return "Neutral", 0.0
    counts = Counter(words)
    positive = sum(counts[word] for word in POSITIVE_TERMS)
    negative = sum(counts[word] for word in NEGATIVE_TERMS)
    score = (positive - negative) / math.sqrt(max(len(words), 1))
    if score >= 0.22:
        return "Bullish", score
    if score <= -0.22:
        return "Bearish", score
    return "Neutral", score


def mentions_for(text: str, tickers: Iterable[str]) -> tuple[str, ...]:
    upper_text = text.upper()
    mentions = []
    for ticker in tickers:
        escaped = re.escape(ticker)
        pattern = rf"(?<![A-Z0-9.])\$?{escaped}(?![A-Z0-9.])"
        if re.search(pattern, upper_text):
            mentions.append(ticker)
    return tuple(mentions)


def macro_scores_for(text: str) -> tuple[float, Counter[str]]:
    lowered = text.lower()
    factors: Counter[str] = Counter()
    total = 0.0
    for factor, terms in MACRO_FACTOR_TERMS.items():
        for term, weight in terms.items():
            if term in lowered:
                factors[factor] += weight
                total += weight
    for term in VOLATILITY_TERMS:
        if term in lowered:
            total += 1.25
    return total, factors


def parse_datetime_text(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = parsedate_to_datetime(str(value).strip())
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    try:
        parsed_ts = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed_ts):
            return None
        return parsed_ts.to_pydatetime()
    except Exception:
        return None


def parsed_datetime(entry: dict) -> datetime | None:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        try:
            return datetime.fromtimestamp(calendar.timegm(struct_time), tz=timezone.utc)
        except (OverflowError, TypeError, ValueError):
            pass
    for key in ("published", "updated", "pubDate", "dc_date"):
        parsed = parse_datetime_text(entry.get(key))
        if parsed:
            return parsed
    return None


def xml_local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def xml_child_text(parent: ET.Element, names: tuple[str, ...]) -> str:
    wanted = {name.lower() for name in names}
    for child in list(parent):
        if xml_local_name(child.tag) in wanted and child.text:
            return clean_text(child.text)
    return ""


def xml_entry_link(entry: ET.Element) -> str:
    for child in list(entry):
        if xml_local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href
        if child.text:
            return clean_text(child.text)
    return ""


def parse_feed_content(content: bytes) -> tuple[list[dict], bool, str]:
    if feedparser is not None:
        parsed = feedparser.parse(content)
        return list(parsed.entries), bool(parsed.bozo and not parsed.entries), str(getattr(parsed, "bozo_exception", ""))
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        return [], True, str(exc)
    entries: list[dict] = []
    for node in root.iter():
        node_type = xml_local_name(node.tag)
        if node_type not in {"item", "entry"}:
            continue
        summary = xml_child_text(node, ("summary", "description", "subtitle", "content"))
        date_text = xml_child_text(node, ("published", "updated", "pubDate", "date"))
        entries.append(
            {
                "title": xml_child_text(node, ("title",)),
                "link": xml_entry_link(node),
                "summary": summary,
                "description": summary,
                "published": date_text,
                "updated": date_text,
                "content": [{"value": summary}],
            }
        )
    return entries, False, "feedparser unavailable; used built-in XML parser"


def format_age(value: datetime | None) -> str:
    if not value:
        return "Unknown"
    delta = datetime.now(timezone.utc) - value
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        minutes = max(seconds // 60, 1)
        return f"{minutes}m ago"
    if seconds < 86_400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86_400}d ago"


def parse_relative_age(value: object, now: datetime | None = None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([mhdw])(?:in(?:ute)?s?|ours?|ays?|eeks?)?\s*ago", text)
    if match:
        amount = float(match.group(1))
        unit = match.group(2)
        current = now or datetime.now(timezone.utc)
        if unit == "m":
            return current - timedelta(minutes=amount)
        if unit == "h":
            return current - timedelta(hours=amount)
        if unit == "d":
            return current - timedelta(days=amount)
        if unit == "w":
            return current - timedelta(weeks=amount)
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if not pd.isna(parsed):
        return parsed.to_pydatetime()
    return None


def article_timestamp(article: Article) -> float | None:
    if article.published:
        return article.published.timestamp()
    parsed = parse_relative_age(getattr(article, "age", None))
    return parsed.timestamp() if parsed else None


def sort_articles_by_recent(articles: Iterable[Article]) -> list[Article]:
    return sorted(
        articles,
        key=lambda article: (
            article_timestamp(article) is None,
            -(article_timestamp(article) or 0),
            article.source,
            article.title,
        ),
    )


def clean_headline_summary(title: str, summary: str, max_chars: int = 180) -> str:
    raw_summary = html.unescape(str(summary or ""))
    if re.search(r"\b(ticker-row|factor-chip|news-card|metric-cell|card-topline)\b", raw_summary, flags=re.IGNORECASE):
        return ""
    cleaned_title = clean_text(title).casefold()
    cleaned_summary = clean_text(raw_summary)
    if not cleaned_summary:
        return ""
    lowered = cleaned_summary.casefold()
    if lowered == cleaned_title or cleaned_title in lowered and len(cleaned_summary) <= len(clean_text(title)) + 24:
        return ""
    if re.search(r"\b(class|span|div|href|ticker-row|factor-chip|news-card)\b", lowered) and "<" in raw_summary:
        return ""
    if re.search(r"\b(ticker-row|factor-chip|news-card|metric-cell)\b", lowered):
        return ""
    if len(cleaned_summary) > max_chars:
        return cleaned_summary[: max_chars - 3].rstrip() + "..."
    return cleaned_summary


def classify_headline(article: Article) -> tuple[str, ...]:
    categories = [canonical_macro_category(factor) for factor in article.macro_factors]
    if article.mentions:
        categories.append("Company / Stock")
    text = f"{article.title} {article.summary}".lower()
    if any(term in text for term in ("market", "stocks", "wall street", "s&p", "nasdaq", "dow", "russell")):
        categories.append("Market")
    if not categories:
        categories.append("Market")
    seen = []
    for category in categories:
        if category not in seen:
            seen.append(category)
    return tuple(seen)


def headline_is_relevant(article: Article, tickers: Sequence[str] = ()) -> bool:
    text = clean_text(f"{article.title} {article.summary}").lower()
    if not text:
        return False
    if any(term in text for term in LOW_QUALITY_HEADLINE_TERMS):
        return False
    source = article.source.strip()
    selected_mentions = set(article.mentions).intersection(set(tickers))
    has_market_term = any(term in text for term in MARKET_HEADLINE_RELEVANCE_TERMS)
    has_macro_or_ticker = article.macro_score > 0 or bool(selected_mentions)
    if source == "Yahoo Finance":
        return has_macro_or_ticker or has_market_term
    if source in OFFICIAL_OR_MARKET_SOURCES:
        return True
    return has_macro_or_ticker or has_market_term


def filter_source_quality(articles: Iterable[Article], tickers: Sequence[str] = ()) -> tuple[list[Article], int]:
    kept = []
    removed = 0
    for article in articles:
        if headline_is_relevant(article, tickers):
            kept.append(article)
        else:
            removed += 1
    return sort_articles_by_recent(kept), removed


@st.cache_data(ttl=600, show_spinner=False)
def fetch_market_macro_headlines(
    feeds: tuple[tuple[str, str], ...] = MARKET_MACRO_FEEDS,
    tickers: tuple[str, ...] = (),
) -> tuple[list[Article], list[dict], datetime, dict[str, object]]:
    raw_articles, statuses = fetch_feeds(feeds, tickers)
    quality_articles, filtered_out = filter_source_quality(raw_articles, tickers)
    stats = {
        "raw_count": len(raw_articles),
        "filtered_out": filtered_out,
        "kept_count": len(quality_articles),
        "sources": sorted({article.source for article in quality_articles}),
    }
    return quality_articles, statuses, eastern_now(), stats


def request_feed(source: str, url: str, tickers: tuple[str, ...]) -> tuple[list[Article], dict]:
    status = {
        "source": source,
        "url": url,
        "status": "OK",
        "articles": 0,
        "message": "",
    }
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "volatility-radar/1.0 (+https://streamlit.io)",
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status["status"] = "Error"
        status["message"] = str(exc)
        return [], status

    entries, parse_error, parse_message = parse_feed_content(response.content)
    if parse_error and not entries:
        status["status"] = "Error"
        status["message"] = parse_message
        return [], status
    if parse_message and feedparser is None:
        status["message"] = parse_message

    articles: list[Article] = []
    for entry in entries:
        title = clean_text(entry.get("title"))
        link = entry.get("link", "")
        raw_summary = (
            entry.get("summary")
            or entry.get("description")
            or entry.get("subtitle")
            or ""
        )
        summary = clean_headline_summary(title, raw_summary, 240)
        if not title:
            continue
        combined = f"{title} {summary}"
        sentiment, score = sentiment_for(combined)
        macro_score, factors = macro_scores_for(combined)
        articles.append(
            Article(
                title=title,
                link=link,
                summary=summary,
                source=source,
                published=parsed_datetime(entry),
                sentiment=sentiment,
                sentiment_score=score,
                mentions=mentions_for(combined, tickers),
                macro_score=macro_score,
                macro_factors=tuple(factor for factor, value in factors.items() if value > 0),
            )
        )

    status["articles"] = len(articles)
    return articles, status


@st.cache_data(ttl=600, show_spinner=False)
def fetch_feeds(
    feeds: tuple[tuple[str, str], ...],
    tickers: tuple[str, ...],
) -> tuple[list[Article], list[dict]]:
    articles: list[Article] = []
    statuses: list[dict] = []
    if not feeds:
        return articles, statuses

    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as executor:
        futures = {
            executor.submit(request_feed, source, url, tickers): (source, url)
            for source, url in feeds
        }
        for future in as_completed(futures):
            feed_articles, feed_status = future.result()
            articles.extend(feed_articles)
            statuses.append(feed_status)

    deduped: dict[str, Article] = {}
    for article in articles:
        key = (article.link or f"{article.source}:{article.title}").lower()
        if key not in deduped:
            deduped[key] = article

    ordered = sort_articles_by_recent(deduped.values())
    statuses.sort(key=lambda item: item["source"])
    return ordered, statuses


def social_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    if isinstance(parsed, pd.Timestamp):
        return parsed.to_pydatetime()
    return None


def social_sentiment_for(text: str, declared: str | None = None) -> tuple[str, float]:
    if declared:
        normalized = declared.strip().lower()
        if normalized == "bullish":
            return "Bullish", 0.55
        if normalized == "bearish":
            return "Bearish", -0.55
    return sentiment_for(text)


def request_social_feed(
    source: str,
    url: str,
    tickers: tuple[str, ...],
) -> tuple[list[SocialMention], dict]:
    status = {
        "source": source,
        "url": url,
        "status": "OK",
        "mentions": 0,
        "message": "",
    }
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "volatility-radar-social/1.0 (+https://streamlit.io)",
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status["status"] = "Error"
        status["message"] = str(exc)
        return [], status

    entries, parse_error, parse_message = parse_feed_content(response.content)
    if parse_error and not entries:
        status["status"] = "Error"
        status["message"] = parse_message
        return [], status
    if parse_message and feedparser is None:
        status["message"] = parse_message

    mentions: list[SocialMention] = []
    for entry in entries:
        title = clean_text(entry.get("title"))
        content_value = ""
        if entry.get("content"):
            content_value = entry.get("content", [{}])[0].get("value", "")
        body = clean_text(entry.get("summary") or entry.get("description") or content_value)
        combined = f"{title} {body}"
        mentioned = mentions_for(combined, tickers)
        if not title or not mentioned:
            continue
        sentiment, score = sentiment_for(combined)
        mentions.append(
            SocialMention(
                title=title,
                body=body,
                link=entry.get("link", ""),
                source=source,
                published=parsed_datetime(entry),
                sentiment=sentiment,
                sentiment_score=score,
                mentions=mentioned,
                engagement=0,
            )
        )

    status["mentions"] = len(mentions)
    return mentions, status


def request_stocktwits_stream(ticker: str) -> tuple[list[SocialMention], dict]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    status = {
        "source": f"Stocktwits {ticker}",
        "url": url,
        "status": "OK",
        "mentions": 0,
        "message": "",
    }
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "volatility-radar-social/1.0 (+https://streamlit.io)"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        status["status"] = "Error"
        status["message"] = str(exc)
        return [], status

    mentions: list[SocialMention] = []
    for message in payload.get("messages", [])[:30]:
        body = clean_text(message.get("body", ""))
        if not body:
            continue
        declared = None
        entities = message.get("entities") or {}
        sentiment_payload = entities.get("sentiment") or {}
        if isinstance(sentiment_payload, dict):
            declared = sentiment_payload.get("basic")
        sentiment, score = social_sentiment_for(body, declared)
        user = message.get("user") or {}
        username = user.get("username", "Stocktwits")
        likes = message.get("likes") or {}
        engagement = int(likes.get("total", 0) or 0)
        mentions.append(
            SocialMention(
                title=f"{username} on {ticker}",
                body=body,
                link=f"https://stocktwits.com/symbol/{ticker}",
                source="Stocktwits",
                published=social_datetime(message.get("created_at")),
                sentiment=sentiment,
                sentiment_score=score,
                mentions=(ticker,),
                engagement=engagement,
            )
        )

    status["mentions"] = len(mentions)
    return mentions, status


@st.cache_data(ttl=600, show_spinner=False)
def fetch_social_mentions(
    feeds: tuple[tuple[str, str], ...],
    tickers: tuple[str, ...],
    enabled: bool,
    include_stocktwits: bool,
    max_stocktwits_symbols: int,
) -> tuple[list[SocialMention], list[dict]]:
    if not enabled or not tickers:
        return [], []

    mentions: list[SocialMention] = []
    statuses: list[dict] = []
    work_count = len(feeds) + (min(len(tickers), max_stocktwits_symbols) if include_stocktwits else 0)
    if work_count <= 0:
        return mentions, statuses

    with ThreadPoolExecutor(max_workers=min(8, work_count)) as executor:
        futures = {
            executor.submit(request_social_feed, source, url, tickers): source
            for source, url in feeds
        }
        if include_stocktwits:
            for ticker in list(tickers)[:max_stocktwits_symbols]:
                futures[executor.submit(request_stocktwits_stream, ticker)] = f"Stocktwits {ticker}"

        for future in as_completed(futures):
            try:
                fetched_mentions, status = future.result()
            except Exception as exc:
                status = {
                    "source": futures[future],
                    "url": "",
                    "status": "Error",
                    "mentions": 0,
                    "message": str(exc),
                }
                fetched_mentions = []
            mentions.extend(fetched_mentions)
            statuses.append(status)

    deduped: dict[str, SocialMention] = {}
    for mention in mentions:
        key = (mention.link or f"{mention.source}:{mention.title}:{mention.body[:80]}").lower()
        if key not in deduped:
            deduped[key] = mention

    ordered = sort_social_mentions_by_reactions(deduped.values())
    statuses.sort(key=lambda item: item["source"])
    return ordered, statuses


def social_mentions_to_frame(mentions: Iterable[SocialMention]) -> pd.DataFrame:
    rows = []
    for mention in mentions:
        rows.append(
            {
                "Title": mention.title,
                "Source": mention.source,
                "Published": mention.published,
                "Age": format_age(mention.published),
                "Sentiment": mention.sentiment,
                "Sentiment Score": mention.sentiment_score,
                "Tickers": ", ".join(mention.mentions),
                "Total Engagement": get_total_reactions(mention),
                "Link": mention.link,
            }
        )
    return pd.DataFrame(rows)


def articles_to_frame(articles: Iterable[Article]) -> pd.DataFrame:
    rows = []
    for article in articles:
        rows.append(
            {
                "Title": article.title,
                "Source": article.source,
                "Published": article.published,
                "Age": format_age(article.published),
                "Sentiment": article.sentiment,
                "Sentiment Score": article.sentiment_score,
                "Tickers": ", ".join(article.mentions),
                "Macro Score": article.macro_score,
                "Macro Factors": ", ".join(article.macro_factors),
                "Link": article.link,
            }
        )
    return pd.DataFrame(rows)


def coerce_float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_numeric_value(value: object) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "na", "none", "null", "undefined", "--"}:
        return None
    cleaned = (
        text.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("+/-", "")
        .replace("+-", "")
        .strip()
    )
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_percent_value(value: object) -> float | None:
    return parse_numeric_value(value)


def sort_descending_by_metric(
    frame: pd.DataFrame,
    metric_column: str,
    tie_columns: tuple[str, ...] = ("Ticker", "Company"),
) -> pd.DataFrame:
    if frame.empty or metric_column not in frame:
        return frame
    sortable = frame.copy()
    metric_values = sortable[metric_column].map(parse_numeric_value)
    sortable["__metric_missing"] = metric_values.isna()
    sortable["__metric_value"] = metric_values.fillna(float("-inf"))
    sort_columns = ["__metric_missing", "__metric_value"]
    ascending = [True, False]
    for column in tie_columns:
        if column in sortable:
            sort_columns.append(column)
            ascending.append(True)
    return (
        sortable.sort_values(sort_columns, ascending=ascending, kind="mergesort")
        .drop(columns=["__metric_missing", "__metric_value"])
        .reset_index(drop=True)
    )


def forecast_rank_metric(frame: pd.DataFrame) -> str:
    if "Options Move %" in frame:
        options_values = frame["Options Move %"].map(parse_percent_value)
        if options_values.notna().any():
            return "Options Move %"
    return "Projected Move %"


FORECAST_SORT_MODES = {
    "Option Move %": ("Options Move %", "Projected Move %"),
    "IV Rank / IV Percentile": ("Options IV %", "30D Options IV %"),
    "ATR %": ("ATR Move %",),
    "Volume Spike": ("Volume Shock",),
    "Social Engagement": ("Social Engagement", "Social Risk", "Social Mentions"),
}


def sort_metric_for_mode(frame: pd.DataFrame, sort_mode: str) -> str:
    if sort_mode == "Ticker A-Z":
        return "Ticker"
    for column in FORECAST_SORT_MODES.get(sort_mode, ()):
        if column in frame and frame[column].map(parse_numeric_value).notna().any():
            return column
    return forecast_rank_metric(frame)


def sort_forecast_for_mode(frame: pd.DataFrame, sort_mode: str) -> pd.DataFrame:
    if frame.empty:
        return frame.reindex(columns=FORECAST_COLUMNS)
    if sort_mode == "Ticker A-Z":
        sorted_frame = frame.sort_values(["Ticker", "Company"], ascending=[True, True], kind="mergesort").reset_index(drop=True)
        if "Rank" in sorted_frame:
            sorted_frame["Rank"] = range(1, len(sorted_frame) + 1)
        else:
            sorted_frame.insert(0, "Rank", range(1, len(sorted_frame) + 1))
        return sorted_frame.reindex(columns=FORECAST_COLUMNS)
    metric = sort_metric_for_mode(frame, sort_mode)
    return rank_rows_by_metric(frame, metric).reindex(columns=FORECAST_COLUMNS)


def rank_rows_by_metric(frame: pd.DataFrame, metric_column: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    ranked = sort_descending_by_metric(frame, metric_column)
    if "Rank" in ranked:
        ranked["Rank"] = range(1, len(ranked) + 1)
    else:
        ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked


def rank_forecast_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.reindex(columns=FORECAST_COLUMNS)
    metric = forecast_rank_metric(frame)
    ranked = rank_rows_by_metric(frame, metric)
    return ranked.reindex(columns=FORECAST_COLUMNS)


def get_total_reactions(item: object) -> int:
    if isinstance(item, SocialMention):
        return int(max(parse_numeric_value(item.engagement) or 0, 0))
    if isinstance(item, dict):
        for field in ("total_reactions", "reaction_count", "reactions", "engagement", "total_engagement"):
            value = item.get(field)
            if isinstance(value, dict):
                value = value.get("total")
            parsed = parse_numeric_value(value)
            if parsed is not None:
                return int(max(parsed, 0))
        fields = (
            "likes",
            "comments",
            "shares",
            "reposts",
            "retweets",
            "replies",
            "upvotes",
            "favorites",
        )
        total = 0.0
        for field in fields:
            value = item.get(field)
            if isinstance(value, dict):
                value = value.get("total")
            total += max(parse_numeric_value(value) or 0, 0)
        return int(total)
    return int(max(parse_numeric_value(getattr(item, "engagement", 0)) or 0, 0))


def sort_social_mentions_by_reactions(mentions: Iterable[SocialMention]) -> list[SocialMention]:
    return sorted(
        mentions,
        key=lambda mention: (
            -get_total_reactions(mention),
            -(mention.published.timestamp() if mention.published else 0),
            mention.source,
            mention.title,
        ),
    )


def sort_articles_by_relevance(articles: Iterable[Article]) -> list[Article]:
    return sorted(
        articles,
        key=lambda article: (
            -parse_numeric_value(article.macro_score or 0),
            -len(article.mentions),
            -abs(parse_numeric_value(article.sentiment_score) or 0),
            -(article.published.timestamp() if article.published else 0),
            article.source,
            article.title,
        ),
    )


def article_categories(article: Article) -> tuple[str, ...]:
    return classify_headline(article)


def article_in_time_range(article: Article, date_range: str) -> bool:
    if date_range == "All":
        return True
    timestamp = article.published
    if timestamp is None:
        return False
    now = datetime.now(timezone.utc)
    age = now - timestamp
    if date_range == "Today":
        return timestamp.astimezone(ZoneInfo("America/New_York")).date() == eastern_now().date()
    if date_range == "This Week":
        return age <= timedelta(days=7)
    if date_range == "Last 30 Days":
        return age <= timedelta(days=30)
    return True


def filter_articles(
    articles: Iterable[Article],
    sources: Sequence[str],
    categories: Sequence[str],
    sentiments: Sequence[str],
    date_range: str,
    keyword: str = "",
) -> list[Article]:
    filtered = []
    source_set = set(sources)
    category_set = set(categories)
    sentiment_set = set(sentiments)
    keyword_clean = clean_text(keyword).casefold()
    for article in articles:
        if source_set and article.source not in source_set:
            continue
        if category_set and not category_set.intersection(article_categories(article)):
            continue
        if sentiment_set and article.sentiment not in sentiment_set:
            continue
        if not article_in_time_range(article, date_range):
            continue
        if keyword_clean:
            haystack = clean_text(
                f"{article.title} {article.summary} {article.source} {' '.join(article.mentions)} {' '.join(article_categories(article))}"
            ).casefold()
            if keyword_clean not in haystack:
                continue
        filtered.append(article)
    return sort_articles_by_recent(filtered)


def article_timestamp_bounds(articles: Iterable[Article]) -> tuple[str, str]:
    timestamps = [article.published for article in articles if article.published]
    if not timestamps:
        return "N/A", "N/A"
    newest = max(timestamps)
    oldest = min(timestamps)
    return (
        newest.strftime("%Y-%m-%d %I:%M %p UTC").lstrip("0"),
        oldest.strftime("%Y-%m-%d %I:%M %p UTC").lstrip("0"),
    )


def sort_status_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    severity = {"Error": 0, "Warning": 1, "OK": 2}
    sortable = frame.copy()
    if "Status" in sortable:
        sortable["__status_rank"] = sortable["Status"].map(severity).fillna(3)
    elif "status" in sortable:
        sortable["__status_rank"] = sortable["status"].map(severity).fillna(3)
    else:
        sortable["__status_rank"] = 3
    if "History Bars" in sortable:
        sortable["__bars"] = pd.to_numeric(sortable["History Bars"], errors="coerce").fillna(0)
    else:
        sortable["__bars"] = 0
    sort_columns = ["__status_rank", "__bars"]
    ascending = [True, True]
    for column in ("source", "Ticker", "Exchange"):
        if column in sortable:
            sort_columns.append(column)
            ascending.append(True)
    return (
        sortable.sort_values(sort_columns, ascending=ascending, kind="mergesort")
        .drop(columns=["__status_rank", "__bars"])
        .reset_index(drop=True)
    )


def compact_number(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    number = float(value)
    absolute = abs(number)
    if absolute >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:.0f}"


def format_currency(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    number = float(value)
    sign = "-" if number < 0 else ""
    return f"{sign}${abs(number):,.{decimals}f}"


def format_compact_currency(value: float | int | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    number = float(value)
    sign = "-" if number < 0 else ""
    absolute = abs(number)
    units = (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )
    for divisor, suffix in units:
        if absolute >= divisor:
            return f"{sign}${absolute / divisor:,.{decimals}f}{suffix}"
    return f"{sign}${absolute:,.0f}"


def format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def format_move(value: float | int | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"+/-{float(value):,.{decimals}f}%"


def format_percent(value: float | int | None, decimals: int = 1, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    prefix = "+" if signed and float(value) > 0 else ""
    return f"{prefix}{float(value):,.{decimals}f}%"


def market_cap_bucket(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "Unknown market cap"
    number = float(value)
    for label, (low, high) in MARKET_CAP_BUCKETS.items():
        if label == "Unknown market cap":
            continue
        lower_ok = low is None or number >= low
        upper_ok = high is None or number < high
        if lower_ok and upper_ok:
            return label
    return "Unknown market cap"


def normalize_statement_label(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def clean_statement_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    cleaned = frame.copy()
    cleaned.index = cleaned.index.map(str)
    try:
        cleaned.columns = pd.to_datetime(cleaned.columns, errors="coerce")
        cleaned = cleaned.loc[:, ~pd.isna(cleaned.columns)]
        cleaned = cleaned.sort_index(axis=1)
    except Exception:
        pass
    return cleaned.apply(pd.to_numeric, errors="coerce")


def statement_series(frame: pd.DataFrame, labels: Iterable[str]) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    lookup = {normalize_statement_label(index): index for index in frame.index}
    for label in labels:
        match = lookup.get(normalize_statement_label(label))
        if match is not None:
            series = pd.to_numeric(frame.loc[match], errors="coerce").dropna()
            try:
                series.index = pd.to_datetime(series.index, errors="coerce")
                series = series[~pd.isna(series.index)].sort_index()
            except Exception:
                pass
            return series
    return pd.Series(dtype=float)


def latest_value(series: pd.Series) -> float | None:
    if series.empty:
        return None
    value = coerce_float(series.dropna().iloc[-1])
    return value


def latest_growth(series: pd.Series) -> float | None:
    clean = series.dropna()
    if len(clean) < 2:
        return None
    previous = coerce_float(clean.iloc[-2])
    current = coerce_float(clean.iloc[-1])
    if previous is None or current is None or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


def safe_ratio(numerator: float | int | None, denominator: float | int | None, multiplier: float = 1.0) -> float | None:
    if numerator is None or denominator is None or pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator) * multiplier


def period_label(value: object, quarterly: bool) -> str:
    try:
        timestamp = pd.Timestamp(value)
        if quarterly:
            return f"{timestamp.year} Q{timestamp.quarter}"
        return str(timestamp.year)
    except Exception:
        return str(value)


def format_financial_table(
    frame: pd.DataFrame,
    currency_columns: Iterable[str] = (),
    percent_columns: Iterable[str] = (),
    number_columns: Iterable[str] = (),
    date_columns: Iterable[str] = (),
) -> pd.DataFrame:
    display = frame.copy()
    for column in currency_columns:
        if column in display:
            display[column] = display[column].map(lambda value: format_currency(value, 0))
    for column in percent_columns:
        if column in display:
            display[column] = display[column].map(lambda value: format_percent(value, 1))
    for column in number_columns:
        if column in display:
            display[column] = display[column].map(lambda value: format_number(value, 2))
    for column in date_columns:
        if column in display:
            display[column] = pd.to_datetime(display[column], errors="coerce").dt.strftime("%Y-%m-%d")
            display[column] = display[column].fillna("N/A")
    return display.fillna("N/A")


def format_statement_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    display = frame.copy()
    display.columns = [
        pd.Timestamp(column).strftime("%Y-%m-%d")
        if isinstance(column, (pd.Timestamp, datetime, date))
        else str(column)
        for column in display.columns
    ]
    for column in display.columns:
        display[column] = display[column].map(lambda value: format_currency(value, 0))
    return display


def table_height_for_rows(frame: pd.DataFrame, min_height: int = 130, max_height: int = 420) -> int:
    return min(max_height, max(min_height, 42 + (len(frame) + 1) * 35))


def parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, (tuple, list, set)):
        for item in value:
            parsed = parse_date(item)
            if parsed:
                return parsed
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    parsed_ts = pd.to_datetime(value, errors="coerce", utc=False)
    if pd.isna(parsed_ts):
        return None
    if isinstance(parsed_ts, pd.Timestamp):
        return parsed_ts.date()
    return None


def impact_to_importance(impact: str) -> int:
    return {"High": 5, "Medium": 3, "Low": 1}.get(impact, 3)


def classify_macro_release(name: str, source: str = "") -> tuple[str, str, int, str]:
    text = f"{name} {source}".lower()
    if any(term in text for term in ("fomc", "federal open market", "fed minutes", "rate decision")):
        return "Fed", "High", 5, "Fed"
    if any(term in text for term in ("cpi", "consumer price", "ppi", "producer price", "pce", "personal consumption expenditures")):
        return "Inflation", "High", 5, "Rates & Inflation"
    if any(term in text for term in ("employment situation", "nonfarm", "payroll", "unemployment", "wage", "jobless claims", "hourly earnings")):
        impact = "High" if "jobless" not in text else "Medium"
        return "Labor", impact, impact_to_importance(impact), "Growth & Housing"
    if any(term in text for term in ("gdp", "gross domestic product", "durable goods", "trade", "business inventories")):
        return "Growth", "High", 5, "Growth & Housing"
    if any(term in text for term in ("retail sales", "consumer confidence", "personal income", "personal spending", "personal outlays")):
        return "Consumer", "High", 5, "Growth & Housing"
    if any(term in text for term in ("housing", "new home", "construction")):
        return "Housing", "Medium", 3, "Growth & Housing"
    if any(term in text for term in ("ism", "pmi", "manufacturing", "services")):
        return "Growth", "Medium", 3, "Growth & Housing"
    if any(term in text for term in ("treasury", "auction", "yield", "bill", "note", "bond")):
        return "Rates", "Medium", 3, "Rates & Inflation"
    if any(term in text for term in ("eia", "petroleum", "crude", "oil", "natural gas", "inventory")):
        return "Energy", "Medium", 3, "Geopolitics & Policy"
    return "Macro", "Low", 1, "Scheduled Reports"


def normalize_event_datetime(value: datetime | date | None, default_time: tuple[int, int] = (8, 30)) -> datetime | None:
    if value is None:
        return None
    tz = ZoneInfo("America/New_York")
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(tz)
        return value.replace(tzinfo=tz)
    return datetime(value.year, value.month, value.day, default_time[0], default_time[1], tzinfo=tz)


def parse_release_datetime(date_text: object, time_text: object = "", default_time: tuple[int, int] = (8, 30)) -> datetime | None:
    text = clean_text(f"{date_text or ''} {time_text or ''}")
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        parsed_date = parse_date(date_text)
        return normalize_event_datetime(parsed_date, default_time)
    if isinstance(parsed, pd.Timestamp):
        timestamp = parsed.to_pydatetime()
        if timestamp.hour == 0 and timestamp.minute == 0 and not re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", text, re.I):
            timestamp = timestamp.replace(hour=default_time[0], minute=default_time[1])
        return normalize_event_datetime(timestamp, default_time)
    return None


def release_time_text(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%I:%M %p ET").lstrip("0")


def make_macro_event(
    name: str,
    event_dt: datetime | date | None,
    source: str,
    source_url: str = "",
    notes: str = "",
    category: str | None = None,
    impact: str | None = None,
    previous: str = "N/A",
    forecast: str = "N/A",
    actual: str = "N/A",
    last_updated: datetime | None = None,
) -> MacroEvent:
    event_datetime = normalize_event_datetime(event_dt)
    category_value, impact_value, importance, factor = classify_macro_release(name, source)
    if category:
        category_value = category
    if impact:
        impact_value = impact
        importance = impact_to_importance(impact)
    today = eastern_now().date()
    event_date = event_datetime.date() if event_datetime else parse_date(event_dt)
    days_until = (event_date - today).days if event_date else None
    return MacroEvent(
        event_date=event_date,
        name=clean_text(name),
        importance=importance,
        notes=notes,
        days_until=days_until,
        in_horizon=days_until is not None and days_until >= 0,
        factor=factor,
        event_datetime=event_datetime,
        release_time=release_time_text(event_datetime),
        source=source,
        category=category_value,
        impact=impact_value,
        previous=previous or "N/A",
        forecast=forecast or "N/A",
        actual=actual or "N/A",
        last_updated=last_updated or eastern_now(),
        source_url=source_url,
    )


def important_release_name(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ECONOMIC_RELEASE_KEYWORDS)


def parse_macro_events(raw_value: str, horizon_days: int) -> tuple[MacroEvent, ...]:
    events: list[MacroEvent] = []
    for line in raw_value.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = [part.strip() for part in text.split("|")]
        event_dt = parse_release_datetime(parts[0]) if parts else None
        name = parts[1] if len(parts) > 1 else text
        impact = "Medium"
        if len(parts) > 2:
            try:
                importance = max(1, min(5, int(float(parts[2]))))
                impact = "High" if importance >= 5 else "Medium" if importance >= 3 else "Low"
            except ValueError:
                normalized = parts[2].strip().title()
                impact = normalized if normalized in {"High", "Medium", "Low"} else "Medium"
        notes = parts[3] if len(parts) > 3 else ""
        event = make_macro_event(
            name=name,
            event_dt=event_dt,
            source="User scheduled event",
            notes=notes,
            impact=impact,
        )
        if event.days_until is not None and 0 <= event.days_until <= max(horizon_days, 1) * 12:
            events.append(event)
    return tuple(events)


def unfold_ics_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and lines:
            lines[-1] += raw_line.strip()
        else:
            lines.append(raw_line.strip())
    return lines


def parse_ics_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    formats = ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d")
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if fmt == "%Y%m%d":
                parsed = parsed.replace(hour=8, minute=30)
            if cleaned.endswith("Z"):
                parsed = parsed.replace(tzinfo=timezone.utc)
            return normalize_event_datetime(parsed)
        except ValueError:
            continue
    return None


def parse_ics_events(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in unfold_ics_lines(text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current:
                events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.split(";", 1)[0].upper()] = html.unescape(value.replace("\\,", ","))
    return events


def economic_source_status(source: str, status: str, rows: int, message: str = "") -> dict:
    return {
        "source": source,
        "status": status,
        "rows": rows,
        "message": message,
        "last_updated": eastern_now(),
    }


def add_event_if_relevant(
    events: list[MacroEvent],
    name: str,
    event_dt: datetime | date | None,
    source: str,
    source_url: str,
    lookahead_days: int,
    notes: str = "",
    category: str | None = None,
    impact: str | None = None,
) -> None:
    if not name or not event_dt or not important_release_name(name):
        return
    event = make_macro_event(
        name,
        event_dt,
        source,
        source_url=source_url,
        notes=notes,
        category=category,
        impact=impact,
    )
    if event.days_until is None or event.days_until < 0 or event.days_until > lookahead_days:
        return
    events.append(event)


def fetch_bls_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "BLS"
    url = ECONOMIC_CALENDAR_SOURCES[source]
    text, raw_status = request_text(url, source)
    if raw_status["status"] != "OK":
        return [], economic_source_status(source, "Error", 0, raw_status.get("message", "Unable to fetch BLS calendar"))
    events: list[MacroEvent] = []
    for item in parse_ics_events(text):
        name = clean_text(item.get("SUMMARY", ""))
        event_dt = parse_ics_datetime(item.get("DTSTART", ""))
        add_event_if_relevant(events, name, event_dt, source, url, lookahead_days)
    return events, economic_source_status(source, "OK", len(events))


def fetch_bea_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "BEA"
    url = ECONOMIC_CALENDAR_SOURCES[source]
    text, raw_status = request_text(url, source)
    if raw_status["status"] != "OK":
        return [], economic_source_status(source, "Error", 0, raw_status.get("message", "Unable to fetch BEA schedule"))
    events: list[MacroEvent] = []
    for table in parse_html_tables(text):
        for _, row in table.iterrows():
            values = [clean_text(str(value)) for value in row.tolist() if clean_text(str(value))]
            row_text = " | ".join(values)
            if not important_release_name(row_text):
                continue
            date_value = next((value for value in values if parse_release_datetime(value) is not None), "")
            event_dt = parse_release_datetime(date_value or row_text)
            name = values[-1] if values else row_text
            add_event_if_relevant(events, name, event_dt, source, url, lookahead_days)
    return events, economic_source_status(source, "OK", len(events))


def fetch_census_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "Census"
    url = ECONOMIC_CALENDAR_SOURCES[source]
    text, raw_status = request_text(url, source)
    if raw_status["status"] != "OK":
        return [], economic_source_status(source, "Error", 0, raw_status.get("message", "Unable to fetch Census calendar"))
    events: list[MacroEvent] = []
    for table in parse_html_tables(text):
        columns = {str(column).lower(): column for column in table.columns}
        for _, row in table.iterrows():
            row_text = " | ".join(clean_text(str(value)) for value in row.tolist())
            if not important_release_name(row_text):
                continue
            name = clean_text(
                row.get(columns.get("indicator", ""), "")
                or row.get(columns.get("release", ""), "")
                or row.get(columns.get("title", ""), "")
                or row_text
            )
            date_text = row.get(columns.get("release date", ""), "") or row.get(columns.get("date", ""), "")
            time_text = row.get(columns.get("time", ""), "")
            event_dt = parse_release_datetime(date_text, time_text)
            add_event_if_relevant(events, name, event_dt, source, url, lookahead_days)
    return events, economic_source_status(source, "OK", len(events))


def fetch_fomc_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "Federal Reserve"
    url = ECONOMIC_CALENDAR_SOURCES[source]
    text, raw_status = request_text(url, source)
    if raw_status["status"] != "OK":
        return [], economic_source_status(source, "Error", 0, raw_status.get("message", "Unable to fetch FOMC calendar"))
    cleaned = clean_text(text)
    current_year = eastern_now().year
    section_start = cleaned.find(f"{current_year} FOMC Meetings")
    section_end = -1
    if section_start >= 0:
        next_heading = re.search(r"\b\d{4} FOMC Meetings\b", cleaned[section_start + 1 :])
        if next_heading:
            section_end = section_start + 1 + next_heading.start()
    if section_start >= 0:
        cleaned = cleaned[section_start : section_end if section_end > section_start else len(cleaned)]
    cleaned = re.sub(r"Released\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}", "", cleaned, flags=re.IGNORECASE)
    events: list[MacroEvent] = []
    year = current_year
    month_regex = "|".join(calendar.month_name[1:])
    pattern = re.compile(rf"({month_regex})\s+(\d{{1,2}})(?:[\-–](\d{{1,2}}))?\*?", re.IGNORECASE)
    for match in pattern.finditer(cleaned):
        month_name, start_day, end_day = match.groups()
        month_number = list(calendar.month_name).index(month_name.title())
        day = int(end_day or start_day)
        meeting_dt = datetime(year, month_number, day, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        add_event_if_relevant(
            events,
            "FOMC rate decision",
            meeting_dt,
            source,
            url,
            lookahead_days,
            notes="Parsed from Federal Reserve FOMC calendar",
            category="Fed",
            impact="High",
        )
        minutes_dt = meeting_dt + timedelta(days=21)
        add_event_if_relevant(
            events,
            "FOMC meeting minutes",
            minutes_dt,
            source,
            url,
            lookahead_days,
            notes="Estimated three-week minutes timing from FOMC meeting date",
            category="Fed",
            impact="High",
        )
    return events, economic_source_status(source, "OK" if events else "Warning", len(events), "" if events else "No upcoming FOMC dates parsed")


def fetch_ism_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "ISM"
    url = ECONOMIC_CALENDAR_SOURCES[source]
    text, raw_status = request_text(url, source)
    if raw_status["status"] != "OK":
        return [], economic_source_status(source, "Error", 0, raw_status.get("message", "Unable to fetch ISM release schedule"))
    events: list[MacroEvent] = []
    for table in parse_html_tables(text):
        for _, row in table.iterrows():
            values = [clean_text(str(value)) for value in row.tolist() if clean_text(str(value))]
            row_text = " | ".join(values)
            lowered = row_text.lower()
            labels = []
            if "manufacturing" in lowered:
                labels.append("ISM Manufacturing PMI")
            if "services" in lowered or "service" in lowered:
                labels.append("ISM Services PMI")
            for label in labels:
                event_dt = parse_release_datetime(row_text, "10:00 AM")
                add_event_if_relevant(events, label, event_dt, source, url, lookahead_days, category="Growth", impact="Medium")
    return events, economic_source_status(source, "OK" if events else "Warning", len(events), "" if events else "No upcoming ISM dates parsed")


def recurring_weekday_events(
    name: str,
    source: str,
    source_url: str,
    weekday: int,
    hour: int,
    minute: int,
    lookahead_days: int,
    category: str,
    impact: str,
    interval_days: int = 7,
) -> list[MacroEvent]:
    now = eastern_now()
    days_ahead = (weekday - now.weekday()) % 7
    first = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if first <= now:
        first += timedelta(days=interval_days)
    events: list[MacroEvent] = []
    current = first
    while (current - now).days <= lookahead_days:
        events.append(
            make_macro_event(
                name,
                current,
                source,
                source_url=source_url,
                notes="Rule-based recurring schedule; source page checked separately when available.",
                category=category,
                impact=impact,
            )
        )
        current += timedelta(days=interval_days)
    return events


def adjust_to_business_day(day_value: date) -> date:
    adjusted = day_value
    while adjusted.weekday() >= 5:
        adjusted += timedelta(days=1)
    return adjusted


def first_business_day(year: int, month: int, offset: int = 0) -> date:
    day_value = date(year, month, 1)
    business_days = []
    while day_value.month == month:
        if day_value.weekday() < 5:
            business_days.append(day_value)
        day_value += timedelta(days=1)
    return business_days[min(offset, len(business_days) - 1)]


def first_weekday(year: int, month: int, weekday: int) -> date:
    day_value = date(year, month, 1)
    while day_value.weekday() != weekday:
        day_value += timedelta(days=1)
    return day_value


def last_weekday(year: int, month: int, weekday: int) -> date:
    day_value = date(year, month, calendar.monthrange(year, month)[1])
    while day_value.weekday() != weekday:
        day_value -= timedelta(days=1)
    return day_value


def fallback_economic_events(source: str, lookahead_days: int) -> list[MacroEvent]:
    now = eastern_now()
    events: list[MacroEvent] = []
    for month_offset in range(5):
        year = now.year + (now.month + month_offset - 1) // 12
        month = (now.month + month_offset - 1) % 12 + 1
        candidates: list[tuple[str, date, str, str, str]] = []
        if source == "BLS":
            candidates.extend(
                [
                    ("Nonfarm payrolls / Employment Situation", first_weekday(year, month, 4), "Labor", "High", ECONOMIC_CALENDAR_SOURCES["BLS"]),
                    ("Consumer Price Index (CPI)", adjust_to_business_day(date(year, month, min(12, calendar.monthrange(year, month)[1]))), "Inflation", "High", ECONOMIC_CALENDAR_SOURCES["BLS"]),
                    ("Producer Price Index (PPI)", adjust_to_business_day(date(year, month, min(14, calendar.monthrange(year, month)[1]))), "Inflation", "High", ECONOMIC_CALENDAR_SOURCES["BLS"]),
                ]
            )
        elif source == "BEA":
            candidates.append(
                (
                    "Personal income, spending, and PCE inflation",
                    last_weekday(year, month, 4),
                    "Inflation",
                    "High",
                    ECONOMIC_CALENDAR_SOURCES["BEA"],
                )
            )
            if month in {1, 4, 7, 10}:
                candidates.append(
                    (
                        "Gross Domestic Product (GDP)",
                        last_weekday(year, month, 3),
                        "Growth",
                        "High",
                        ECONOMIC_CALENDAR_SOURCES["BEA"],
                    )
                )
        elif source == "ISM":
            candidates.extend(
                [
                    ("ISM Manufacturing PMI", first_business_day(year, month, 0), "Growth", "Medium", ECONOMIC_CALENDAR_SOURCES["ISM"]),
                    ("ISM Services PMI", first_business_day(year, month, 2), "Growth", "Medium", ECONOMIC_CALENDAR_SOURCES["ISM"]),
                ]
            )
        for name, event_date, category, impact, url in candidates:
            event_dt = datetime.combine(event_date, datetime.min.time()).replace(
                hour=8 if source in {"BLS", "BEA"} else 10,
                minute=30 if source in {"BLS", "BEA"} else 0,
                tzinfo=ZoneInfo("America/New_York"),
            )
            if event_dt <= now or (event_dt - now).days > lookahead_days:
                continue
            events.append(
                make_macro_event(
                    name,
                    event_dt,
                    source,
                    source_url=url,
                    notes=f"Fallback estimated schedule because {source} calendar fetch was unavailable or empty.",
                    category=category,
                    impact=impact,
                )
            )
    if source == "Treasury":
        events.extend(
            recurring_weekday_events(
                "Treasury auction schedule",
                "Treasury",
                ECONOMIC_CALENDAR_SOURCES["Treasury"],
                weekday=1,
                hour=11,
                minute=30,
                lookahead_days=lookahead_days,
                category="Rates",
                impact="Medium",
            )
        )
    return events


def fetch_treasury_auction_calendar(lookahead_days: int) -> tuple[list[MacroEvent], dict]:
    source = "Treasury"
    base_url = ECONOMIC_CALENDAR_SOURCES[source]
    today = eastern_now().date().isoformat()
    url = (
        f"{base_url}?fields=security_type,security_term,auction_date,offering_amt"
        f"&filter=auction_date:gte:{today}&sort=auction_date&page[size]=50"
    )
    try:
        response = requests.get(url, headers={"User-Agent": "volatility-radar/1.0 (+https://streamlit.io)"}, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return [], economic_source_status(source, "Error", 0, str(exc))
    events: list[MacroEvent] = []
    for item in payload.get("data", []):
        security_type = clean_text(item.get("security_type", "Treasury auction"))
        term = clean_text(item.get("security_term", ""))
        name = f"Treasury auction - {term} {security_type}".strip()
        event_dt = parse_release_datetime(item.get("auction_date"), "11:30 AM")
        add_event_if_relevant(events, name, event_dt, source, base_url, lookahead_days, category="Rates", impact="Medium")
    return events, economic_source_status(source, "OK", len(events))


def computed_calendar_events(lookahead_days: int) -> tuple[list[MacroEvent], list[dict]]:
    eia_events = recurring_weekday_events(
        "EIA Weekly Petroleum Status Report",
        "EIA",
        ECONOMIC_CALENDAR_SOURCES["EIA"],
        weekday=2,
        hour=10,
        minute=30,
        lookahead_days=lookahead_days,
        category="Energy",
        impact="Medium",
    )
    claims_events = recurring_weekday_events(
        "Initial jobless claims",
        "DOL ETA",
        ECONOMIC_CALENDAR_SOURCES["DOL ETA"],
        weekday=3,
        hour=8,
        minute=30,
        lookahead_days=lookahead_days,
        category="Labor",
        impact="Medium",
    )
    confidence_events: list[MacroEvent] = []
    now = eastern_now()
    for month_offset in range(4):
        year = now.year + (now.month + month_offset - 1) // 12
        month = (now.month + month_offset - 1) % 12 + 1
        days_in_month = calendar.monthrange(year, month)[1]
        candidates = [
            date(year, month, day)
            for day in range(days_in_month - 6, days_in_month + 1)
            if date(year, month, day).weekday() == 1
        ]
        if not candidates:
            continue
        event_dt = datetime.combine(candidates[-1], datetime.min.time()).replace(
            hour=10,
            minute=0,
            tzinfo=ZoneInfo("America/New_York"),
        )
        if event_dt > now and (event_dt - now).days <= lookahead_days:
            confidence_events.append(
                make_macro_event(
                    "Consumer confidence",
                    event_dt,
                    "Conference Board",
                    source_url=ECONOMIC_CALENDAR_SOURCES["Conference Board"],
                    notes="Rule-based last-Tuesday schedule; confirm on provider page.",
                    category="Consumer",
                    impact="Medium",
                )
            )
    statuses = [
        economic_source_status("EIA", "OK", len(eia_events), "Generated from standard weekly release cadence."),
        economic_source_status("DOL ETA", "OK", len(claims_events), "Generated from standard weekly release cadence."),
        economic_source_status("Conference Board", "OK", len(confidence_events), "Generated from standard monthly release cadence."),
    ]
    return eia_events + claims_events + confidence_events, statuses


@st.cache_data(ttl=21_600, show_spinner=False)
def fetch_scheduled_macro_events(lookahead_days: int = 90) -> tuple[tuple[MacroEvent, ...], tuple[dict, ...], datetime]:
    fetchers = (
        fetch_bls_calendar,
        fetch_bea_calendar,
        fetch_census_calendar,
        fetch_fomc_calendar,
        fetch_ism_calendar,
        fetch_treasury_auction_calendar,
    )
    events: list[MacroEvent] = []
    statuses: list[dict] = []
    for fetcher in fetchers:
        try:
            source_events, status = fetcher(lookahead_days)
        except Exception as exc:
            source_events, status = [], economic_source_status(fetcher.__name__, "Error", 0, str(exc))
        source_name = str(status.get("source", ""))
        if status.get("status") == "Error" or not source_events:
            fallback_events = fallback_economic_events(source_name, lookahead_days)
            if fallback_events:
                source_events = fallback_events
                status = economic_source_status(
                    source_name,
                    "Warning",
                    len(source_events),
                    "Using rule-based fallback schedule because the live source was unavailable or empty.",
                )
        events.extend(source_events)
        statuses.append(status)
    computed_events, computed_statuses = computed_calendar_events(lookahead_days)
    events.extend(computed_events)
    statuses.extend(computed_statuses)
    deduped: dict[tuple[str, date | None, str], MacroEvent] = {}
    for event in events:
        key = (event.name.lower(), event.event_date, event.source)
        existing = deduped.get(key)
        if existing is None or event.event_datetime and not existing.event_datetime:
            deduped[key] = event
    ordered = tuple(
        sorted(
            deduped.values(),
            key=lambda event: (
                event.event_datetime or datetime.max.replace(tzinfo=ZoneInfo("America/New_York")),
                -event.importance,
                event.name,
            ),
        )
    )
    return ordered, tuple(statuses), eastern_now()


def build_macro_context(
    articles: Iterable[Article],
    horizon_days: int,
    macro_events_text: str,
    scheduled_events: Iterable[MacroEvent] = (),
) -> MacroContext:
    now = datetime.now(timezone.utc)
    factor_scores: Counter[str] = Counter()
    scored_headlines: list[tuple[float, Article]] = []

    for article in articles:
        if article.published:
            age_days = max((now - article.published).total_seconds() / 86_400, 0)
            recency_weight = max(0.25, 1.0 - (age_days / 7.0))
        else:
            recency_weight = 0.45
        if article.macro_score <= 0:
            continue
        headline_score = article.macro_score * recency_weight
        scored_headlines.append((headline_score, article))
        for factor in article.macro_factors:
            factor_scores[factor] += headline_score

    events = tuple(scheduled_events) + parse_macro_events(macro_events_text, horizon_days)
    scheduled_event_score = 0.0
    for event in events:
        if event.days_until is None or event.days_until < 0 or event.days_until > horizon_days:
            continue
        urgency = 1.0
        if event.days_until is not None and horizon_days:
            urgency += (horizon_days - event.days_until) / horizon_days * 0.35
        event_score = event.importance * 5.0 * urgency
        factor_scores[event.factor] += event_score
        scheduled_event_score += event_score

    feed_score = sum(score for score, _ in scored_headlines)
    stress_score = min(100.0, (feed_score * 1.35) + scheduled_event_score)
    if stress_score > 0:
        stress_score = min(100.0, 12.0 + stress_score)

    top_headlines = tuple(
        article
        for _, article in sorted(scored_headlines, key=lambda item: item[0], reverse=True)[:8]
    )
    ordered_factors = tuple(
        (factor, round(score, 2))
        for factor, score in factor_scores.most_common()
    )
    return MacroContext(
        stress_score=round(stress_score, 1),
        factor_scores=ordered_factors,
        events=events,
        top_headlines=top_headlines,
    )


def event_frame(events: Iterable[MacroEvent]) -> pd.DataFrame:
    rows = []
    for event in events:
        event_dt = event.event_datetime
        rows.append(
            {
                "Report Name": event.name,
                "Release Date": event.event_date,
                "Release Time": event.release_time,
                "Source": event.source,
                "Category": event.category,
                "Impact": event.impact,
                "Previous": event.previous,
                "Forecast": event.forecast,
                "Actual": event.actual,
                "Days Until": event.days_until,
                "In Horizon": event.in_horizon,
                "Last Updated": event.last_updated.strftime("%Y-%m-%d %I:%M %p ET").lstrip("0")
                if event.last_updated
                else "N/A",
                "Notes": event.notes,
                "__event_dt": event_dt,
                "__impact_rank": {"High": 0, "Medium": 1, "Low": 2}.get(event.impact, 3),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return (
        result.sort_values(
            ["__event_dt", "__impact_rank", "Report Name"],
            ascending=[True, True, True],
            kind="mergesort",
        )
        .drop(columns=["__event_dt", "__impact_rank"])
        .reset_index(drop=True)
    )


def canonical_macro_category(value: object) -> str:
    label = clean_text(str(value or ""))
    return MACRO_CATEGORY_ALIASES.get(label, label or "Geopolitical / Macro Risk")


def macro_factor_frame(context: MacroContext) -> pd.DataFrame:
    category_scores: Counter[str] = Counter()
    for factor, score in context.factor_scores:
        category_scores[canonical_macro_category(factor)] += float(score or 0.0)

    rows = []
    for category, raw_score in category_scores.items():
        if raw_score <= 0:
            continue
        rows.append(
            {
                "Category": category,
                "Stress Score": min(round(raw_score, 1), 100.0),
                "Raw Score": round(raw_score, 1),
                "Signal State": "Current signals",
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Category", "Stress Score", "Raw Score", "Signal State"])
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Stress Score", "Raw Score", "Category"],
            ascending=[False, False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def scheduled_report_source_summary(statuses: Iterable[dict]) -> str:
    sources = sorted(
        {
            str(status.get("source", "Unknown"))
            for status in statuses
            if str(status.get("status", "")).lower() in {"ok", "warning"}
        }
    )
    return ", ".join(sources)


def filter_scheduled_reports(
    frame: pd.DataFrame,
    categories: Sequence[str],
    impacts: Sequence[str],
    sources: Sequence[str],
    date_range: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    filtered = frame.copy()
    if categories:
        filtered = filtered[filtered["Category"].isin(categories)]
    if impacts:
        filtered = filtered[filtered["Impact"].isin(impacts)]
    if sources:
        filtered = filtered[filtered["Source"].isin(sources)]

    today = eastern_now().date()
    release_dates = pd.to_datetime(filtered["Release Date"], errors="coerce").dt.date
    if date_range == "Today":
        filtered = filtered[release_dates.eq(today)]
    elif date_range == "This Week":
        filtered = filtered[release_dates.ge(today) & release_dates.le(today + timedelta(days=7))]
    elif date_range == "Next 30 Days":
        filtered = filtered[release_dates.ge(today) & release_dates.le(today + timedelta(days=30))]
    return filtered.reset_index(drop=True)


def scheduled_reports_summary_items(frame: pd.DataFrame, refreshed_at: datetime) -> list[dict[str, object]]:
    today = eastern_now().date()
    if frame.empty:
        next_high = "N/A"
        reports_this_week = 0
        high_this_week = 0
    else:
        release_dates = pd.to_datetime(frame["Release Date"], errors="coerce").dt.date
        week_mask = release_dates.ge(today) & release_dates.le(today + timedelta(days=7))
        reports_this_week = int(week_mask.sum())
        high_mask = frame["Impact"].astype(str).str.casefold().eq("high")
        high_this_week = int((week_mask & high_mask).sum())
        high_reports = frame[high_mask]
        next_high = str(high_reports.iloc[0]["Report Name"]) if not high_reports.empty else "N/A"
    return [
        {
            "label": "Next High Impact",
            "value": next_high,
            "context": "upcoming release",
            "tone": "bad" if next_high != "N/A" else "neutral",
        },
        {"label": "Reports This Week", "value": reports_this_week, "context": "scheduled events"},
        {
            "label": "High Impact",
            "value": high_this_week,
            "context": "this week",
            "tone": "bad" if high_this_week else "neutral",
        },
        {
            "label": "Last Refreshed",
            "value": refreshed_at.strftime("%I:%M %p ET").lstrip("0"),
            "context": "calendar cache",
        },
    ]


def macro_signal_debug_frame(articles: Iterable[Article], factor_frame: pd.DataFrame) -> pd.DataFrame:
    feed_counts: Counter[str] = Counter()
    for article in articles:
        for factor in article.macro_factors:
            feed_counts[canonical_macro_category(factor)] += 1

    stress_lookup = {}
    if not factor_frame.empty:
        stress_lookup = {
            str(row["Category"]): row.get("Stress Score", "N/A")
            for _, row in factor_frame.iterrows()
        }

    def debug_sort_key(category: str) -> tuple[float, str]:
        stress = coerce_float(stress_lookup.get(category))
        return (-(stress or 0.0), category)

    categories = sorted(set(feed_counts) | set(stress_lookup), key=debug_sort_key)
    return pd.DataFrame(
        [
            {
                "Category": category,
                "Feed Items": feed_counts.get(category, 0),
                "Stress Score": stress_lookup.get(category, "No current signals"),
            }
            for category in categories
        ]
    )


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])


def eastern_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-4)))


def provider_metadata(
    provider_name: str,
    data_type: str,
    freshness_status: str,
    *,
    last_updated: datetime | None = None,
    is_realtime: bool = False,
    is_delayed: bool = True,
    is_cached: bool = False,
    delay_disclaimer: str = "",
    rate_limit_notes: str = "",
    source_label: str = "",
    source_url: str = "",
    error: str = "",
) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name=provider_name,
        data_type=data_type,
        freshness_status=freshness_status,
        last_updated=last_updated or eastern_now(),
        is_realtime=is_realtime,
        is_delayed=is_delayed,
        is_cached=is_cached,
        delay_disclaimer=delay_disclaimer,
        rate_limit_notes=rate_limit_notes,
        source_label=source_label or provider_name,
        source_url=source_url,
        error=error,
    )


def metadata_to_dict(meta: ProviderMetadata) -> dict[str, object]:
    return {
        "provider_name": meta.provider_name,
        "data_type": meta.data_type,
        "freshness_status": meta.freshness_status,
        "last_updated": meta.last_updated,
        "is_realtime": meta.is_realtime,
        "is_delayed": meta.is_delayed,
        "is_cached": meta.is_cached,
        "delay_disclaimer": meta.delay_disclaimer,
        "rate_limit_notes": meta.rate_limit_notes,
        "source_label": meta.source_label,
        "source_url": meta.source_url,
        "error": meta.error,
    }


def default_yahoo_metadata(data_type: str, *, last_updated: datetime | None = None) -> ProviderMetadata:
    return provider_metadata(
        "Yahoo Finance/yfinance",
        data_type,
        "Delayed",
        last_updated=last_updated,
        is_realtime=False,
        is_delayed=True,
        delay_disclaimer="Yahoo/yfinance data can be delayed or cached by the provider.",
        rate_limit_notes="Free public endpoint; app cache TTLs throttle refreshes.",
        source_label="Yahoo Finance/yfinance",
    )


def yfinance_unavailable_message() -> str:
    if yf is not None:
        return ""
    detail = f" ({YFINANCE_IMPORT_ERROR})" if YFINANCE_IMPORT_ERROR else ""
    return "Yahoo Finance/yfinance is unavailable in this runtime. Reboot the app after dependency install or check Streamlit Cloud build logs." + detail


def make_yf_ticker(symbol: str):
    if yf is None:
        raise RuntimeError(yfinance_unavailable_message())
    return yf.Ticker(symbol)


def yahoo_chart_frame(symbol: str, range_param: str = "5d", interval: str = "1d") -> tuple[pd.DataFrame, dict, str]:
    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    try:
        response = requests.get(
            url,
            params={"range": range_param, "interval": interval, "includePrePost": "false", "events": "history"},
            headers={"User-Agent": "streamlit-investment-dashboard/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return empty_history(), {}, str(exc)

    chart = payload.get("chart", {}) if isinstance(payload, dict) else {}
    error = chart.get("error")
    if error:
        description = error.get("description") if isinstance(error, dict) else str(error)
        return empty_history(), {}, description or "Yahoo chart endpoint returned an error"
    results = chart.get("result") or []
    if not results:
        return empty_history(), {}, "Yahoo chart endpoint returned no result"
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote_blocks = ((result.get("indicators") or {}).get("quote") or [{}])
    quote = quote_blocks[0] if quote_blocks else {}
    if not timestamps or not quote:
        return empty_history(), result.get("meta") or {}, "Yahoo chart endpoint returned no price bars"

    index = pd.to_datetime(timestamps, unit="s", utc=True)
    frame = pd.DataFrame(
        {
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", []),
        },
        index=index,
    )
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"], how="all")
    if frame.empty:
        return empty_history(), result.get("meta") or {}, "Yahoo chart endpoint returned empty close data"
    return frame, result.get("meta") or {}, ""


def yahoo_chart_quote_snapshot(symbol: str) -> dict:
    intraday, meta_payload, message = yahoo_chart_frame(symbol, "1d", "5m")
    daily, daily_meta, daily_message = yahoo_chart_frame(symbol, "5d", "1d")
    meta_payload = meta_payload or daily_meta
    close = pd.to_numeric(intraday.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    daily_close = pd.to_numeric(daily.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    price = coerce_float(meta_payload.get("regularMarketPrice")) or (coerce_float(close.iloc[-1]) if not close.empty else None)
    previous_close = coerce_float(meta_payload.get("chartPreviousClose") or meta_payload.get("previousClose"))
    if previous_close is None and len(daily_close) >= 2:
        previous_close = coerce_float(daily_close.iloc[-2])
    change = price - previous_close if price is not None and previous_close not in (None, 0) else None
    change_pct = safe_ratio(change, previous_close, 100) if change is not None else None
    quote_frame = pd.DataFrame()
    if not close.empty:
        quote_frame = pd.DataFrame({"Price": close})
        quote_frame.index = pd.to_datetime(quote_frame.index)
    status_message = message or daily_message
    meta = provider_metadata(
        "Yahoo Finance chart API",
        "Quote",
        "Delayed / near real-time",
        last_updated=eastern_now(),
        is_realtime=False,
        is_delayed=True,
        delay_disclaimer="Yahoo chart endpoint is a public delayed/near-real-time fallback when yfinance is unavailable.",
        rate_limit_notes="Cached by Streamlit; no API key used.",
        source_label="Yahoo Finance chart API",
        error=status_message if price is None else "",
    )
    return {
        "status": "OK" if price is not None else "Error",
        "message": "" if price is not None else status_message,
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "previous_close": previous_close,
        "market_status": "Open" if str(meta_payload.get("marketState", "")).upper() in {"REGULAR", "OPEN"} else "Delayed",
        "quote_label": meta.freshness_status,
        "updated_at": meta.last_updated,
        "intraday": quote_frame,
        "provider": metadata_to_dict(meta),
    }


def freshness_caption(meta: ProviderMetadata | dict | None, fallback_source: str = "N/A") -> str:
    if meta is None:
        return f"Source: {fallback_source} | Freshness: Unavailable"
    if isinstance(meta, dict):
        meta = provider_metadata(
            str(meta.get("provider_name") or meta.get("source_label") or fallback_source),
            str(meta.get("data_type") or "Data"),
            str(meta.get("freshness_status") or "Delayed"),
            last_updated=meta.get("last_updated") if isinstance(meta.get("last_updated"), datetime) else eastern_now(),
            is_realtime=bool(meta.get("is_realtime")),
            is_delayed=bool(meta.get("is_delayed", True)),
            is_cached=bool(meta.get("is_cached")),
            delay_disclaimer=str(meta.get("delay_disclaimer") or ""),
            rate_limit_notes=str(meta.get("rate_limit_notes") or ""),
            source_label=str(meta.get("source_label") or fallback_source),
            source_url=str(meta.get("source_url") or ""),
            error=str(meta.get("error") or ""),
        )
    stamp = meta.last_updated.strftime("%I:%M:%S %p ET").lstrip("0")
    warning = f" | {meta.error}" if meta.error else ""
    return f"{meta.freshness_status}: updated {stamp} | Source: {meta.source_label}{warning}"


def metadata_from_status_frame(
    frame: pd.DataFrame,
    data_type: str,
    refreshed_at: datetime,
    fallback_source: str = "Yahoo Finance/yfinance",
) -> ProviderMetadata:
    provider = fallback_source
    freshness = "Delayed"
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        if "Provider" in frame and frame["Provider"].dropna().astype(str).str.len().any():
            provider = str(frame["Provider"].dropna().iloc[0])
        elif "Source" in frame and frame["Source"].dropna().astype(str).str.len().any():
            provider = str(frame["Source"].dropna().iloc[0])
        if "Freshness" in frame and frame["Freshness"].dropna().astype(str).str.len().any():
            freshness = str(frame["Freshness"].dropna().iloc[0])
        elif "Status" in frame and frame["Status"].astype(str).str.casefold().eq("error").any():
            freshness = "Error"
    is_realtime = "real-time" in freshness.casefold() and "unavailable" not in freshness.casefold()
    is_delayed = not is_realtime
    return provider_metadata(
        provider,
        data_type,
        freshness,
        last_updated=refreshed_at,
        is_realtime=is_realtime,
        is_delayed=is_delayed,
        delay_disclaimer="" if is_realtime else "Free/default providers may be delayed or cached.",
        source_label=provider,
    )


def active_quote_provider_label() -> str:
    if yf is None:
        return "Yahoo Finance chart API fallback"
    return "Yahoo Finance/yfinance"


def refresh_interval_seconds() -> int:
    label = st.session_state.get("global_refresh_interval", "1 minute")
    return int(GLOBAL_REFRESH_INTERVALS.get(label, 60))


def clear_live_data_caches(include_slow: bool = True) -> None:
    fast_functions = [
        fetch_quote_snapshot,
        fetch_home_market_snapshot,
        fetch_sector_performance,
        fetch_home_stock_snapshot,
        fetch_market_payloads,
        fetch_benchmark_history,
        fetch_performance_history,
        fetch_feeds,
        fetch_market_macro_headlines,
        fetch_social_mentions,
    ]
    slow_functions = [
        fetch_company_financials,
        fetch_scheduled_macro_events,
        fetch_us_listed_symbols,
        fetch_index_memberships,
        load_symbol_universe,
    ]
    for func in fast_functions + (slow_functions if include_slow else []):
        try:
            func.clear()
        except Exception:
            continue


def infer_market_status(info: dict | None = None) -> str:
    info = info or {}
    state = str(
        info.get("marketState")
        or info.get("market_state")
        or info.get("exchangeTimezoneName", "")
    ).upper()
    state_map = {
        "REGULAR": "Open",
        "OPEN": "Open",
        "PRE": "Pre-market",
        "PREMARKET": "Pre-market",
        "POST": "After-hours",
        "POSTMARKET": "After-hours",
        "CLOSED": "Closed",
    }
    if state in state_map:
        return state_map[state]

    now = eastern_now()
    minutes = now.hour * 60 + now.minute
    if now.weekday() >= 5:
        return "Closed"
    if 9 * 60 + 30 <= minutes < 16 * 60:
        return "Open"
    if 4 * 60 <= minutes < 9 * 60 + 30:
        return "Pre-market"
    if 16 * 60 <= minutes < 20 * 60:
        return "After-hours"
    return "Closed"


def extract_earnings_dates(yf_ticker: yf.Ticker) -> list[date]:
    dates: list[date] = []

    try:
        getter = getattr(yf_ticker, "get_earnings_dates", None)
        if callable(getter):
            earnings = getter(limit=8)
            if isinstance(earnings, pd.DataFrame) and not earnings.empty:
                for item in list(earnings.index) + list(earnings.get("Earnings Date", [])):
                    parsed = parse_date(item)
                    if parsed:
                        dates.append(parsed)
    except Exception:
        pass

    try:
        calendar_data = yf_ticker.calendar
        if isinstance(calendar_data, pd.DataFrame):
            for index_value, row in calendar_data.iterrows():
                index_text = str(index_value).lower()
                for column, value in row.items():
                    column_text = str(column).lower()
                    if "earn" in index_text or "earn" in column_text:
                        parsed = parse_date(value)
                        if parsed:
                            dates.append(parsed)
        elif isinstance(calendar_data, dict):
            for key, value in calendar_data.items():
                if "earn" in str(key).lower():
                    parsed = parse_date(value)
                    if parsed:
                        dates.append(parsed)
    except Exception:
        pass

    unique_dates = sorted({item for item in dates})
    return unique_dates


def extract_targets(yf_ticker: yf.Ticker, info: dict) -> dict[str, float | None]:
    targets = {
        "current": None,
        "mean": None,
        "low": None,
        "high": None,
    }
    try:
        raw_targets = yf_ticker.analyst_price_targets or {}
        targets["current"] = coerce_float(raw_targets.get("current"))
        targets["mean"] = coerce_float(raw_targets.get("mean"))
        targets["low"] = coerce_float(raw_targets.get("low"))
        targets["high"] = coerce_float(raw_targets.get("high"))
    except Exception:
        pass

    if info:
        targets["current"] = targets["current"] or coerce_float(
            info.get("currentPrice") or info.get("regularMarketPrice")
        )
        targets["mean"] = targets["mean"] or coerce_float(info.get("targetMeanPrice"))
        targets["low"] = targets["low"] or coerce_float(info.get("targetLowPrice"))
        targets["high"] = targets["high"] or coerce_float(info.get("targetHighPrice"))
    return targets


def empty_options_snapshot(message: str = "") -> dict:
    return {
        "iv": None,
        "move_pct": None,
        "expiry": None,
        "days_to_expiry": None,
        "contracts": 0,
        "message": message,
    }


def options_snapshot(
    ticker: str,
    yf_ticker: yf.Ticker,
    last_price: float | None,
    horizon_days: int,
    enabled: bool,
) -> dict:
    if not enabled:
        return empty_options_snapshot()
    if not last_price or last_price <= 0:
        return empty_options_snapshot("Missing last price for options moneyness")

    try:
        expirations = list(yf_ticker.options or [])
    except Exception as exc:
        return empty_options_snapshot(f"Options unavailable: {exc}")

    today = date.today()
    target_date = today + timedelta(days=max(horizon_days, 1))
    parsed_expirations: list[tuple[date, str]] = []
    for expiration in expirations:
        parsed = parse_date(expiration)
        if parsed and parsed >= today:
            parsed_expirations.append((parsed, expiration))
    if not parsed_expirations:
        return empty_options_snapshot("No future options expirations")

    parsed_expirations.sort(key=lambda item: item[0])
    selected_date, selected_expiration = parsed_expirations[-1]
    for expiration_date, expiration in parsed_expirations:
        if expiration_date >= target_date:
            selected_date = expiration_date
            selected_expiration = expiration
            break

    try:
        chain = yf_ticker.option_chain(selected_expiration)
    except Exception as exc:
        return empty_options_snapshot(f"Option chain unavailable: {exc}")

    contracts = []
    for side in (getattr(chain, "calls", None), getattr(chain, "puts", None)):
        if side is not None and not side.empty:
            contracts.append(side)
    if not contracts:
        return empty_options_snapshot("No option contracts returned")

    options = pd.concat(contracts, ignore_index=True)
    if "impliedVolatility" not in options or "strike" not in options:
        return empty_options_snapshot("Option chain missing IV or strike")

    options = options.copy()
    options["impliedVolatility"] = pd.to_numeric(options["impliedVolatility"], errors="coerce")
    options["strike"] = pd.to_numeric(options["strike"], errors="coerce")
    options = options.dropna(subset=["impliedVolatility", "strike"])
    options = options[(options["impliedVolatility"] > 0) & (options["impliedVolatility"] < 5)]
    if options.empty:
        return empty_options_snapshot("No usable implied volatility")

    options["distance"] = (options["strike"] - last_price).abs()
    nearest = options.nsmallest(min(8, len(options)), "distance").copy()
    weight = pd.Series(1.0, index=nearest.index)
    for column in ("openInterest", "volume"):
        if column in nearest:
            weight += pd.to_numeric(nearest[column], errors="coerce").fillna(0).clip(lower=0)
    iv = float((nearest["impliedVolatility"] * weight).sum() / weight.sum())
    days_to_expiry = max((selected_date - today).days, 1)
    move_pct = iv * math.sqrt(days_to_expiry / 365.0) * 100
    return {
        "iv": iv,
        "move_pct": move_pct,
        "expiry": selected_date,
        "days_to_expiry": days_to_expiry,
        "contracts": len(nearest),
        "message": "",
    }


def payload_error(ticker: str, message: str) -> dict:
    return {
        "ticker": ticker,
        "history": empty_history(),
        "company": ticker,
        "sector": "",
        "market_cap": None,
        "earnings_dates": [],
        "targets": {"current": None, "mean": None, "low": None, "high": None},
        "options": empty_options_snapshot(message),
        "options_30d": empty_options_snapshot(message),
        "status": "Error",
        "message": message,
    }


def fetch_ticker_payload(
    ticker: str,
    period: str,
    horizon_days: int,
    include_options: bool,
    include_30d_options: bool,
) -> dict:
    try:
        yf_ticker = make_yf_ticker(ticker)
        history = yf_ticker.history(
            period=period,
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=False,
        )
        if history is None:
            history = empty_history()
        info: dict = {}
        try:
            fast_info = getattr(yf_ticker, "fast_info", {}) or {}
            info.update(dict(fast_info))
        except Exception:
            pass
        try:
            full_info = yf_ticker.get_info()
            if isinstance(full_info, dict):
                info.update(full_info)
        except Exception:
            pass

        company = (
            info.get("shortName")
            or info.get("longName")
            or info.get("displayName")
            or ticker
        )
        sector = info.get("sector") or ""
        market_cap = coerce_float(info.get("marketCap") or info.get("market_cap"))
        targets = extract_targets(yf_ticker, info)
        earnings_dates = extract_earnings_dates(yf_ticker)
        last_price = None
        if history is not None and not history.empty and "Close" in history:
            close = pd.to_numeric(history["Close"], errors="coerce").dropna()
            if not close.empty:
                last_price = float(close.iloc[-1])
        if last_price is None:
            last_price = targets.get("current")
        option_data = options_snapshot(
            ticker,
            yf_ticker,
            last_price,
            horizon_days,
            include_options,
        )
        option_30d_data = options_snapshot(
            ticker,
            yf_ticker,
            last_price,
            30,
            include_options and include_30d_options,
        )
        status = "OK" if not history.empty else "Warning"
        message = "" if not history.empty else "No price history returned"
        if include_options and option_data.get("message"):
            message = "; ".join(part for part in [message, option_data["message"]] if part)
        if include_options and include_30d_options and option_30d_data.get("message"):
            message = "; ".join(part for part in [message, f"30D: {option_30d_data['message']}"] if part)
        return {
            "ticker": ticker,
            "history": history,
            "company": company,
            "sector": sector,
            "market_cap": market_cap,
            "earnings_dates": earnings_dates,
            "targets": targets,
            "options": option_data,
            "options_30d": option_30d_data,
            "status": status,
            "message": message,
        }
    except Exception as exc:
        return payload_error(ticker, str(exc))


@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_payloads(
    tickers: tuple[str, ...],
    period: str,
    horizon_days: int,
    include_options: bool,
    include_30d_options: bool,
) -> tuple[dict, ...]:
    if not tickers:
        return tuple()
    payloads: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as executor:
        futures = {
            executor.submit(
                fetch_ticker_payload,
                ticker,
                period,
                horizon_days,
                include_options,
                include_30d_options,
            ): ticker
            for ticker in tickers
        }
        for future in as_completed(futures):
            try:
                payloads.append(future.result())
            except Exception as exc:
                payloads.append(payload_error(futures[future], str(exc)))
    return tuple(sorted(payloads, key=lambda item: item["ticker"]))


def enrich_payloads_with_universe(payloads: Iterable[dict], scan_universe: pd.DataFrame) -> tuple[dict, ...]:
    if scan_universe.empty:
        return tuple(payloads)
    metadata = scan_universe.set_index("Ticker").to_dict("index")
    enriched = []
    for payload in payloads:
        ticker = payload.get("ticker", "")
        meta = metadata.get(ticker, {})
        row = dict(payload)
        row["exchange"] = meta.get("Exchange", "")
        row["index_membership"] = meta.get("Index Membership", "")
        row["listing_group"] = meta.get("Listing Group", "")
        row["is_etf"] = bool(meta.get("Is ETF", False))
        if row.get("company") == ticker and meta.get("Security Name"):
            row["company"] = meta["Security Name"]
        enriched.append(row)
    return tuple(enriched)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_benchmark_history(period: str) -> pd.DataFrame:
    try:
        history = make_yf_ticker("SPY").history(
            period=period,
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=False,
        )
        if history is None or history.empty:
            return empty_history()
        return history
    except Exception:
        return empty_history()


def normalized_returns(history: pd.DataFrame) -> pd.Series:
    if history is None or history.empty or "Close" not in history:
        return pd.Series(dtype=float)
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if len(close) < 3:
        return pd.Series(dtype=float)
    returns = close.pct_change().replace([float("inf"), float("-inf")], pd.NA).dropna()
    returns.index = pd.to_datetime(returns.index).normalize()
    return returns


def annualized_volatility(returns: pd.Series) -> float | None:
    if len(returns) < 5:
        return None
    return float(returns.tail(63).std() * math.sqrt(252) * 100)


def historical_window_move(
    returns: pd.Series,
    lookback_days: int,
    horizon_days: int,
) -> float | None:
    minimum_points = min(max(10, lookback_days // 3), lookback_days)
    if len(returns) < minimum_points:
        return None
    window = returns.tail(lookback_days)
    if len(window) < 5:
        return None
    return float(window.std() * math.sqrt(max(horizon_days, 1)) * 100)


def projected_base_move(returns: pd.Series, horizon_days: int) -> float | None:
    if len(returns) < 5:
        return None
    recent_window = min(max(12, horizon_days * 5), len(returns))
    recent_vol = float(returns.tail(recent_window).std())
    ewma_vol = float(returns.ewm(span=14, adjust=False).std().iloc[-1])
    daily_vol = max(recent_vol, ewma_vol)
    return daily_vol * math.sqrt(max(horizon_days, 1)) * 100


def atr_move(history: pd.DataFrame, horizon_days: int) -> float | None:
    required = {"High", "Low", "Close"}
    if history is None or history.empty or not required.issubset(history.columns):
        return None
    price_data = history[list(required)].apply(pd.to_numeric, errors="coerce").dropna()
    if len(price_data) < 5:
        return None
    previous_close = price_data["Close"].shift(1)
    true_range = pd.concat(
        [
            price_data["High"] - price_data["Low"],
            (price_data["High"] - previous_close).abs(),
            (price_data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    last_close = float(price_data["Close"].iloc[-1])
    if last_close <= 0:
        return None
    average_range = float(true_range.tail(14).mean())
    return average_range / last_close * math.sqrt(max(horizon_days, 1)) * 100


def volume_shock(history: pd.DataFrame) -> float | None:
    if history is None or history.empty or "Volume" not in history:
        return None
    volume = pd.to_numeric(history["Volume"], errors="coerce").dropna()
    volume = volume[volume > 0]
    if len(volume) < 8:
        return None
    recent = float(volume.tail(5).mean())
    baseline = float(volume.tail(30).mean())
    if baseline <= 0:
        return None
    return recent / baseline


def average_dollar_volume(history: pd.DataFrame) -> float | None:
    if history is None or history.empty or not {"Close", "Volume"}.issubset(history.columns):
        return None
    data = history[["Close", "Volume"]].apply(pd.to_numeric, errors="coerce").dropna()
    data = data[data["Volume"] > 0]
    if data.empty:
        return None
    return float((data["Close"] * data["Volume"]).tail(20).mean())


def gap_move(history: pd.DataFrame, horizon_days: int) -> float:
    if history is None or history.empty or not {"Open", "Close"}.issubset(history.columns):
        return 0.0
    data = history[["Open", "Close"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 6:
        return 0.0
    previous_close = data["Close"].shift(1)
    gaps = (data["Open"] / previous_close - 1).abs().dropna()
    if gaps.empty:
        return 0.0
    return float(gaps.tail(30).mean() * math.sqrt(max(horizon_days, 1)) * 100)


def recent_momentum(history: pd.DataFrame) -> float:
    if history is None or history.empty or "Close" not in history:
        return 0.0
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if len(close) < 6:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-6] - 1) * 100)


def trailing_realized_move(history: pd.DataFrame, horizon_days: int) -> float | None:
    required = {"High", "Low", "Close"}
    if history is None or history.empty or not required.issubset(history.columns):
        return None
    data = history[list(required)].apply(pd.to_numeric, errors="coerce").dropna()
    horizon = max(horizon_days, 1)
    if len(data) < horizon + 1:
        return None
    start_close = float(data["Close"].iloc[-horizon - 1])
    if start_close <= 0:
        return None
    window = data.tail(horizon)
    high_move = abs(float(window["High"].max()) / start_close - 1)
    low_move = abs(float(window["Low"].min()) / start_close - 1)
    return max(high_move, low_move) * 100


def rolling_beta(stock_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    if stock_returns.empty or benchmark_returns.empty:
        return None
    aligned = pd.concat([stock_returns, benchmark_returns], axis=1, join="inner").dropna()
    if len(aligned) < 20:
        return None
    aligned = aligned.tail(90)
    stock = aligned.iloc[:, 0]
    benchmark = aligned.iloc[:, 1]
    variance = float(benchmark.var())
    if variance <= 0:
        return None
    return float(stock.cov(benchmark) / variance)


def next_earnings_date(earnings_dates: Iterable[date]) -> tuple[date | None, int | None]:
    today = date.today()
    future_dates = sorted(item for item in earnings_dates if item >= today - timedelta(days=1))
    if not future_dates:
        return None, None
    next_date = future_dates[0]
    return next_date, (next_date - today).days


def sector_macro_multiplier(sector: str, factor_scores: tuple[tuple[str, float], ...]) -> float:
    if not factor_scores:
        return 1.0
    total = sum(score for _, score in factor_scores)
    if total <= 0:
        return 1.0
    weights = SECTOR_FACTOR_WEIGHTS.get(sector, {})
    weighted = 0.0
    for factor, score in factor_scores:
        weighted += (score / total) * weights.get(factor, 1.0)
    return max(0.75, min(1.55, weighted))


def ticker_news_risk(ticker: str, articles: Iterable[Article]) -> tuple[float, float, int]:
    now = datetime.now(timezone.utc)
    risk = 0.0
    sentiment_total = 0.0
    mention_count = 0
    for article in articles:
        if ticker not in article.mentions:
            continue
        mention_count += 1
        if article.published:
            age_days = max((now - article.published).total_seconds() / 86_400, 0)
            recency = max(0.25, 1.0 - (age_days / 5.0))
        else:
            recency = 0.45
        risk += (0.55 + abs(article.sentiment_score) * 1.2 + article.macro_score * 0.08) * recency
        sentiment_total += article.sentiment_score
    avg_sentiment = sentiment_total / mention_count if mention_count else 0.0
    return min(risk, 6.0), avg_sentiment, mention_count


def ticker_social_risk(
    ticker: str,
    mentions: Iterable[SocialMention],
    lookback_days: int,
) -> tuple[float, float, int]:
    now = datetime.now(timezone.utc)
    risk = 0.0
    sentiment_total = 0.0
    mention_count = 0
    horizon = max(lookback_days, 1)

    for mention in mentions:
        if ticker not in mention.mentions:
            continue
        if mention.published:
            age_days = max((now - mention.published).total_seconds() / 86_400, 0)
            if age_days > horizon:
                continue
            recency = max(0.2, 1.0 - (age_days / horizon))
        else:
            recency = 0.45
        source_weight = 1.15 if mention.source == "Stocktwits" else 1.0
        engagement_weight = min(math.log1p(max(mention.engagement, 0)) * 0.12, 0.6)
        risk += (
            0.42
            + abs(mention.sentiment_score) * 1.35
            + engagement_weight
        ) * recency * source_weight
        sentiment_total += mention.sentiment_score
        mention_count += 1

    buzz_bonus = min(math.log1p(mention_count) * 0.8, 2.2)
    avg_sentiment = sentiment_total / mention_count if mention_count else 0.0
    return min(risk + buzz_bonus, 7.0), avg_sentiment, mention_count


def ticker_social_engagement(
    ticker: str,
    mentions: Iterable[SocialMention],
    lookback_days: int,
) -> int:
    now = datetime.now(timezone.utc)
    horizon = max(lookback_days, 1)
    total = 0
    for mention in mentions:
        if ticker not in mention.mentions:
            continue
        if mention.published:
            age_days = max((now - mention.published).total_seconds() / 86_400, 0)
            if age_days > horizon:
                continue
        total += get_total_reactions(mention)
    return total


def analyst_dispersion_risk(targets: dict[str, float | None], last_price: float | None) -> float:
    current = targets.get("current") or last_price
    low = targets.get("low")
    high = targets.get("high")
    if not current or current <= 0 or not low or not high or high <= low:
        return 0.0
    spread_pct = (high - low) / current * 100
    return min(max(spread_pct / 18.0, 0.0), 5.0)


def direction_bias(
    momentum_pct: float,
    news_sentiment: float,
    targets: dict[str, float | None],
    last_price: float | None,
) -> str:
    score = 0.0
    score += max(-2.0, min(2.0, momentum_pct / 4.0))
    score += max(-2.0, min(2.0, news_sentiment * 2.2))
    target_mean = targets.get("mean")
    if target_mean and last_price and last_price > 0:
        score += max(-1.5, min(1.5, ((target_mean / last_price) - 1) * 10))
    if score >= 1.1:
        return "Upside skew"
    if score <= -1.1:
        return "Downside skew"
    return "Two-sided"


def forecast_for_payload(
    payload: dict,
    benchmark_returns: pd.Series,
    context: MacroContext,
    articles: Iterable[Article],
    social_mentions: Iterable[SocialMention],
    social_lookback_days: int,
    horizon_days: int,
) -> dict:
    ticker = payload["ticker"]
    history = payload.get("history", empty_history())
    notes: list[str] = []
    if payload.get("message"):
        notes.append(payload["message"])

    returns = normalized_returns(history)
    base_move = projected_base_move(returns, horizon_days)
    annual_vol = annualized_volatility(returns)
    hist_20_move = historical_window_move(returns, 20, horizon_days)
    hist_60_move = historical_window_move(returns, 60, horizon_days)
    hist_90_move = historical_window_move(returns, 90, horizon_days)
    hist_252_move = historical_window_move(returns, 252, horizon_days)
    atr_pct = atr_move(history, horizon_days)
    avg_dollar_volume = average_dollar_volume(history)
    if base_move is None and atr_pct is None:
        base_move = 0.0
        notes.append("Insufficient history")
    elif base_move is None:
        base_move = atr_pct or 0.0
    elif atr_pct is not None:
        base_move = max(base_move, atr_pct * 0.72)

    last_price = None
    if history is not None and not history.empty and "Close" in history:
        close = pd.to_numeric(history["Close"], errors="coerce").dropna()
        if not close.empty:
            last_price = float(close.iloc[-1])

    shock = volume_shock(history)
    volume_risk = 0.0
    if shock is not None and shock > 1.0:
        volume_risk = min((shock - 1.0) * 1.35, 4.5)

    momentum_pct = recent_momentum(history)
    momentum_risk = min(abs(momentum_pct) * 0.22, 4.0)
    gap_risk = min(gap_move(history, horizon_days) * 0.3, 3.5)

    earnings_date, days_to_earnings = next_earnings_date(payload.get("earnings_dates", []))
    earnings_risk = 0.0
    if days_to_earnings is not None and 0 <= days_to_earnings <= horizon_days:
        urgency = 1.0 + ((horizon_days - days_to_earnings) / max(horizon_days, 1) * 0.28)
        earnings_risk = max(1.8, base_move * 0.38) * urgency

    beta = rolling_beta(returns, benchmark_returns)
    beta_for_model = abs(beta) if beta is not None else 1.0
    sector = payload.get("sector", "")
    macro_multiplier = sector_macro_multiplier(sector, context.factor_scores)
    macro_risk = min(
        (context.stress_score / 100.0) * (0.75 + min(beta_for_model, 2.2) * 0.55) * macro_multiplier * 4.2,
        7.5,
    )

    news_risk, news_sentiment, news_mentions = ticker_news_risk(ticker, articles)
    social_risk, social_sentiment, social_mentions_count = ticker_social_risk(
        ticker,
        social_mentions,
        social_lookback_days,
    )
    social_engagement = ticker_social_engagement(ticker, social_mentions, social_lookback_days)
    target_risk = analyst_dispersion_risk(payload.get("targets", {}), last_price)
    directional_sentiment = news_sentiment
    if social_mentions_count:
        directional_sentiment = (news_sentiment + social_sentiment) / 2
    option_data = payload.get("options", {}) or {}
    options_move = coerce_float(option_data.get("move_pct"))
    options_iv = coerce_float(option_data.get("iv"))
    options_iv_pct = options_iv * 100 if options_iv is not None else None
    option_30d_data = payload.get("options_30d", {}) or {}
    options_30d_move = coerce_float(option_30d_data.get("move_pct"))
    options_30d_iv = coerce_float(option_30d_data.get("iv"))
    options_30d_iv_pct = options_30d_iv * 100 if options_30d_iv is not None else None

    model_move = (
        base_move
        + earnings_risk
        + macro_risk
        + news_risk
        + social_risk
        + volume_risk
        + target_risk
        + momentum_risk
        + gap_risk
    )
    options_lift = 0.0
    projected_move = model_move
    if options_move is not None:
        options_lift = max(options_move - model_move, 0.0)
        projected_move = max(model_move, options_move)
    backtest_move = trailing_realized_move(history, horizon_days)
    backtest_error = None
    backtest_result = ""
    if backtest_move is not None:
        backtest_error = projected_move - backtest_move
        backtest_result = "Covered" if backtest_error >= 0 else "Missed"
    volatility_score = min(100.0, projected_move * 5.5 + news_mentions * 1.6 + social_mentions_count * 1.2)

    history_points = len(returns)
    confidence = min(95.0, 38.0 + min(history_points, 90) * 0.42)
    if payload.get("status") != "OK":
        confidence -= 18.0
    if context.stress_score == 0:
        confidence -= 4.0
    if earnings_date is None:
        confidence -= 4.0
    if options_move is not None:
        confidence += 5.0
    confidence = max(10.0, min(95.0, confidence))

    components = {
        "realized volatility": base_move,
        "earnings": earnings_risk,
        "macro": macro_risk,
        "news": news_risk,
        "social": social_risk,
        "options IV": options_lift,
        "volume": volume_risk,
        "analyst dispersion": target_risk,
        "momentum/gaps": momentum_risk + gap_risk,
    }
    main_drivers = [
        name
        for name, value in sorted(components.items(), key=lambda item: item[1], reverse=True)
        if value >= 0.6
    ][:4]

    return {
        "Ticker": ticker,
        "Company": payload.get("company") or ticker,
        "Exchange": payload.get("exchange", ""),
        "Index Membership": payload.get("index_membership", ""),
        "Sector": sector or "Unknown",
        "Size": market_cap_bucket(payload.get("market_cap")),
        "Market Cap": payload.get("market_cap"),
        "Last Price": last_price,
        "Avg Dollar Volume": avg_dollar_volume,
        "Projected Move %": round(projected_move, 2),
        "Options Move %": None if options_move is None else round(options_move, 2),
        "Options IV %": None if options_iv_pct is None else round(options_iv_pct, 2),
        "Options Expiry": option_data.get("expiry"),
        "30D Options Move %": None if options_30d_move is None else round(options_30d_move, 2),
        "30D Options IV %": None if options_30d_iv_pct is None else round(options_30d_iv_pct, 2),
        "30D Options Expiry": option_30d_data.get("expiry"),
        "20D Hist Move %": None if hist_20_move is None else round(hist_20_move, 2),
        "60D Hist Move %": None if hist_60_move is None else round(hist_60_move, 2),
        "90D Hist Move %": None if hist_90_move is None else round(hist_90_move, 2),
        "252D Hist Move %": None if hist_252_move is None else round(hist_252_move, 2),
        "Backtest Move %": None if backtest_move is None else round(backtest_move, 2),
        "Backtest Error %": None if backtest_error is None else round(backtest_error, 2),
        "Backtest Result": backtest_result,
        "Volatility Score": round(volatility_score, 1),
        "Confidence": round(confidence, 0),
        "Direction Bias": direction_bias(
            momentum_pct,
            directional_sentiment,
            payload.get("targets", {}),
            last_price,
        ),
        "Base Move %": round(base_move, 2),
        "Earnings Risk": round(earnings_risk, 2),
        "Macro Risk": round(macro_risk, 2),
        "News Risk": round(news_risk, 2),
        "Social Risk": round(social_risk, 2),
        "Social Mentions": social_mentions_count,
        "Social Engagement": social_engagement,
        "Social Sentiment": round(social_sentiment, 2),
        "Volume Risk": round(volume_risk, 2),
        "Analyst Dispersion": round(target_risk, 2),
        "Beta": None if beta is None else round(beta, 2),
        "Volume Shock": None if shock is None else round(shock, 2),
        "ATR Move %": None if atr_pct is None else round(atr_pct, 2),
        "Ann. Realized Vol %": None if annual_vol is None else round(annual_vol, 1),
        "Earnings Date": earnings_date,
        "Days To Earnings": days_to_earnings,
        "Main Drivers": ", ".join(main_drivers) if main_drivers else "low signal",
        "Data Notes": "; ".join(notes),
    }


def build_forecast_frame(
    payloads: Iterable[dict],
    benchmark_history: pd.DataFrame,
    context: MacroContext,
    articles: Iterable[Article],
    social_mentions: Iterable[SocialMention],
    social_lookback_days: int,
    horizon_days: int,
) -> pd.DataFrame:
    benchmark_returns = normalized_returns(benchmark_history)
    rows = [
        forecast_for_payload(
            payload,
            benchmark_returns,
            context,
            articles,
            social_mentions,
            social_lookback_days,
            horizon_days,
        )
        for payload in payloads
    ]
    if not rows:
        return pd.DataFrame(columns=FORECAST_COLUMNS)
    frame = pd.DataFrame(rows)
    return rank_forecast_rows(frame)


def apply_forecast_filters(
    frame: pd.DataFrame,
    size_filters: list[str],
    sector_filters: list[str],
    min_price: float,
    min_dollar_volume: float,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    filtered = frame.copy()
    if size_filters:
        filtered = filtered[filtered["Size"].isin(size_filters)]
    if sector_filters:
        filtered = filtered[filtered["Sector"].isin(sector_filters)]
    if min_price > 0:
        filtered = filtered[filtered["Last Price"].fillna(0) >= min_price]
    if min_dollar_volume > 0:
        filtered = filtered[filtered["Avg Dollar Volume"].fillna(0) >= min_dollar_volume]
    return rank_forecast_rows(filtered)


def get_statement(yf_ticker: yf.Ticker, names: Iterable[str]) -> pd.DataFrame:
    for name in names:
        try:
            frame = getattr(yf_ticker, name)
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return clean_statement_frame(frame)
        except Exception:
            continue
    return pd.DataFrame()


def get_estimate_frame(yf_ticker: yf.Ticker, getter_name: str, property_name: str) -> pd.DataFrame:
    try:
        getter = getattr(yf_ticker, getter_name, None)
        frame = getter() if callable(getter) else getattr(yf_ticker, property_name, None)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            cleaned = frame.copy()
            cleaned.index = cleaned.index.map(str)
            for column in cleaned.columns:
                if column != "currency":
                    try:
                        cleaned[column] = pd.to_numeric(cleaned[column])
                    except (TypeError, ValueError):
                        pass
            return cleaned
    except Exception:
        pass
    return pd.DataFrame()


def earnings_expectations_frame(yf_ticker: yf.Ticker) -> pd.DataFrame:
    try:
        getter = getattr(yf_ticker, "get_earnings_history", None)
        history = getter() if callable(getter) else getattr(yf_ticker, "earnings_history", None)
    except Exception:
        history = None

    if isinstance(history, pd.DataFrame) and not history.empty:
        rows = []
        for period, row in history.tail(4).iterrows():
            report_date = parse_date(period)
            if report_date is None:
                report_date = date.today()
            estimate = coerce_float(row.get("epsEstimate"))
            actual = coerce_float(row.get("epsActual"))
            surprise = coerce_float(row.get("epsDifference"))
            surprise_pct = coerce_float(row.get("surprisePercent"))
            if surprise is None and estimate is not None and actual is not None:
                surprise = actual - estimate
            if surprise_pct is not None and abs(surprise_pct) <= 1:
                surprise_pct *= 100
            elif surprise_pct is None and surprise is not None and estimate:
                surprise_pct = surprise / abs(estimate) * 100
            rows.append(
                {
                    "Report Date": report_date,
                    "Quarter": f"{report_date.year} Q{((report_date.month - 1) // 3) + 1}",
                    "EPS Estimate": estimate,
                    "Reported EPS": actual,
                    "EPS Surprise": surprise,
                    "Surprise %": surprise_pct,
                    "Result": "Beat" if surprise is not None and surprise > 0 else "Miss" if surprise is not None and surprise < 0 else "In line",
                }
            )
        return pd.DataFrame(rows).sort_values("Report Date", ascending=False).reset_index(drop=True)

    try:
        getter = getattr(yf_ticker, "get_earnings_dates", None)
        if not callable(getter):
            return pd.DataFrame()
        earnings = getter(limit=12)
    except Exception:
        return pd.DataFrame()

    if not isinstance(earnings, pd.DataFrame) or earnings.empty:
        return pd.DataFrame()

    frame = earnings.copy()
    if "Earnings Date" not in frame.columns:
        frame = frame.reset_index().rename(columns={"index": "Earnings Date"})
    else:
        frame = frame.reset_index(drop=True)

    column_lookup = {normalize_statement_label(column): column for column in frame.columns}
    estimate_col = column_lookup.get("epsestimate") or column_lookup.get("epsest")
    actual_col = column_lookup.get("reportedeps") or column_lookup.get("actualeps")
    surprise_col = (
        column_lookup.get("surprise")
        or column_lookup.get("surprisepercent")
        or column_lookup.get("surprisepercent")
    )
    date_col = column_lookup.get("earningsdate") or frame.columns[0]

    rows = []
    today = pd.Timestamp(date.today())
    for _, row in frame.iterrows():
        report_date = pd.to_datetime(row.get(date_col), errors="coerce")
        if pd.isna(report_date) or report_date.tzinfo is not None:
            try:
                report_date = report_date.tz_localize(None)
            except (TypeError, AttributeError):
                pass
        if pd.isna(report_date) or report_date > today:
            continue

        estimate = coerce_float(row.get(estimate_col)) if estimate_col else None
        actual = coerce_float(row.get(actual_col)) if actual_col else None
        surprise_pct = coerce_float(row.get(surprise_col)) if surprise_col else None
        surprise = None
        if estimate is not None and actual is not None:
            surprise = actual - estimate
            if surprise_pct is None and estimate != 0:
                surprise_pct = surprise / abs(estimate) * 100
        if surprise_pct is not None and abs(surprise_pct) <= 1:
            surprise_pct *= 100
        if actual is None and estimate is None:
            continue
        rows.append(
            {
                "Report Date": report_date.date(),
                "Quarter": f"{report_date.year} Q{report_date.quarter}",
                "EPS Estimate": estimate,
                "Reported EPS": actual,
                "EPS Surprise": surprise,
                "Surprise %": surprise_pct,
                "Result": "Beat" if surprise is not None and surprise > 0 else "Miss" if surprise is not None and surprise < 0 else "In line",
            }
        )

    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    return result.sort_values("Report Date", ascending=False).head(4).reset_index(drop=True)


def nested_value(data: object, path: Sequence[str]) -> object:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_news_datetime(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    return parse_date(value)


def infer_report_rating(text: str) -> str:
    lowered = text.lower()
    rating_order = [
        ("Strong Buy", ("strong buy",)),
        ("Buy", (" buy ", "buy rating", "upgrades to buy")),
        ("Outperform", ("outperform",)),
        ("Overweight", ("overweight",)),
        ("Hold", (" hold ", "neutral", "market perform")),
        ("Underperform", ("underperform",)),
        ("Underweight", ("underweight",)),
        ("Sell", (" sell ", "sell rating", "downgrades to sell")),
    ]
    padded = f" {lowered} "
    for rating, terms in rating_order:
        if any(term in padded for term in terms):
            return rating
    if "upgrade" in lowered:
        return "Upgrade"
    if "downgrade" in lowered:
        return "Downgrade"
    return "N/A"


def infer_price_targets(text: str) -> tuple[float | None, float | None]:
    normalized = clean_text(text)
    target = None
    previous = None
    target_match = re.search(
        r"(?:price target|target|pt)\D{0,30}\$?\s*([0-9]{1,5}(?:\.[0-9]+)?)",
        normalized,
        flags=re.IGNORECASE,
    )
    if target_match:
        target = coerce_float(target_match.group(1))
    previous_match = re.search(
        r"\bfrom\s+\$?\s*([0-9]{1,5}(?:\.[0-9]+)?)",
        normalized,
        flags=re.IGNORECASE,
    )
    if previous_match:
        previous = coerce_float(previous_match.group(1))
    return target, previous


def fetch_analyst_reports_frame(yf_ticker: yf.Ticker, ticker: str) -> pd.DataFrame:
    news_items = []
    getter = getattr(yf_ticker, "get_news", None)
    if callable(getter):
        for kwargs in ({"count": 50}, {}):
            try:
                news_items = getter(**kwargs) or []
                if news_items:
                    break
            except TypeError:
                continue
            except Exception:
                break
    if not news_items:
        try:
            news_items = getattr(yf_ticker, "news", []) or []
        except Exception:
            news_items = []

    rows = []
    seen: set[str] = set()
    for item in news_items:
        if not isinstance(item, dict):
            continue
        title = (
            item.get("title")
            or nested_value(item, ("content", "title"))
            or nested_value(item, ("content", "headline"))
            or ""
        )
        summary = (
            item.get("summary")
            or nested_value(item, ("content", "summary"))
            or nested_value(item, ("content", "description"))
            or ""
        )
        text = clean_text(f"{title} {summary}")
        if not text or not any(term in text.lower() for term in ANALYST_REPORT_TERMS):
            continue
        source = (
            item.get("publisher")
            or nested_value(item, ("content", "provider", "displayName"))
            or nested_value(item, ("content", "provider", "name"))
            or "Yahoo Finance"
        )
        url = (
            item.get("link")
            or nested_value(item, ("content", "canonicalUrl", "url"))
            or nested_value(item, ("content", "clickThroughUrl", "url"))
            or ""
        )
        key = str(url or title)
        if key in seen:
            continue
        seen.add(key)
        published = parse_news_datetime(
            item.get("providerPublishTime")
            or nested_value(item, ("content", "pubDate"))
            or nested_value(item, ("content", "displayTime"))
        )
        target, previous_target = infer_price_targets(text)
        rows.append(
            {
                "Report Title": clean_text(str(title)),
                "Analyst Firm / Source": clean_text(str(source)),
                "Analyst": "N/A",
                "Publication Date": published,
                "Rating": infer_report_rating(text),
                "Price Target": target,
                "Previous Price Target": previous_target,
                "Summary": clean_text(str(summary)) or "Public analyst-related headline or report page.",
                "Source URL": str(url),
                "Data Source": "Yahoo Finance public news",
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Report Title",
                "Analyst Firm / Source",
                "Analyst",
                "Publication Date",
                "Rating",
                "Price Target",
                "Previous Price Target",
                "Summary",
                "Source URL",
                "Data Source",
            ]
        )
    return (
        pd.DataFrame(rows)
        .sort_values("Publication Date", ascending=False, na_position="last", kind="mergesort")
        .head(12)
        .reset_index(drop=True)
    )


def earnings_dates_frame(yf_ticker: yf.Ticker) -> pd.DataFrame:
    getter = getattr(yf_ticker, "get_earnings_dates", None)
    if not callable(getter):
        return pd.DataFrame()
    try:
        frame = getter(limit=12)
    except Exception:
        return pd.DataFrame()
    return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()


@st.cache_data(ttl=21_600, show_spinner=False)
def fetch_company_financials(
    ticker: str,
    statement_period: str = "Any",
    periods_requested: int = 0,
    target_year: int = 0,
) -> dict:
    symbol = normalize_symbol(ticker)
    if not symbol:
        return {"status": "Error", "message": "Invalid ticker symbol"}

    if yf is None:
        quote = fetch_quote_snapshot(symbol)
        history, _, _ = yahoo_chart_frame(symbol, "1y", "1d")
        info = {
            "symbol": symbol,
            "shortName": symbol,
            "longName": symbol,
            "currentPrice": quote.get("price"),
            "regularMarketPrice": quote.get("price"),
            "previousClose": quote.get("previous_close"),
        }
        return {
            "status": "OK",
            "message": yfinance_unavailable_message(),
            "ticker": symbol,
            "info": info,
            "history": history if isinstance(history, pd.DataFrame) else empty_history(),
            "financials_refreshed": eastern_now(),
            "request_context": {
                "statement_period": statement_period,
                "periods_requested": int(periods_requested or 0),
                "target_year": int(target_year or 0),
            },
            "annual_income": pd.DataFrame(),
            "quarterly_income": pd.DataFrame(),
            "annual_balance": pd.DataFrame(),
            "quarterly_balance": pd.DataFrame(),
            "annual_cashflow": pd.DataFrame(),
            "quarterly_cashflow": pd.DataFrame(),
            "earnings_expectations": pd.DataFrame(),
            "earnings_dates": pd.DataFrame(),
            "analyst_reports": pd.DataFrame(),
            "analyst_reports_refreshed": eastern_now(),
            "earnings_estimate": pd.DataFrame(),
            "revenue_estimate": pd.DataFrame(),
        }

    try:
        yf_ticker = make_yf_ticker(symbol)
        info: dict = {}
        try:
            fast_info = getattr(yf_ticker, "fast_info", {}) or {}
            info.update(dict(fast_info))
        except Exception:
            pass
        try:
            full_info = yf_ticker.get_info()
            if isinstance(full_info, dict):
                info.update(full_info)
        except Exception:
            pass
        try:
            history = yf_ticker.history(
                period="1y",
                interval="1d",
                auto_adjust=False,
                actions=False,
                raise_errors=False,
            )
        except Exception:
            history = empty_history()

        return {
            "status": "OK",
            "message": "",
            "ticker": symbol,
            "info": info,
            "history": history if isinstance(history, pd.DataFrame) else empty_history(),
            "financials_refreshed": eastern_now(),
            "request_context": {
                "statement_period": statement_period,
                "periods_requested": int(periods_requested or 0),
                "target_year": int(target_year or 0),
            },
            "annual_income": get_statement(yf_ticker, ("income_stmt", "financials")),
            "quarterly_income": get_statement(yf_ticker, ("quarterly_income_stmt", "quarterly_financials")),
            "annual_balance": get_statement(yf_ticker, ("balance_sheet",)),
            "quarterly_balance": get_statement(yf_ticker, ("quarterly_balance_sheet",)),
            "annual_cashflow": get_statement(yf_ticker, ("cashflow", "cash_flow")),
            "quarterly_cashflow": get_statement(yf_ticker, ("quarterly_cashflow", "quarterly_cash_flow")),
            "earnings_expectations": earnings_expectations_frame(yf_ticker),
            "earnings_dates": earnings_dates_frame(yf_ticker),
            "analyst_reports": fetch_analyst_reports_frame(yf_ticker, symbol),
            "analyst_reports_refreshed": eastern_now(),
            "earnings_estimate": get_estimate_frame(yf_ticker, "get_earnings_estimate", "earnings_estimate"),
            "revenue_estimate": get_estimate_frame(yf_ticker, "get_revenue_estimate", "revenue_estimate"),
        }
    except Exception as exc:
        return {"status": "Error", "message": str(exc), "ticker": symbol}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_performance_history(ticker: str, range_key: str) -> pd.DataFrame:
    symbol = normalize_symbol(ticker)
    config = PERFORMANCE_RANGES.get(range_key, PERFORMANCE_RANGES["1Y"])
    if not symbol:
        return empty_history()
    if yf is None:
        direct_history, _, _ = yahoo_chart_frame(symbol, config["period"], config["interval"])
        return direct_history if isinstance(direct_history, pd.DataFrame) else empty_history()

    try:
        yf_ticker = make_yf_ticker(symbol)
        if range_key == "YTD":
            today = date.today()
            history = yf_ticker.history(
                start=date(today.year, 1, 1),
                end=today + timedelta(days=1),
                interval=config["interval"],
                auto_adjust=True,
                actions=False,
                raise_errors=False,
            )
        else:
            history = yf_ticker.history(
                period=config["period"],
                interval=config["interval"],
                auto_adjust=True,
                actions=False,
                raise_errors=False,
            )
    except Exception:
        return empty_history()

    return history if isinstance(history, pd.DataFrame) else empty_history()


@st.cache_data(ttl=45, show_spinner=False)
def fetch_quote_snapshot(ticker: str) -> dict:
    raw_symbol = clean_text(str(ticker or "")).upper()
    symbol = raw_symbol if re.fullmatch(r"\^[A-Z0-9]{1,12}", raw_symbol) else normalize_symbol(ticker)
    if not symbol:
        meta = provider_metadata("Unavailable", "Quote", "Unavailable", is_delayed=False, error="Invalid ticker symbol")
        return {
            "status": "Error",
            "message": "Invalid ticker symbol",
            "price": None,
            "change": None,
            "change_pct": None,
            "market_status": "Unavailable",
            "quote_label": "Real-time unavailable",
            "updated_at": eastern_now(),
            "intraday": pd.DataFrame(),
            "provider": metadata_to_dict(meta),
        }

    if yf is None:
        return yahoo_chart_quote_snapshot(symbol)

    try:
        yf_ticker = make_yf_ticker(symbol)
        info: dict = {}
        try:
            fast_info = getattr(yf_ticker, "fast_info", {}) or {}
            info.update(dict(fast_info))
        except Exception:
            pass

        try:
            intraday = yf_ticker.history(
                period="1d",
                interval="5m",
                auto_adjust=True,
                actions=False,
                raise_errors=False,
            )
        except Exception:
            intraday = empty_history()

        if not isinstance(intraday, pd.DataFrame):
            intraday = empty_history()
        close = pd.Series(dtype=float)
        if not intraday.empty and "Close" in intraday:
            close = pd.to_numeric(intraday["Close"], errors="coerce").dropna()

        price = (
            coerce_float(info.get("last_price"))
            or coerce_float(info.get("lastPrice"))
            or coerce_float(info.get("regular_market_price"))
            or coerce_float(info.get("regularMarketPrice"))
            or (coerce_float(close.iloc[-1]) if not close.empty else None)
        )
        previous_close = (
            coerce_float(info.get("previous_close"))
            or coerce_float(info.get("previousClose"))
            or coerce_float(info.get("regular_market_previous_close"))
            or coerce_float(info.get("regularMarketPreviousClose"))
        )
        if previous_close is None:
            try:
                previous = yf_ticker.history(
                    period="5d",
                    interval="1d",
                    auto_adjust=True,
                    actions=False,
                    raise_errors=False,
                )
                if isinstance(previous, pd.DataFrame) and "Close" in previous:
                    previous_close_values = pd.to_numeric(previous["Close"], errors="coerce").dropna()
                    if len(previous_close_values) >= 2:
                        previous_close = coerce_float(previous_close_values.iloc[-2])
            except Exception:
                previous_close = None

        change = None
        change_pct = None
        if price is not None and previous_close not in (None, 0):
            change = price - previous_close
            change_pct = change / abs(previous_close) * 100

        quote_frame = pd.DataFrame()
        if not close.empty:
            quote_frame = pd.DataFrame({"Price": close})
            quote_frame.index = pd.to_datetime(quote_frame.index)

        meta = default_yahoo_metadata("Quote", last_updated=eastern_now())
        return {
            "status": "OK" if price is not None else "Warning",
            "message": "" if price is not None else "No quote price returned",
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "previous_close": previous_close,
            "market_status": infer_market_status(info),
            "quote_label": meta.freshness_status,
            "updated_at": meta.last_updated,
            "intraday": quote_frame,
            "provider": metadata_to_dict(meta),
        }
    except Exception as exc:
        meta = default_yahoo_metadata("Quote", last_updated=eastern_now())
        return {
            "status": "Error",
            "message": str(exc),
            "price": None,
            "change": None,
            "change_pct": None,
            "market_status": "Unavailable",
            "quote_label": "Real-time unavailable",
            "updated_at": meta.last_updated,
            "intraday": pd.DataFrame(),
            "provider": metadata_to_dict(
                provider_metadata(
                    meta.provider_name,
                    meta.data_type,
                    "Error",
                    last_updated=meta.last_updated,
                    is_realtime=False,
                    is_delayed=True,
                    error=str(exc),
                    source_label=meta.source_label,
                )
            ),
        }


def performance_frame(history: pd.DataFrame) -> pd.DataFrame:
    if history is None or history.empty or "Close" not in history:
        return pd.DataFrame()
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if close.empty:
        return pd.DataFrame()
    frame = pd.DataFrame({"Stock Price": close})
    frame.index = pd.to_datetime(frame.index)
    first_price = close.iloc[0]
    if first_price and not pd.isna(first_price):
        frame["Performance %"] = (close / first_price - 1) * 100
    else:
        frame["Performance %"] = 0.0
    return frame


def performance_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    if frame.empty or "Stock Price" not in frame:
        return {"last": None, "return": None, "high": None, "low": None}
    prices = pd.to_numeric(frame["Stock Price"], errors="coerce").dropna()
    performance = pd.to_numeric(frame.get("Performance %", pd.Series(dtype=float)), errors="coerce").dropna()
    return {
        "last": coerce_float(prices.iloc[-1]) if not prices.empty else None,
        "return": coerce_float(performance.iloc[-1]) if not performance.empty else None,
        "high": coerce_float(prices.max()) if not prices.empty else None,
        "low": coerce_float(prices.min()) if not prices.empty else None,
    }


def quote_row_from_yfinance(label: str, symbol: str, value_type: str = "index") -> dict[str, object]:
    try:
        quote = fetch_quote_snapshot(symbol)
        if quote.get("price") is not None:
            value = coerce_float(quote.get("price"))
            change = coerce_float(quote.get("change"))
            change_pct = coerce_float(quote.get("change_pct"))
            if value_type == "yield":
                value = value / 10 if value is not None else None
                change = change / 10 if change is not None else None
            provider = quote.get("provider", {})
            return {
                "Label": label,
                "Symbol": symbol,
                "Value": value,
                "Change": change,
                "Change %": change_pct,
                "Type": value_type,
                "Status": quote.get("status", "OK"),
                "Message": quote.get("message", ""),
                "Provider": provider.get("source_label", "Yahoo Finance/yfinance") if isinstance(provider, dict) else "Yahoo Finance/yfinance",
                "Freshness": provider.get("freshness_status", quote.get("quote_label", "Delayed")) if isinstance(provider, dict) else quote.get("quote_label", "Delayed"),
            }

        yf_ticker = make_yf_ticker(symbol)
        fast_info = {}
        try:
            fast_info = dict(getattr(yf_ticker, "fast_info", {}) or {})
        except Exception:
            fast_info = {}
        history = yf_ticker.history(
            period="5d",
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=False,
        )
        close = pd.Series(dtype=float)
        if isinstance(history, pd.DataFrame) and not history.empty and "Close" in history:
            close = pd.to_numeric(history["Close"], errors="coerce").dropna()
        value = coerce_float(fast_info.get("last_price") or fast_info.get("lastPrice"))
        previous = coerce_float(fast_info.get("previous_close") or fast_info.get("previousClose"))
        if value is None and not close.empty:
            value = coerce_float(close.iloc[-1])
        if previous is None and len(close) >= 2:
            previous = coerce_float(close.iloc[-2])
        change = value - previous if value is not None and previous is not None else None
        change_pct = safe_ratio(change, previous, 100) if change is not None else None
        if value_type == "yield":
            value = value / 10 if value is not None else None
            change = change / 10 if change is not None else None
        return {
            "Label": label,
            "Symbol": symbol,
            "Value": value,
            "Change": change,
            "Change %": change_pct,
            "Type": value_type,
            "Status": "OK",
            "Message": "",
            "Provider": "Yahoo Finance/yfinance",
            "Freshness": "Delayed",
        }
    except Exception as exc:
        return {
            "Label": label,
            "Symbol": symbol,
            "Value": None,
            "Change": None,
            "Change %": None,
            "Type": value_type,
            "Status": "Error",
            "Message": str(exc),
            "Provider": "Yahoo Finance/yfinance",
            "Freshness": "Error",
        }


@st.cache_data(ttl=60, show_spinner=False)
def fetch_home_market_snapshot() -> tuple[pd.DataFrame, pd.DataFrame, datetime]:
    rows = [
        quote_row_from_yfinance(item["label"], item["symbol"], item["type"])
        for item in HOME_MARKET_SYMBOLS
    ]
    status = pd.DataFrame(
        [
            {
                "Source": "Yahoo Finance/yfinance",
                "Symbol": row["Symbol"],
                "Status": row["Status"],
                "Message": row["Message"],
                "Provider": row.get("Provider", "Yahoo Finance/yfinance"),
                "Freshness": row.get("Freshness", "Delayed"),
            }
            for row in rows
        ]
    )
    return pd.DataFrame(rows), status, eastern_now()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sector_performance() -> tuple[pd.DataFrame, pd.DataFrame, datetime]:
    rows = []
    statuses = []
    for sector, symbol in SECTOR_ETFS:
        row = quote_row_from_yfinance(sector, symbol, "etf")
        rows.append(
            {
                "Sector": sector,
                "ETF": symbol,
                "Last": row["Value"],
                "Daily Change %": row["Change %"],
                "Daily Change": row["Change"],
            }
        )
        statuses.append(
            {
                "Source": "Yahoo Finance/yfinance",
                "Symbol": symbol,
                "Status": row["Status"],
                "Message": row["Message"],
                "Provider": row.get("Provider", "Yahoo Finance/yfinance"),
                "Freshness": row.get("Freshness", "Delayed"),
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("Daily Change %", ascending=False, na_position="last", kind="mergesort").reset_index(drop=True)
    return frame, pd.DataFrame(statuses), eastern_now()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_home_stock_snapshot(ticker: str) -> tuple[dict, pd.DataFrame, datetime]:
    symbol = normalize_symbol(ticker) or "SPY"
    if yf is None:
        quote = fetch_quote_snapshot(symbol)
        history, _, _ = yahoo_chart_frame(symbol, "1y", "1d")
        last_price = quote.get("price")
        volume = None
        if isinstance(history, pd.DataFrame) and not history.empty and "Volume" in history:
            volume_values = pd.to_numeric(history["Volume"], errors="coerce").dropna()
            volume = coerce_float(volume_values.iloc[-1]) if not volume_values.empty else None
        snapshot = {
            "Ticker": symbol,
            "Name": symbol,
            "Last Price": last_price,
            "Daily Change %": quote.get("change_pct"),
            "Market Cap": None,
            "Volume": volume,
            "Relative Volume": None,
            "52W High": coerce_float(history["High"].max()) if isinstance(history, pd.DataFrame) and "High" in history else None,
            "52W Low": coerce_float(history["Low"].min()) if isinstance(history, pd.DataFrame) and "Low" in history else None,
            "Trailing PE": None,
            "Forward PE": None,
            "EPS": None,
            "Revenue Growth %": None,
            "Analyst Rating": "N/A",
            "Avg Target": None,
            "Option Move %": None,
            "IV %": None,
            "IV Rank": None,
            "Next Earnings": None,
            "Dividend Yield %": None,
            "Short Interest %": None,
            "Market Status": quote.get("market_status"),
            "Quote Label": quote.get("quote_label"),
            "Provider": (quote.get("provider") or {}).get("source_label", "Yahoo Finance chart API") if isinstance(quote.get("provider"), dict) else "Yahoo Finance chart API",
            "Freshness": (quote.get("provider") or {}).get("freshness_status", quote.get("quote_label", "Delayed")) if isinstance(quote.get("provider"), dict) else quote.get("quote_label", "Delayed"),
            "Provider Metadata": quote.get("provider") or metadata_to_dict(default_yahoo_metadata("Quick Stock Snapshot")),
            "Status": quote.get("status", "Warning"),
            "Message": yfinance_unavailable_message(),
        }
        return (
            snapshot,
            pd.DataFrame(
                [
                    {
                        "Source": "Yahoo Finance chart API",
                        "Symbol": symbol,
                        "Status": snapshot["Status"],
                        "Message": snapshot["Message"],
                        "Provider": snapshot["Provider"],
                        "Freshness": snapshot["Freshness"],
                    }
                ]
            ),
            eastern_now(),
        )
    try:
        yf_ticker = make_yf_ticker(symbol)
        info = {}
        try:
            info.update(dict(getattr(yf_ticker, "fast_info", {}) or {}))
        except Exception:
            pass
        try:
            full_info = yf_ticker.get_info()
            if isinstance(full_info, dict):
                info.update(full_info)
        except Exception:
            pass
        quote = fetch_quote_snapshot(symbol)
        last_price = quote.get("price") or coerce_float(info.get("last_price") or info.get("currentPrice"))
        option_snapshot = options_snapshot(symbol, yf_ticker, last_price, 7, True)
        volume = coerce_float(info.get("last_volume") or info.get("regularMarketVolume") or info.get("volume"))
        avg_volume = coerce_float(info.get("averageVolume") or info.get("average_volume"))
        relative_volume = safe_ratio(volume, avg_volume)
        snapshot = {
            "Ticker": symbol,
            "Name": info.get("longName") or info.get("shortName") or symbol,
            "Last Price": last_price,
            "Daily Change %": quote.get("change_pct"),
            "Market Cap": coerce_float(info.get("marketCap") or info.get("market_cap")),
            "Volume": volume,
            "Relative Volume": relative_volume,
            "52W High": coerce_float(info.get("fiftyTwoWeekHigh") or info.get("yearHigh")),
            "52W Low": coerce_float(info.get("fiftyTwoWeekLow") or info.get("yearLow")),
            "Trailing PE": coerce_float(info.get("trailingPE")),
            "Forward PE": coerce_float(info.get("forwardPE")),
            "EPS": coerce_float(info.get("trailingEps")),
            "Revenue Growth %": (coerce_float(info.get("revenueGrowth")) * 100) if coerce_float(info.get("revenueGrowth")) is not None else None,
            "Analyst Rating": str(info.get("recommendationKey") or "N/A").replace("_", " ").title(),
            "Avg Target": coerce_float(info.get("targetMeanPrice")),
            "Option Move %": coerce_float(option_snapshot.get("move_pct")),
            "IV %": (coerce_float(option_snapshot.get("iv")) * 100) if coerce_float(option_snapshot.get("iv")) is not None else None,
            "IV Rank": None,
            "Next Earnings": next_company_earnings_date({"earnings_dates": earnings_dates_frame(yf_ticker)}, info),
            "Dividend Yield %": (coerce_float(info.get("dividendYield")) * 100) if coerce_float(info.get("dividendYield")) is not None else None,
            "Short Interest %": (coerce_float(info.get("shortPercentOfFloat")) * 100) if coerce_float(info.get("shortPercentOfFloat")) is not None else None,
            "Market Status": quote.get("market_status"),
            "Quote Label": quote.get("quote_label"),
            "Provider": (quote.get("provider") or {}).get("source_label", "Yahoo Finance/yfinance") if isinstance(quote.get("provider"), dict) else "Yahoo Finance/yfinance",
            "Freshness": (quote.get("provider") or {}).get("freshness_status", quote.get("quote_label", "Delayed")) if isinstance(quote.get("provider"), dict) else quote.get("quote_label", "Delayed"),
            "Provider Metadata": quote.get("provider") or metadata_to_dict(default_yahoo_metadata("Quick Stock Snapshot")),
            "Status": quote.get("status", "OK"),
        }
        status = pd.DataFrame(
            [
                {
                    "Source": "Yahoo Finance/yfinance",
                    "Symbol": symbol,
                    "Status": snapshot["Status"],
                    "Message": option_snapshot.get("message", ""),
                    "Provider": snapshot.get("Provider", "Yahoo Finance/yfinance"),
                    "Freshness": snapshot.get("Freshness", "Delayed"),
                }
            ]
        )
        return snapshot, status, eastern_now()
    except Exception as exc:
        return (
            {
                "Ticker": symbol,
                "Name": symbol,
                "Status": "Error",
                "Message": str(exc),
            },
            pd.DataFrame([{"Source": "Yahoo Finance/yfinance", "Symbol": symbol, "Status": "Error", "Message": str(exc)}]),
            eastern_now(),
        )


def format_market_snapshot_value(row: pd.Series) -> str:
    value = coerce_float(row.get("Value"))
    if str(row.get("Type")) == "yield":
        return format_percent(value, 2)
    return format_number(value, 2)


def market_mood_score(market_df: pd.DataFrame, sector_df: pd.DataFrame, articles: Sequence[Article], events_df: pd.DataFrame) -> tuple[int, str]:
    score = 50.0
    if not market_df.empty and "Change %" in market_df:
        index_changes = pd.to_numeric(
            market_df[market_df["Label"].isin(["S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000"])]["Change %"],
            errors="coerce",
        ).dropna()
        if not index_changes.empty:
            score += float(index_changes.mean()) * 5.0
        vix_change = pd.to_numeric(market_df[market_df["Label"].eq("VIX")]["Change %"], errors="coerce").dropna()
        if not vix_change.empty:
            score -= float(vix_change.iloc[0]) * 0.35
    if not sector_df.empty:
        sector_changes = pd.to_numeric(sector_df["Daily Change %"], errors="coerce").dropna()
        if not sector_changes.empty:
            score += float(sector_changes.mean()) * 2.0
            score -= min(float(sector_changes.std() or 0) * 1.2, 8.0)
    if articles:
        sentiment = sum(article.sentiment_score for article in articles[:25]) / max(min(len(articles), 25), 1)
        score += sentiment * 10.0
    if not events_df.empty:
        high_impact = events_df["Impact"].astype(str).str.casefold().eq("high").sum()
        score -= min(float(high_impact) * 2.5, 10.0)
    bounded = int(max(0, min(100, round(score))))
    label = "Risk-on" if bounded >= 62 else "Defensive" if bounded <= 42 else "Balanced"
    return bounded, label


def company_statement_set(payload: dict, period: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, bool]:
    quarterly = period == "Quarterly"
    prefix = "quarterly" if quarterly else "annual"
    return (
        payload.get(f"{prefix}_income", pd.DataFrame()),
        payload.get(f"{prefix}_balance", pd.DataFrame()),
        payload.get(f"{prefix}_cashflow", pd.DataFrame()),
        quarterly,
    )


def next_company_earnings_date(payload: dict, info: dict) -> date | None:
    earnings_dates = payload.get("earnings_dates", pd.DataFrame())
    if isinstance(earnings_dates, pd.DataFrame) and not earnings_dates.empty:
        frame = earnings_dates.copy()
        if "Earnings Date" not in frame.columns:
            frame = frame.reset_index().rename(columns={"index": "Earnings Date"})
        date_col = "Earnings Date" if "Earnings Date" in frame.columns else frame.columns[0]
        parsed = pd.to_datetime(frame[date_col], errors="coerce", utc=True)
        try:
            parsed = parsed.dt.tz_convert(None)
        except (AttributeError, TypeError):
            pass
        upcoming = parsed[parsed.dt.date >= date.today()].dropna().sort_values()
        if not upcoming.empty:
            return upcoming.iloc[0].date()

    for key in ("earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd"):
        timestamp = coerce_float(info.get(key))
        if timestamp:
            try:
                parsed = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            except (OverflowError, OSError, ValueError):
                continue
            if parsed >= date.today():
                return parsed
    return None


def financial_series_map(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, pd.Series]:
    return {
        "Revenue": statement_series(income, FINANCIAL_LINE_ITEMS["Revenue"]),
        "Gross Profit": statement_series(income, FINANCIAL_LINE_ITEMS["Gross Profit"]),
        "Operating Income": statement_series(income, FINANCIAL_LINE_ITEMS["Operating Income"]),
        "Net Income": statement_series(income, FINANCIAL_LINE_ITEMS["Net Income"]),
        "EBITDA": statement_series(income, FINANCIAL_LINE_ITEMS["EBITDA"]),
        "Diluted EPS": statement_series(income, FINANCIAL_LINE_ITEMS["Diluted EPS"]),
        "Total Assets": statement_series(balance, FINANCIAL_LINE_ITEMS["Total Assets"]),
        "Total Debt": statement_series(balance, FINANCIAL_LINE_ITEMS["Total Debt"]),
        "Cash": statement_series(balance, FINANCIAL_LINE_ITEMS["Cash"]),
        "Stockholders Equity": statement_series(balance, FINANCIAL_LINE_ITEMS["Stockholders Equity"]),
        "Current Assets": statement_series(balance, FINANCIAL_LINE_ITEMS["Current Assets"]),
        "Current Liabilities": statement_series(balance, FINANCIAL_LINE_ITEMS["Current Liabilities"]),
        "Operating Cash Flow": statement_series(cashflow, FINANCIAL_LINE_ITEMS["Operating Cash Flow"]),
        "Capital Expenditure": statement_series(cashflow, FINANCIAL_LINE_ITEMS["Capital Expenditure"]),
        "Free Cash Flow": statement_series(cashflow, FINANCIAL_LINE_ITEMS["Free Cash Flow"]),
    }


def align_financial_series(series_map: dict[str, pd.Series], quarterly: bool, periods: int) -> pd.DataFrame:
    rows = []
    all_periods = sorted(
        {
            period
            for series in series_map.values()
            for period in series.dropna().index
        }
    )[-periods:]
    for period in all_periods:
        row = {"Period": period_label(period, quarterly), "Period Date": period}
        for name, series in series_map.items():
            value = series.get(period)
            row[name] = coerce_float(value)
        if row.get("Free Cash Flow") is None:
            operating_cash = row.get("Operating Cash Flow")
            capex = row.get("Capital Expenditure")
            if operating_cash is not None and capex is not None:
                row["Free Cash Flow"] = operating_cash + capex
        rows.append(row)
    return pd.DataFrame(rows)


def statement_period_options(frames: Sequence[pd.DataFrame]) -> list[pd.Timestamp]:
    periods: set[pd.Timestamp] = set()
    for frame in frames:
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        for column in frame.columns:
            try:
                timestamp = pd.Timestamp(column)
                if not pd.isna(timestamp):
                    periods.add(timestamp.tz_localize(None) if timestamp.tzinfo else timestamp)
            except Exception:
                continue
    return sorted(periods, reverse=True)


def match_statement_column(frame: pd.DataFrame, period: object) -> object | None:
    if frame.empty or period is None:
        return None
    if period in frame.columns:
        return period
    try:
        target = pd.Timestamp(period)
    except Exception:
        target = None
    for column in frame.columns:
        if column == period:
            return column
        if target is None:
            continue
        try:
            candidate = pd.Timestamp(column)
            if candidate == target or candidate.date() == target.date():
                return column
        except Exception:
            continue
    return None


def statement_line_value(frame: pd.DataFrame, period: object, aliases: Iterable[str]) -> tuple[float | None, str | None]:
    if frame.empty:
        return None, None
    column = match_statement_column(frame, period)
    if column is None:
        return None, None
    lookup = {normalize_statement_label(index): index for index in frame.index}
    for alias in aliases:
        match = lookup.get(normalize_statement_label(alias))
        if match is None:
            continue
        value = coerce_float(frame.loc[match, column])
        if value is not None:
            return value, str(match)
    return None, None


def normalize_sankey_statement(
    frame: pd.DataFrame,
    field_map: dict[str, tuple[str, ...]],
    period: object,
    previous_period: object | None,
    base_label: str,
) -> pd.DataFrame:
    rows = []
    base_value, _ = statement_line_value(frame, period, field_map.get(base_label, ()))
    for label, aliases in field_map.items():
        value, source = statement_line_value(frame, period, aliases)
        previous, _ = statement_line_value(frame, previous_period, aliases) if previous_period is not None else (None, None)
        percent_of_base = safe_ratio(abs(value), abs(base_value), 100) if value is not None and base_value else None
        yoy = None
        if value is not None and previous not in (None, 0):
            yoy = safe_ratio(value - previous, abs(previous), 100)
        rows.append(
            {
                "Line Item": label,
                "Value": value,
                "Percent of Base": percent_of_base,
                "Source Field": source or "N/A",
                "YoY Change %": yoy,
            }
        )
    return pd.DataFrame(rows)


def sankey_value(normalized: pd.DataFrame, label: str) -> float | None:
    if normalized.empty or "Line Item" not in normalized:
        return None
    match = normalized[normalized["Line Item"].eq(label)]
    if match.empty:
        return None
    return coerce_float(match.iloc[0].get("Value"))


def sankey_yoy(normalized: pd.DataFrame, label: str) -> float | None:
    if normalized.empty or "Line Item" not in normalized:
        return None
    match = normalized[normalized["Line Item"].eq(label)]
    if match.empty:
        return None
    return coerce_float(match.iloc[0].get("YoY Change %"))


def set_derived_sankey_value(
    normalized: pd.DataFrame,
    label: str,
    value: float | None,
    base_value: float | None,
    source: str,
) -> pd.DataFrame:
    if value is None or pd.isna(value) or abs(value) <= 0:
        return normalized
    mask = normalized["Line Item"].eq(label) if "Line Item" in normalized else pd.Series(dtype=bool)
    percent_of_base = safe_ratio(abs(value), abs(base_value), 100) if base_value else None
    row = {
        "Line Item": label,
        "Value": value,
        "Percent of Base": percent_of_base,
        "Source Field": source,
        "YoY Change %": None,
    }
    if mask.any():
        current = coerce_float(normalized.loc[mask, "Value"].iloc[0])
        if current is None:
            for column, column_value in row.items():
                normalized.loc[mask, column] = column_value
        return normalized
    return pd.concat([normalized, pd.DataFrame([row])], ignore_index=True)


def sankey_fields_debug(normalized: pd.DataFrame) -> tuple[list[str], list[str]]:
    if normalized.empty:
        return [], []
    values = normalized["Value"].map(coerce_float)
    available = normalized.loc[values.notna(), "Line Item"].astype(str).tolist()
    missing = normalized.loc[values.isna(), "Line Item"].astype(str).tolist()
    return available, missing


def normalized_sankey_display(normalized: pd.DataFrame) -> pd.DataFrame:
    if normalized.empty:
        return normalized
    display = normalized.copy()
    if "Value" in display:
        display["Value"] = display["Value"].map(lambda value: format_compact_currency(value, 2))
    if "Percent of Base" in display:
        display["Percent of Base"] = display["Percent of Base"].map(lambda value: format_percent(value, 1))
    if "YoY Change %" in display:
        display["YoY Change %"] = display["YoY Change %"].map(lambda value: format_percent(value, 1, signed=True))
    return display.fillna("N/A")


def sankey_node_name(label: str, value: float | None = None) -> str:
    formatted = format_compact_currency(value, 1) if value is not None else ""
    return f"{label}<br>{formatted}" if formatted and formatted != "N/A" else label


def sankey_svg_color(tone: object, alpha_hex: str = "aa") -> str:
    colors = {
        "inflow": "#49d69b",
        "outflow": "#ef6f7b",
        "neutral": "#5ec7e8",
        "warning": "#e6d36f",
        "claim": "#9bdcf3",
    }
    return colors.get(str(tone or "neutral"), colors["neutral"]) + alpha_hex


def truncate_svg_label(value: object, max_chars: int = 24) -> str:
    text = str(value or "")
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "..."


def sankey_svg_layers(links: list[dict[str, object]]) -> dict[str, int]:
    nodes = []
    for link in links:
        for key in ("source", "target"):
            node = str(link.get(key, ""))
            if node and node not in nodes:
                nodes.append(node)
    layers = {node: 0 for node in nodes}
    for _ in range(max(1, len(nodes))):
        changed = False
        for link in links:
            source = str(link.get("source", ""))
            target = str(link.get("target", ""))
            if not source or not target:
                continue
            next_layer = layers.get(source, 0) + 1
            if next_layer > layers.get(target, 0):
                layers[target] = next_layer
                changed = True
        if not changed:
            break
    max_layer = max(layers.values(), default=0)
    if max_layer > 5:
        scale = 5 / max_layer
        layers = {node: int(round(layer * scale)) for node, layer in layers.items()}
    return layers


def render_sankey_svg_flow(
    links: list[dict[str, object]],
    node_values: dict[str, float | None],
    *,
    title: str,
    max_links: int = 18,
) -> None:
    if not links:
        st.info("No flow links are available for this statement.")
        return
    visible_links = sorted(
        links,
        key=lambda link: float(link.get("value") or 0),
        reverse=True,
    )[:max_links]
    layers = sankey_svg_layers(visible_links)
    layer_nodes: dict[int, list[str]] = {}
    for node, layer in layers.items():
        layer_nodes.setdefault(layer, []).append(node)
    node_flow: dict[str, float] = {}
    for link in visible_links:
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        value = float(link.get("value") or 0)
        node_flow[source] = node_flow.get(source, 0.0) + value
        node_flow[target] = node_flow.get(target, 0.0) + value
    for node in list(node_flow):
        value = coerce_float(node_values.get(node))
        if value is not None:
            node_flow[node] = max(node_flow.get(node, 0.0), abs(value))
    max_flow = max(node_flow.values(), default=1.0) or 1.0

    width = 1180
    height = 430
    margin_x = 42
    margin_y = 42
    node_width = 12
    max_layer = max(layer_nodes, default=0)
    x_gap = (width - margin_x * 2 - node_width) / max(1, max_layer)
    node_positions: dict[str, tuple[float, float, float]] = {}
    node_parts = []
    for layer, nodes in sorted(layer_nodes.items()):
        nodes = sorted(nodes, key=lambda node: (-node_flow.get(node, 0.0), node))
        slot = (height - margin_y * 2) / max(1, len(nodes))
        x = margin_x + layer * x_gap
        for index, node in enumerate(nodes):
            flow = node_flow.get(node, 0.0)
            node_height = max(20.0, min(68.0, 18.0 + (flow / max_flow) * 50.0))
            y = margin_y + slot * index + (slot - node_height) / 2
            node_positions[node] = (x, y, node_height)
            label_x = x + node_width + 7 if layer <= max_layer / 2 else x - 7
            anchor = "start" if layer <= max_layer / 2 else "end"
            label = html.escape(truncate_svg_label(node, 26))
            value_text = html.escape(format_compact_currency(node_values.get(node), 1))
            title_text = html.escape(f"{node}: {format_compact_currency(node_values.get(node), 2)}")
            node_parts.append(
                f"<g><title>{title_text}</title>"
                f"<rect x='{x:.1f}' y='{y:.1f}' width='{node_width}' height='{node_height:.1f}' rx='5' "
                "fill='#10212a' stroke='#5ec7e8' stroke-opacity='0.55'/>"
                f"<text x='{label_x:.1f}' y='{y + node_height / 2 - 2:.1f}' text-anchor='{anchor}' "
                "fill='#e4eef0' font-size='13' font-weight='800'>"
                f"{label}</text>"
                f"<text x='{label_x:.1f}' y='{y + node_height / 2 + 14:.1f}' text-anchor='{anchor}' "
                "fill='#92aab2' font-size='11' font-weight='700'>"
                f"{value_text}</text></g>"
            )

    link_parts = []
    for link in visible_links:
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        if source not in node_positions or target not in node_positions:
            continue
        sx, sy, sh = node_positions[source]
        tx, ty, th = node_positions[target]
        start_x = sx + node_width
        start_y = sy + sh / 2
        end_x = tx
        end_y = ty + th / 2
        curve = max(40.0, abs(end_x - start_x) * 0.46)
        value = float(link.get("value") or 0)
        stroke_width = max(2.4, min(28.0, 2.0 + value / max_flow * 26.0))
        color = sankey_svg_color(link.get("tone"))
        label = (
            f"{source} -> {target}: "
            f"{format_compact_currency(link.get('raw_value'), 2)} "
            f"({format_percent(link.get('percent'), 1)})"
        )
        link_parts.append(
            f"<path d='M {start_x:.1f} {start_y:.1f} C {start_x + curve:.1f} {start_y:.1f}, "
            f"{end_x - curve:.1f} {end_y:.1f}, {end_x:.1f} {end_y:.1f}' "
            f"fill='none' stroke='{color}' stroke-width='{stroke_width:.1f}' stroke-linecap='round'>"
            f"<title>{html.escape(label)}</title></path>"
        )

    note = ""
    if len(links) > max_links:
        note = f"<div class='sankey-note'>Showing the {max_links} largest generated flow links out of {len(links)} total links.</div>"
    svg = (
        "<div class='sankey-svg-card'>"
        f"<svg class='sankey-svg' viewBox='0 0 {width} {height}' role='img' "
        f"aria-label='{html.escape(title)}'>"
        "<rect x='0' y='0' width='1180' height='430' rx='12' fill='#071014'/>"
        + "".join(link_parts)
        + "".join(node_parts)
        + "</svg>"
        + note
        + "</div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def add_sankey_link(
    links: list[dict[str, object]],
    source: str,
    target: str,
    value: float | None,
    *,
    base_value: float | None,
    tone: str = "neutral",
    raw_value: float | None = None,
    yoy: float | None = None,
) -> None:
    numeric = coerce_float(value)
    if numeric is None or abs(numeric) <= 0:
        return
    pct = safe_ratio(abs(numeric), abs(base_value), 100) if base_value else None
    links.append(
        {
            "source": source,
            "target": target,
            "value": abs(numeric),
            "raw_value": raw_value if raw_value is not None else numeric,
            "percent": pct,
            "tone": tone,
            "yoy": yoy,
        }
    )


def sankey_color(tone: str, alpha: float = 0.54) -> str:
    colors = {
        "inflow": f"rgba(73, 214, 155, {alpha})",
        "outflow": f"rgba(239, 111, 123, {alpha})",
        "neutral": f"rgba(94, 199, 232, {alpha})",
        "warning": f"rgba(230, 211, 111, {alpha})",
        "claim": f"rgba(155, 220, 243, {alpha})",
    }
    return colors.get(tone, colors["neutral"])


def make_sankey_figure(
    title: str,
    links: list[dict[str, object]],
    node_values: dict[str, float | None],
    *,
    height: int = 360,
) -> go.Figure | None:
    plotly_module = plotly_go()
    if plotly_module is None:
        return None
    if not links:
        return None
    node_lookup: dict[str, int] = {}
    nodes: list[str] = []
    for link in links:
        for node in (str(link["source"]), str(link["target"])):
            if node not in node_lookup:
                node_lookup[node] = len(nodes)
                nodes.append(node)
    customdata = [
        [
            format_compact_currency(link.get("raw_value"), 2),
            format_percent(link.get("percent"), 1),
            format_percent(link.get("yoy"), 1, signed=True),
        ]
        for link in links
    ]
    figure = plotly_module.Figure(
        data=[
            plotly_module.Sankey(
                arrangement="snap",
                node={
                    "pad": 14,
                    "thickness": 14,
                    "line": {"color": "#19313a", "width": 0.7},
                    "label": [sankey_node_name(node, node_values.get(node)) for node in nodes],
                    "color": [sankey_color("claim", 0.85) for _ in nodes],
                    "hovertemplate": "%{label}<extra></extra>",
                },
                link={
                    "source": [node_lookup[str(link["source"])] for link in links],
                    "target": [node_lookup[str(link["target"])] for link in links],
                    "value": [float(link["value"]) for link in links],
                    "color": [sankey_color(str(link.get("tone", "neutral"))) for link in links],
                    "customdata": customdata,
                    "hovertemplate": (
                        "%{source.label} -> %{target.label}<br>"
                        "Flow: %{customdata[0]}<br>"
                        "% of base: %{customdata[1]}<br>"
                        "YoY: %{customdata[2]}<extra></extra>"
                    ),
                },
            )
        ]
    )
    figure.update_layout(
        title={"text": title, "font": {"size": 14, "color": "#e4eef0"}},
        paper_bgcolor="#071013",
        plot_bgcolor="#071013",
        font={"color": "#d7e7e9", "family": "Inter, Segoe UI, Arial", "size": 11},
        margin={"l": 8, "r": 8, "t": 38, "b": 8},
        height=height,
    )
    return figure


def income_sankey_payload(normalized: pd.DataFrame) -> tuple[list[dict[str, object]], dict[str, float | None], list[str]]:
    revenue = sankey_value(normalized, "Revenue")
    cost = sankey_value(normalized, "Cost of Revenue")
    gross = sankey_value(normalized, "Gross Profit")
    operating_expenses = sankey_value(normalized, "Operating Expenses")
    operating_income = sankey_value(normalized, "Operating Income")
    pretax = sankey_value(normalized, "Pretax Income")
    taxes = sankey_value(normalized, "Taxes")
    net_income = sankey_value(normalized, "Net Income")
    base = revenue or gross or operating_income or net_income
    links: list[dict[str, object]] = []
    negative_notes = []

    if operating_expenses is None and gross is not None and operating_income is not None:
        operating_expenses = gross - operating_income
        normalized = set_derived_sankey_value(normalized, "Operating Expenses", operating_expenses, base, "Derived: Gross Profit - Operating Income")
    if pretax is None and net_income is not None and taxes is not None:
        pretax = net_income + taxes
        normalized = set_derived_sankey_value(normalized, "Pretax Income", pretax, base, "Derived: Net Income + Taxes")

    if revenue is not None:
        add_sankey_link(links, "Revenue", "Cost of Revenue", cost, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Cost of Revenue"))
        add_sankey_link(links, "Revenue", "Gross Profit", gross, base_value=base, tone="inflow", yoy=sankey_yoy(normalized, "Gross Profit"))
    if gross is not None:
        add_sankey_link(links, "Gross Profit", "Operating Expenses", operating_expenses, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Operating Expenses"))
        op_label = "Operating Income" if (operating_income or 0) >= 0 else "Operating Loss"
        if operating_income is not None and operating_income < 0:
            negative_notes.append("Operating loss")
        add_sankey_link(links, "Gross Profit", op_label, operating_income, base_value=base, tone="inflow" if (operating_income or 0) >= 0 else "outflow", yoy=sankey_yoy(normalized, "Operating Income"))
    for expense_label in ("R&D", "Sales & Marketing", "SG&A", "G&A", "Other Operating Expenses"):
        add_sankey_link(links, "Operating Expenses", expense_label, sankey_value(normalized, expense_label), base_value=base, tone="outflow", yoy=sankey_yoy(normalized, expense_label))

    op_source = "Operating Income" if (operating_income or 0) >= 0 else "Operating Loss"
    if pretax is not None:
        add_sankey_link(links, op_source, "Pretax Income", pretax, base_value=base, tone="neutral", yoy=sankey_yoy(normalized, "Pretax Income"))
        add_sankey_link(links, op_source, "Interest Expense", sankey_value(normalized, "Interest Expense"), base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Interest Expense"))
        add_sankey_link(links, "Interest Income", "Pretax Income", sankey_value(normalized, "Interest Income"), base_value=base, tone="inflow", yoy=sankey_yoy(normalized, "Interest Income"))
        other_income = sankey_value(normalized, "Other Income / Expense")
        if other_income is not None and other_income < 0:
            add_sankey_link(links, op_source, "Other Income / Expense", other_income, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Other Income / Expense"))
        else:
            add_sankey_link(links, "Other Income / Expense", "Pretax Income", other_income, base_value=base, tone="inflow", yoy=sankey_yoy(normalized, "Other Income / Expense"))

    pretax_source = "Pretax Income" if pretax is not None else op_source
    net_label = "Net Income" if (net_income or 0) >= 0 else "Net Loss"
    if net_income is not None and net_income < 0:
        negative_notes.append("Net loss")
    add_sankey_link(links, pretax_source, "Taxes", taxes, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Taxes"))
    add_sankey_link(links, pretax_source, net_label, net_income, base_value=base, tone="inflow" if (net_income or 0) >= 0 else "outflow", yoy=sankey_yoy(normalized, "Net Income"))

    node_values = {
        "Revenue": revenue,
        "Cost of Revenue": cost,
        "Gross Profit": gross,
        "Operating Expenses": operating_expenses,
        "Operating Income": operating_income if (operating_income or 0) >= 0 else None,
        "Operating Loss": operating_income if operating_income is not None and operating_income < 0 else None,
        "Pretax Income": pretax,
        "Taxes": taxes,
        "Net Income": net_income if (net_income or 0) >= 0 else None,
        "Net Loss": net_income if net_income is not None and net_income < 0 else None,
    }
    for label in ("R&D", "Sales & Marketing", "SG&A", "G&A", "Other Operating Expenses", "Interest Expense", "Interest Income", "Other Income / Expense"):
        node_values[label] = sankey_value(normalized, label)
    return links, node_values, negative_notes


def balance_sankey_payload(normalized: pd.DataFrame) -> tuple[list[dict[str, object]], dict[str, float | None], list[str]]:
    total_assets = sankey_value(normalized, "Total Assets")
    current_assets = sankey_value(normalized, "Current Assets")
    cash = sankey_value(normalized, "Cash")
    receivables = sankey_value(normalized, "Accounts Receivable")
    inventory = sankey_value(normalized, "Inventory")
    non_current_assets = sankey_value(normalized, "Non-current Assets")
    total_liabilities = sankey_value(normalized, "Total Liabilities")
    current_liabilities = sankey_value(normalized, "Current Liabilities")
    long_debt = sankey_value(normalized, "Long-term Debt")
    short_debt = sankey_value(normalized, "Short-term Debt")
    total_debt = sankey_value(normalized, "Total Debt")
    equity = sankey_value(normalized, "Shareholders' Equity")
    if non_current_assets is None and total_assets is not None and current_assets is not None:
        non_current_assets = total_assets - current_assets
        normalized = set_derived_sankey_value(normalized, "Non-current Assets", non_current_assets, total_assets, "Derived: Total Assets - Current Assets")
    if total_debt is None:
        debt_parts = [value for value in (long_debt, short_debt) if value is not None]
        if debt_parts:
            total_debt = sum(debt_parts)
            normalized = set_derived_sankey_value(normalized, "Total Debt", total_debt, total_assets, "Derived: Long-term Debt + Short-term Debt")
    other_current_assets = sankey_value(normalized, "Other Current Assets")
    if other_current_assets is None and current_assets is not None:
        component_sum = sum(value for value in (cash, receivables, inventory) if value is not None)
        other_current_assets = current_assets - component_sum
        normalized = set_derived_sankey_value(normalized, "Other Current Assets", other_current_assets, total_assets, "Derived residual current assets")
    other_liabilities = sankey_value(normalized, "Other Liabilities")
    if other_liabilities is None and total_liabilities is not None:
        component_sum = sum(value for value in (current_liabilities, long_debt, short_debt) if value is not None)
        other_liabilities = total_liabilities - component_sum
        normalized = set_derived_sankey_value(normalized, "Other Liabilities", other_liabilities, total_assets, "Derived residual liabilities")

    links: list[dict[str, object]] = []
    base = total_assets or total_liabilities or equity
    add_sankey_link(links, "Total Assets", "Current Assets", current_assets, base_value=base, tone="neutral", yoy=sankey_yoy(normalized, "Current Assets"))
    add_sankey_link(links, "Total Assets", "Non-current Assets", non_current_assets, base_value=base, tone="neutral", yoy=sankey_yoy(normalized, "Non-current Assets"))
    for label, value in (
        ("Cash", cash),
        ("Accounts Receivable", receivables),
        ("Inventory", inventory),
        ("Other Current Assets", other_current_assets),
    ):
        add_sankey_link(links, "Current Assets", label, value, base_value=base, tone="inflow", yoy=sankey_yoy(normalized, label))

    add_sankey_link(links, "Total Assets", "Assets = Liabilities + Equity", total_assets, base_value=base, tone="claim")
    add_sankey_link(links, "Assets = Liabilities + Equity", "Total Liabilities", total_liabilities, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Total Liabilities"))
    add_sankey_link(links, "Assets = Liabilities + Equity", "Shareholders' Equity", equity, base_value=base, tone="inflow", yoy=sankey_yoy(normalized, "Shareholders' Equity"))
    add_sankey_link(links, "Total Liabilities", "Current Liabilities", current_liabilities, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Current Liabilities"))
    add_sankey_link(links, "Total Liabilities", "Long-term Debt", long_debt, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Long-term Debt"))
    add_sankey_link(links, "Total Liabilities", "Short-term Debt", short_debt, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Short-term Debt"))
    add_sankey_link(links, "Total Liabilities", "Other Liabilities", other_liabilities, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Other Liabilities"))

    node_values = {
        "Total Assets": total_assets,
        "Current Assets": current_assets,
        "Cash": cash,
        "Accounts Receivable": receivables,
        "Inventory": inventory,
        "Other Current Assets": other_current_assets,
        "Non-current Assets": non_current_assets,
        "Assets = Liabilities + Equity": total_assets,
        "Total Liabilities": total_liabilities,
        "Current Liabilities": current_liabilities,
        "Long-term Debt": long_debt,
        "Short-term Debt": short_debt,
        "Other Liabilities": other_liabilities,
        "Shareholders' Equity": equity,
    }
    return links, node_values, []


def cash_flow_sankey_payload(normalized: pd.DataFrame) -> tuple[list[dict[str, object]], dict[str, float | None], list[str]]:
    net_income = sankey_value(normalized, "Net Income")
    ocf = sankey_value(normalized, "Operating Cash Flow")
    capex = sankey_value(normalized, "Capital Expenditures")
    fcf = sankey_value(normalized, "Free Cash Flow")
    investing = sankey_value(normalized, "Investing Cash Flow")
    financing = sankey_value(normalized, "Financing Cash Flow")
    dividends = sankey_value(normalized, "Dividends")
    buybacks = sankey_value(normalized, "Buybacks")
    debt_issuance = sankey_value(normalized, "Debt Issuance")
    debt_repayment = sankey_value(normalized, "Debt Repayment")
    net_change = sankey_value(normalized, "Net Change in Cash")
    base = ocf or net_change or fcf or net_income
    if fcf is None and ocf is not None and capex is not None:
        fcf = ocf + capex
        normalized = set_derived_sankey_value(normalized, "Free Cash Flow", fcf, base, "Derived: Operating Cash Flow + Capital Expenditures")

    links: list[dict[str, object]] = []
    negative_notes = []
    add_sankey_link(links, "Net Income", "Operating Cash Flow", ocf, base_value=base, tone="inflow", yoy=sankey_yoy(normalized, "Operating Cash Flow"))
    add_sankey_link(links, "Operating Cash Flow", "Capital Expenditures", capex, base_value=base, tone="outflow", yoy=sankey_yoy(normalized, "Capital Expenditures"))
    add_sankey_link(links, "Operating Cash Flow", "Free Cash Flow", fcf, base_value=base, tone="inflow" if (fcf or 0) >= 0 else "outflow", yoy=sankey_yoy(normalized, "Free Cash Flow"))

    net_change_label = "Net Change in Cash" if (net_change or 0) >= 0 else "Net Cash Outflow"
    for label, value in (("Operating Cash Flow", ocf), ("Investing Cash Flow", investing), ("Financing Cash Flow", financing)):
        if value is not None and value < 0:
            negative_notes.append(f"{label} outflow")
        add_sankey_link(links, label, net_change_label, value, base_value=base, tone="inflow" if (value or 0) >= 0 else "outflow", yoy=sankey_yoy(normalized, label))
    for label, value, tone in (
        ("Debt Issuance", debt_issuance, "inflow"),
        ("Debt Repayment", debt_repayment, "outflow"),
        ("Buybacks", buybacks, "outflow"),
        ("Dividends", dividends, "outflow"),
    ):
        add_sankey_link(links, "Financing Cash Flow", label, value, base_value=base, tone=tone, yoy=sankey_yoy(normalized, label))
        if value is not None and value < 0:
            negative_notes.append(label)

    node_values = {
        "Net Income": net_income,
        "Operating Cash Flow": ocf,
        "Capital Expenditures": capex,
        "Free Cash Flow": fcf,
        "Investing Cash Flow": investing,
        "Financing Cash Flow": financing,
        "Debt Issuance": debt_issuance,
        "Debt Repayment": debt_repayment,
        "Buybacks": buybacks,
        "Dividends": dividends,
        "Net Change in Cash": net_change if (net_change or 0) >= 0 else None,
        "Net Cash Outflow": net_change if net_change is not None and net_change < 0 else None,
    }
    return links, node_values, negative_notes


def statement_display_frame(financial_df: pd.DataFrame) -> pd.DataFrame:
    if financial_df.empty:
        return financial_df
    display = financial_df.copy()
    value_columns = [column for column in display.columns if column not in {"Period", "Period Date"}]
    if value_columns:
        display = display[display[value_columns].notna().any(axis=1)]
    if "Period Date" in display:
        display = display.sort_values("Period Date", ascending=False, kind="mergesort")
    return display.reset_index(drop=True)


def ratio_frame(financial_df: pd.DataFrame) -> pd.DataFrame:
    if financial_df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in financial_df.iterrows():
        revenue = row.get("Revenue")
        gross_profit = row.get("Gross Profit")
        operating_income = row.get("Operating Income")
        net_income = row.get("Net Income")
        free_cash_flow = row.get("Free Cash Flow")
        current_assets = row.get("Current Assets")
        current_liabilities = row.get("Current Liabilities")
        debt = row.get("Total Debt")
        cash = row.get("Cash")
        equity = row.get("Stockholders Equity")
        assets = row.get("Total Assets")
        rows.append(
            {
                "Period": row.get("Period"),
                "Gross Margin %": safe_ratio(gross_profit, revenue, 100),
                "Operating Margin %": safe_ratio(operating_income, revenue, 100),
                "Net Margin %": safe_ratio(net_income, revenue, 100),
                "FCF Margin %": safe_ratio(free_cash_flow, revenue, 100),
                "Current Ratio": safe_ratio(current_assets, current_liabilities),
                "Debt / Equity": safe_ratio(debt, equity),
                "Cash / Debt": safe_ratio(cash, debt),
                "Asset Turnover": safe_ratio(revenue, assets),
            }
        )
    return pd.DataFrame(rows)


def latest_financial_metrics(financial_df: pd.DataFrame, ratios: pd.DataFrame, info: dict) -> dict:
    latest = financial_df.iloc[-1].to_dict() if not financial_df.empty else {}
    latest_ratios = ratios.iloc[-1].to_dict() if not ratios.empty else {}
    revenue_series = pd.Series(financial_df["Revenue"].dropna().values) if "Revenue" in financial_df else pd.Series(dtype=float)
    net_income_series = pd.Series(financial_df["Net Income"].dropna().values) if "Net Income" in financial_df else pd.Series(dtype=float)
    free_cash_flow_series = pd.Series(financial_df["Free Cash Flow"].dropna().values) if "Free Cash Flow" in financial_df else pd.Series(dtype=float)

    return {
        "Market Cap": coerce_float(info.get("marketCap") or info.get("market_cap")),
        "Enterprise Value": coerce_float(info.get("enterpriseValue")),
        "Trailing PE": coerce_float(info.get("trailingPE")),
        "Forward PE": coerce_float(info.get("forwardPE")),
        "Price / Sales": coerce_float(info.get("priceToSalesTrailing12Months")),
        "EV / EBITDA": coerce_float(info.get("enterpriseToEbitda")),
        "Dividend Yield %": safe_ratio(coerce_float(info.get("dividendYield")), 1, 100),
        "Revenue": latest.get("Revenue"),
        "Revenue Growth %": latest_growth(revenue_series),
        "Net Income": latest.get("Net Income"),
        "Net Income Growth %": latest_growth(net_income_series),
        "Free Cash Flow": latest.get("Free Cash Flow"),
        "FCF Growth %": latest_growth(free_cash_flow_series),
        "Net Margin %": latest_ratios.get("Net Margin %"),
        "FCF Margin %": latest_ratios.get("FCF Margin %"),
        "Current Ratio": latest_ratios.get("Current Ratio"),
        "Debt / Equity": latest_ratios.get("Debt / Equity"),
        "Cash / Debt": latest_ratios.get("Cash / Debt"),
    }


def financial_health_score(metrics: dict) -> tuple[int, list[str]]:
    score = 50
    notes = []
    checks = (
        ("Revenue Growth %", 0, 10, "revenue growth"),
        ("Net Income Growth %", 0, 8, "net income growth"),
        ("Net Margin %", 10, 10, "double-digit net margin"),
        ("FCF Margin %", 5, 8, "positive free-cash-flow margin"),
        ("Current Ratio", 1, 6, "current ratio above 1"),
        ("Cash / Debt", 0.5, 5, "cash covers meaningful debt"),
    )
    for key, threshold, points, label in checks:
        value = metrics.get(key)
        if value is not None and not pd.isna(value) and value >= threshold:
            score += points
            notes.append(label)
    debt_equity = metrics.get("Debt / Equity")
    if debt_equity is not None and not pd.isna(debt_equity):
        if debt_equity <= 1.5:
            score += 8
            notes.append("manageable leverage")
        elif debt_equity > 3:
            score -= 10
    if metrics.get("Free Cash Flow") is not None and metrics["Free Cash Flow"] < 0:
        score -= 8
    return max(0, min(100, int(score))), notes


def score_driver_items(score_notes: list[str], metrics: dict) -> list[dict[str, str]]:
    driver_values = {
        "revenue growth": {
            "label": "Revenue Growth",
            "value": format_percent(metrics.get("Revenue Growth %"), signed=True),
        },
        "net income growth": {
            "label": "Net Income Growth",
            "value": format_percent(metrics.get("Net Income Growth %"), signed=True),
        },
        "double-digit net margin": {
            "label": "Net Margin",
            "value": format_percent(metrics.get("Net Margin %")),
        },
        "positive free-cash-flow margin": {
            "label": "FCF Margin",
            "value": format_percent(metrics.get("FCF Margin %")),
        },
        "current ratio above 1": {
            "label": "Current Ratio",
            "value": format_number(metrics.get("Current Ratio")),
        },
        "cash covers meaningful debt": {
            "label": "Cash / Debt",
            "value": format_number(metrics.get("Cash / Debt")),
        },
        "manageable leverage": {
            "label": "Debt / Equity",
            "value": format_number(metrics.get("Debt / Equity")),
        },
    }
    return [
        driver_values.get(note, {"label": note.title(), "value": "Included"})
        for note in score_notes[:6]
    ]


def estimate_period_for_year(target_year: int) -> str | None:
    current_year = date.today().year
    if target_year <= current_year:
        return "0y"
    if target_year == current_year + 1:
        return "+1y"
    return None


def estimate_value(frame: pd.DataFrame, period_key: str | None, column: str) -> float | None:
    if frame.empty or not period_key or period_key not in frame.index or column not in frame:
        return None
    return coerce_float(frame.loc[period_key, column])


def actual_sum(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.sum())


def target_progress(actual: float | None, target: float | None) -> float | None:
    if actual is None or target is None or pd.isna(actual) or pd.isna(target) or target == 0:
        return None
    return actual / abs(target) * 100


def target_variance(actual: float | None, target: float | None) -> float | None:
    if actual is None or target is None or pd.isna(actual) or pd.isna(target):
        return None
    return actual - target


def actual_quarters_for_target_year(
    quarterly_financial_df: pd.DataFrame,
    annual_financial_df: pd.DataFrame,
    target_year: int,
) -> pd.DataFrame:
    if quarterly_financial_df.empty or "Period Date" not in quarterly_financial_df:
        return pd.DataFrame()

    period_dates = pd.to_datetime(quarterly_financial_df["Period Date"], errors="coerce")
    if (
        target_year >= date.today().year
        and not annual_financial_df.empty
        and "Period Date" in annual_financial_df
    ):
        annual_dates = pd.to_datetime(annual_financial_df["Period Date"], errors="coerce").dropna()
        if not annual_dates.empty:
            latest_annual_date = annual_dates.max()
            current_fiscal_quarters = quarterly_financial_df[period_dates > latest_annual_date]
            if not current_fiscal_quarters.empty:
                return current_fiscal_quarters

    return quarterly_financial_df[period_dates.dt.year == target_year]


def actual_quarter_rows(
    quarterly_financial_df: pd.DataFrame,
    annual_financial_df: pd.DataFrame,
    target_year: int,
) -> dict[int, dict]:
    actual_quarters = actual_quarters_for_target_year(
        quarterly_financial_df,
        annual_financial_df,
        target_year,
    )
    if actual_quarters.empty:
        return {}
    actual_quarters = actual_quarters.copy()
    actual_quarters["Period Date"] = pd.to_datetime(actual_quarters["Period Date"], errors="coerce")
    actual_quarters = actual_quarters.sort_values("Period Date").head(4)
    return {
        index + 1: row.to_dict()
        for index, (_, row) in enumerate(actual_quarters.iterrows())
    }


def format_target_value(value: float | None, value_type: str) -> str:
    if value_type == "currency":
        return format_currency(value, 0)
    if value_type == "eps":
        return format_currency(value, 2)
    if value_type == "price":
        return format_currency(value, 2)
    if value_type == "percent":
        return format_percent(value)
    return format_number(value)


def estimate_quarter_targets(
    estimate_frame: pd.DataFrame,
    annual_target: float | None,
    actual_by_quarter: dict[int, float | None],
    reported_quarters: int,
    target_label: str,
) -> tuple[dict[int, float | None], dict[int, str]]:
    targets: dict[int, float | None] = {}
    sources: dict[int, str] = {}
    next_quarter = min(reported_quarters + 1, 4)

    current_quarter_target = estimate_value(estimate_frame, "0q", "avg")
    if current_quarter_target is not None and next_quarter <= 4:
        targets[next_quarter] = current_quarter_target
        sources[next_quarter] = f"Analyst {target_label} estimate"

    next_quarter_target = estimate_value(estimate_frame, "+1q", "avg")
    if next_quarter_target is not None and next_quarter + 1 <= 4:
        targets[next_quarter + 1] = next_quarter_target
        sources[next_quarter + 1] = f"Analyst next-quarter {target_label} estimate"

    if annual_target is None:
        return targets, sources

    actual_total = sum(
        value
        for value in actual_by_quarter.values()
        if value is not None and not pd.isna(value)
    )
    assigned_total = sum(
        value
        for value in targets.values()
        if value is not None and not pd.isna(value)
    )
    remaining_quarters = [
        quarter
        for quarter in range(1, 5)
        if quarter not in actual_by_quarter and quarter not in targets
    ]
    if remaining_quarters:
        implied_target = (annual_target - actual_total - assigned_total) / len(remaining_quarters)
        for quarter in remaining_quarters:
            targets[quarter] = implied_target
            sources[quarter] = f"Implied from annual {target_label} target"

    return targets, sources


def eps_targets_from_history(
    earnings_expectations: pd.DataFrame,
    actual_rows: dict[int, dict],
) -> tuple[dict[int, float | None], dict[int, str]]:
    if earnings_expectations.empty or "Report Date" not in earnings_expectations:
        return {}, {}
    targets: dict[int, float | None] = {}
    sources: dict[int, str] = {}
    expectations = earnings_expectations.copy()
    expectations["Report Date"] = pd.to_datetime(expectations["Report Date"], errors="coerce")
    for quarter, row in actual_rows.items():
        period_date = pd.to_datetime(row.get("Period Date"), errors="coerce")
        if pd.isna(period_date):
            continue
        exact = expectations[expectations["Report Date"].dt.date == period_date.date()]
        if exact.empty:
            exact = expectations[
                (expectations["Report Date"].dt.year == period_date.year)
                & (expectations["Report Date"].dt.quarter == period_date.quarter)
            ]
        if exact.empty:
            continue
        estimate = coerce_float(exact.iloc[0].get("EPS Estimate"))
        if estimate is not None:
            targets[quarter] = estimate
            sources[quarter] = "Reported quarter EPS estimate"
    return targets, sources


def build_quarterly_actuals_targets_breakout(
    quarterly_financial_df: pd.DataFrame,
    annual_financial_df: pd.DataFrame,
    revenue_estimate: pd.DataFrame,
    earnings_estimate: pd.DataFrame,
    earnings_expectations: pd.DataFrame,
    target_year: int,
) -> pd.DataFrame:
    actual_rows = actual_quarter_rows(
        quarterly_financial_df,
        annual_financial_df,
        target_year,
    )
    reported_quarters = len(actual_rows)
    revenue_actuals = {
        quarter: coerce_float(row.get("Revenue"))
        for quarter, row in actual_rows.items()
    }
    eps_actuals = {
        quarter: coerce_float(row.get("Diluted EPS"))
        for quarter, row in actual_rows.items()
    }

    annual_period = estimate_period_for_year(target_year)
    revenue_targets, revenue_sources = estimate_quarter_targets(
        revenue_estimate,
        estimate_value(revenue_estimate, annual_period, "avg"),
        revenue_actuals,
        reported_quarters,
        "revenue",
    )
    eps_targets, eps_sources = estimate_quarter_targets(
        earnings_estimate,
        estimate_value(earnings_estimate, annual_period, "avg"),
        eps_actuals,
        reported_quarters,
        "EPS",
    )
    historical_eps_targets, historical_eps_sources = eps_targets_from_history(
        earnings_expectations,
        actual_rows,
    )
    eps_targets.update(historical_eps_targets)
    eps_sources.update(historical_eps_sources)

    rows = []
    for quarter in range(1, 5):
        actual_row = actual_rows.get(quarter, {})
        period_date = actual_row.get("Period Date")
        revenue_actual = revenue_actuals.get(quarter)
        revenue_target = revenue_targets.get(quarter)
        eps_actual = eps_actuals.get(quarter)
        eps_target = eps_targets.get(quarter)
        rows.append(
            {
                "Quarter": f"Q{quarter} {target_year}",
                "Period Date": period_date,
                "Revenue Actual": revenue_actual,
                "Revenue Target": revenue_target,
                "Revenue Variance": target_variance(revenue_actual, revenue_target),
                "Revenue Progress %": target_progress(revenue_actual, revenue_target),
                "EPS Actual": eps_actual,
                "EPS Target": eps_target,
                "EPS Variance": target_variance(eps_actual, eps_target),
                "EPS Progress %": target_progress(eps_actual, eps_target),
                "Target Source": "; ".join(
                    sorted(
                        {
                            source
                            for source in [
                                revenue_sources.get(quarter),
                                eps_sources.get(quarter),
                            ]
                            if source
                        }
                    )
                ) or "N/A",
            }
        )
    return pd.DataFrame(rows)


def build_actuals_targets_frame(
    quarterly_financial_df: pd.DataFrame,
    annual_financial_df: pd.DataFrame,
    revenue_estimate: pd.DataFrame,
    earnings_estimate: pd.DataFrame,
    info: dict,
    target_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_year = actual_quarters_for_target_year(
        quarterly_financial_df,
        annual_financial_df,
        target_year,
    )

    period_key = estimate_period_for_year(target_year)
    revenue_actual = actual_sum(actual_year, "Revenue")
    net_income_actual = actual_sum(actual_year, "Net Income")
    ocf_actual = actual_sum(actual_year, "Operating Cash Flow")
    fcf_actual = actual_sum(actual_year, "Free Cash Flow")
    eps_actual = actual_sum(actual_year, "Diluted EPS")

    rows = [
        {
            "Metric": "Revenue",
            "Actual": revenue_actual,
            "Target": estimate_value(revenue_estimate, period_key, "avg"),
            "Target Low": estimate_value(revenue_estimate, period_key, "low"),
            "Target High": estimate_value(revenue_estimate, period_key, "high"),
            "Progress %": target_progress(revenue_actual, estimate_value(revenue_estimate, period_key, "avg")),
            "Type": "currency",
            "Source": "Reported quarters + analyst revenue estimate",
        },
        {
            "Metric": "Diluted EPS",
            "Actual": eps_actual,
            "Target": estimate_value(earnings_estimate, period_key, "avg"),
            "Target Low": estimate_value(earnings_estimate, period_key, "low"),
            "Target High": estimate_value(earnings_estimate, period_key, "high"),
            "Progress %": target_progress(eps_actual, estimate_value(earnings_estimate, period_key, "avg")),
            "Type": "eps",
            "Source": "Reported quarters + analyst EPS estimate",
        },
        {
            "Metric": "Net Income",
            "Actual": net_income_actual,
            "Target": None,
            "Target Low": None,
            "Target High": None,
            "Progress %": None,
            "Type": "currency",
            "Source": "Reported quarters",
        },
        {
            "Metric": "Operating Cash Flow",
            "Actual": ocf_actual,
            "Target": None,
            "Target Low": None,
            "Target High": None,
            "Progress %": None,
            "Type": "currency",
            "Source": "Reported quarters",
        },
        {
            "Metric": "Free Cash Flow",
            "Actual": fcf_actual,
            "Target": None,
            "Target Low": None,
            "Target High": None,
            "Progress %": None,
            "Type": "currency",
            "Source": "Reported quarters",
        },
    ]
    actuals_targets = pd.DataFrame(rows)

    last_price = coerce_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    price_target = pd.DataFrame(
        [
            {
                "Metric": "Stock Price",
                "Actual": last_price,
                "Target": coerce_float(info.get("targetMeanPrice")),
                "Target Low": coerce_float(info.get("targetLowPrice")),
                "Target High": coerce_float(info.get("targetHighPrice")),
                "Progress %": target_progress(last_price, coerce_float(info.get("targetMeanPrice"))),
                "Type": "price",
                "Source": "Analyst price targets",
            }
        ]
    )
    return actuals_targets, price_target


def format_actuals_targets_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    display = frame.copy()
    for column in ["Actual", "Target", "Target Low", "Target High"]:
        display[column] = display.apply(
            lambda row: format_target_value(row[column], row["Type"]),
            axis=1,
        )
    display["Progress %"] = display["Progress %"].map(lambda value: format_percent(value, 1))
    return display.drop(columns=["Type"])


def format_quarterly_breakout_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    display = frame.copy()
    display["Period Date"] = pd.to_datetime(display["Period Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    display["Period Date"] = display["Period Date"].fillna("N/A")
    for column in ["Revenue Actual", "Revenue Target", "Revenue Variance"]:
        display[column] = display[column].map(lambda value: format_currency(value, 0))
    for column in ["EPS Actual", "EPS Target", "EPS Variance"]:
        display[column] = display[column].map(lambda value: format_currency(value, 2))
    for column in ["Revenue Progress %", "EPS Progress %"]:
        display[column] = display[column].map(lambda value: format_percent(value, 1))
    return display.fillna("N/A")


def data_health_frame(payloads: Iterable[dict], feed_statuses: Iterable[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    market_rows = []
    for payload in payloads:
        history = payload.get("history", empty_history())
        market_rows.append(
            {
                "Ticker": payload.get("ticker"),
                "Exchange": payload.get("exchange", ""),
                "Index Membership": payload.get("index_membership", ""),
                "Status": payload.get("status"),
                "History Bars": 0 if history is None else len(history),
                "Earnings Dates": len(payload.get("earnings_dates", [])),
                "Options Expiry": (payload.get("options") or {}).get("expiry"),
                "Options Message": (payload.get("options") or {}).get("message", ""),
                "30D Options Expiry": (payload.get("options_30d") or {}).get("expiry"),
                "30D Options Message": (payload.get("options_30d") or {}).get("message", ""),
                "Message": payload.get("message", ""),
            }
        )
    return sort_status_frame(pd.DataFrame(market_rows)), sort_status_frame(pd.DataFrame(feed_statuses))


def article_card_html(article: Article) -> str:
    sentiment_class = article.sentiment.lower()
    mentions = " ".join(f"<span class='ticker-chip'>{html.escape(ticker)}</span>" for ticker in article.mentions)
    factors = " ".join(
        f"<span class='factor-chip'>{html.escape(factor)}</span>"
        for factor in article_categories(article)
        if factor != "Company / Stock"
    )
    title = html.escape(article.title)
    source = html.escape(article.source)
    age = html.escape(format_age(article.published))
    link = html.escape(article.link, quote=True)

    return (
        f'<article class="news-card {sentiment_class}" role="listitem">'
        f'<div class="card-topline">'
        f"<span>{source}</span>"
        f"<span>{age}</span>"
        f'<span class="sentiment-pill {sentiment_class}">{html.escape(article.sentiment)}</span>'
        f"</div>"
        f'<a class="headline" href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>'
        f'<div class="ticker-row">{mentions}{factors}</div>'
        f"</article>"
    )


def render_article(article: Article) -> None:
    st.markdown(
        article_card_html(article),
        unsafe_allow_html=True,
    )


def render_market_macro_headlines(
    articles: Sequence[Article],
    statuses: Sequence[dict],
    refreshed_at: datetime,
    *,
    key_prefix: str,
    title: str = "Market & Macro Headlines",
    subtitle: str = "Reputable market and macro feeds sorted newest first.",
    compact: bool = False,
    limit: int = 10,
    default_keyword: str = "",
    show_debug: bool = False,
    stats: dict[str, object] | None = None,
) -> dict[str, object]:
    render_section_title(title, subtitle)

    def controls() -> tuple[list[str], list[str], list[str], str, str]:
        source_options = sorted({article.source for article in articles})
        type_options = sorted({category for article in articles for category in article_categories(article)})
        sentiment_options = sorted({article.sentiment for article in articles})
        filter_cols = st.columns([1, 1, 0.82, 0.88, 1], gap="small")
        with filter_cols[0]:
            selected_sources = st.multiselect("Source", source_options, default=[], key=f"{key_prefix}_sources")
        with filter_cols[1]:
            selected_types = st.multiselect("News Type", type_options, default=[], key=f"{key_prefix}_types")
        with filter_cols[2]:
            selected_sentiments = st.multiselect("Sentiment", sentiment_options, default=[], key=f"{key_prefix}_sentiments")
        with filter_cols[3]:
            selected_range = st.selectbox(
                "Date Range",
                ["Today", "This Week", "Last 30 Days", "All"],
                index=2,
                key=f"{key_prefix}_range",
            )
        with filter_cols[4]:
            keyword = st.text_input(
                "Ticker / keyword",
                value=default_keyword,
                key=f"{key_prefix}_keyword",
                placeholder="Optional",
            )
        return selected_sources, selected_types, selected_sentiments, selected_range, keyword

    if compact:
        with st.expander("Headline filters", expanded=False):
            selected_sources, selected_types, selected_sentiments, selected_range, keyword = controls()
    else:
        selected_sources, selected_types, selected_sentiments, selected_range, keyword = controls()

    filtered_articles = filter_articles(
        articles,
        selected_sources,
        selected_types,
        selected_sentiments,
        selected_range,
        keyword,
    )
    displayed_articles = filtered_articles[:limit]
    source_names = sorted({article.source for article in filtered_articles})
    st.caption(
        f"Showing {len(displayed_articles):,} of {len(filtered_articles):,} matching headlines "
        f"({len(articles):,} quality-filtered) | Last refreshed: "
        f"{refreshed_at.strftime('%I:%M:%S %p ET').lstrip('0')} | Sources: {', '.join(source_names) or 'N/A'}"
    )
    if not displayed_articles:
        st.info("No headlines match the current filters.")
    else:
        if compact:
            st.markdown(
                "<div class='headline-scroll' role='list' aria-label='Scrollable market and macro headline list'>"
                + "".join(article_card_html(article) for article in displayed_articles)
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            for article in displayed_articles:
                render_article(article)

    if compact and len(filtered_articles) > limit:
        with st.expander("View more headlines", expanded=False):
            for article in filtered_articles[limit : min(len(filtered_articles), limit + 24)]:
                render_article(article)

    if show_debug:
        newest, oldest = article_timestamp_bounds(filtered_articles)
        source_counts = Counter(article.source for article in articles)
        debug_rows = [
            {"Metric": "Raw headlines fetched", "Value": (stats or {}).get("raw_count", "N/A")},
            {"Metric": "Quality-filtered out", "Value": (stats or {}).get("filtered_out", "N/A")},
            {"Metric": "Quality-filtered kept", "Value": len(articles)},
            {"Metric": "Headlines after UI filters", "Value": len(filtered_articles)},
            {"Metric": "Headlines displayed", "Value": len(displayed_articles)},
            {"Metric": "Headline summaries hidden", "Value": True},
            {"Metric": "HTML-like summaries detected", "Value": sum(1 for article in filtered_articles if re.search(r"<[^>]+>|&lt;[^&]+&gt;|\b(ticker-row|factor-chip|news-card|metric-cell)\b", str(article.summary or ""), flags=re.IGNORECASE))},
            {"Metric": "Newest timestamp", "Value": newest},
            {"Metric": "Oldest timestamp", "Value": oldest},
            {"Metric": "Sort", "Value": "Published timestamp descending; undated last"},
        ]
        with st.expander(f"{title} diagnostics", expanded=False):
            render_dashboard_table(pd.DataFrame(debug_rows), height=280)
            if source_counts:
                render_dashboard_table(
                    pd.DataFrame(
                        [{"Source": source, "Headlines": count} for source, count in sorted(source_counts.items())]
                    ),
                    height=240,
                )
            if statuses:
                status_df = pd.DataFrame(statuses).rename(
                    columns={"source": "Source", "status": "Status", "message": "Message", "articles": "Articles"}
                )
                render_dashboard_table(status_df, height=240)

    return {
        "filtered_count": len(filtered_articles),
        "displayed_count": len(displayed_articles),
        "sources": source_names,
        "summaries_hidden": True,
        "html_summary_count": sum(
            1
            for article in filtered_articles
            if re.search(r"<[^>]+>|&lt;[^&]+&gt;|\b(ticker-row|factor-chip|news-card|metric-cell)\b", str(article.summary or ""), flags=re.IGNORECASE)
        ),
    }


def render_social_mention(mention: SocialMention) -> None:
    sentiment_class = mention.sentiment.lower()
    mentions = " ".join(f"<span class='ticker-chip'>{html.escape(ticker)}</span>" for ticker in mention.mentions)
    body = html.escape(mention.body[:170])
    if mention.body and len(mention.body) > 170:
        body = f"{body}..."
    title = html.escape(mention.title)
    source = html.escape(mention.source)
    age = html.escape(format_age(mention.published))
    link = html.escape(mention.link, quote=True)
    engagement = get_total_reactions(mention)

    st.markdown(
        f"""
        <article class="news-card {sentiment_class}">
            <div class="card-topline">
                <span>{source}</span>
                <span>{age}</span>
                <span class="sentiment-pill {sentiment_class}">{mention.sentiment}</span>
                <span>{engagement} engagement</span>
            </div>
            <a class="headline" href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>
            <p class="summary">{body}</p>
            <div class="ticker-row">{mentions}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --term-bg: #071013;
                --term-panel: #0c171b;
                --term-panel-2: #101f25;
                --term-line: #23424d;
                --term-line-soft: #19313a;
                --term-amber: #5ec7e8;
                --term-amber-soft: #3f9fbb;
                --term-green: #49d69b;
                --term-red: #ef6f7b;
                --term-text: #e4eef0;
                --term-muted: #92aab2;
                --term-blue: #9bdcf3;
                --card-bg: #0b171c;
                --card-bg-soft: #0f1e24;
            }

            html {
                scroll-behavior: smooth;
            }

            .stApp {
                background: var(--term-bg);
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                scroll-behavior: smooth;
            }

            header[data-testid="stHeader"] {
                background: rgba(3, 3, 3, 0.94);
                border-bottom: 1px solid var(--term-line-soft);
            }

            .block-container {
                max-width: 1680px;
                padding: 0.7rem 1rem 1.35rem 1rem;
            }

            h1, h2, h3, p, li, label, span, div {
                letter-spacing: 0;
            }

            .headline-scroll {
                max-height: 34rem;
                overscroll-behavior: contain;
                overflow-y: auto;
                padding-right: 0.18rem;
                scroll-behavior: smooth;
                scrollbar-color: var(--term-line) transparent;
                scrollbar-gutter: stable;
                scrollbar-width: thin;
                -webkit-overflow-scrolling: touch;
            }

            .headline-scroll::-webkit-scrollbar {
                width: 8px;
            }

            .headline-scroll::-webkit-scrollbar-thumb {
                background: var(--term-line);
                border-radius: 999px;
            }

            .headline-scroll::-webkit-scrollbar-track {
                background: transparent;
            }

            .home-aligned-card {
                min-height: 34rem;
            }

            .home-ticker-control {
                margin: 0 0 0.45rem 0;
            }

            h1,
            [data-testid="stMarkdownContainer"] h1 {
                border-bottom: 1px solid var(--term-line);
                color: var(--term-amber);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 1.45rem !important;
                line-height: 1.15;
                margin: 0 0 0.25rem 0 !important;
                padding-bottom: 0.35rem;
                text-transform: none;
            }

            h2, h3 {
                color: var(--term-amber);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.92rem;
                line-height: 1.15;
                margin: 0.6rem 0 0.35rem 0;
                text-transform: uppercase;
            }

            a {
                color: var(--term-blue);
                cursor: pointer;
                text-underline-offset: 0.18rem;
            }

            a:hover {
                color: var(--term-text);
            }

            button,
            input,
            textarea,
            select,
            [role="button"],
            [data-baseweb="tab"],
            [data-baseweb="select"],
            [data-baseweb="checkbox"],
            [data-baseweb="radio"],
            [data-testid="stRadio"] label,
            [data-testid="stCheckbox"] label {
                cursor: pointer;
                touch-action: manipulation;
            }

            button,
            [data-baseweb="tab"],
            a,
            input,
            textarea,
            [data-baseweb="select"] > div,
            [data-baseweb="input"] > div,
            [data-baseweb="textarea"] textarea {
                transition: border-color 140ms ease, background-color 140ms ease, color 140ms ease, box-shadow 140ms ease, transform 120ms ease;
            }

            button:focus-visible,
            a:focus-visible,
            input:focus,
            textarea:focus,
            [data-baseweb="select"] > div:focus-within,
            [data-baseweb="input"] > div:focus-within,
            [data-baseweb="textarea"] textarea:focus,
            [data-baseweb="tab"]:focus-visible {
                outline: 2px solid rgba(94, 199, 232, 0.75) !important;
                outline-offset: 2px;
            }

            iframe {
                max-width: 100%;
            }

            hr {
                border-color: var(--term-line-soft);
                margin: 0.45rem 0;
            }

            [data-testid="stSidebar"] {
                background: #050505;
                border-right: 1px solid var(--term-line);
            }

            [data-testid="stSidebar"] section {
                background: #050505;
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {
                border: 0;
                color: var(--term-amber);
                font-size: 0.8rem;
                margin: 0.4rem 0 0.2rem 0;
                padding: 0;
            }

            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span {
                font-size: 0.74rem;
            }

            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
                color: var(--term-muted);
                line-height: 1.2;
            }

            [data-testid="stVerticalBlock"] {
                gap: 0.45rem;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.45rem;
            }

            div[data-testid="stMetric"] {
                background: linear-gradient(180deg, #0d1518 0%, #070b0d 100%);
                border: 1px solid var(--term-line);
                border-radius: 0;
                box-shadow: inset 0 1px 0 rgba(76, 201, 240, 0.14);
                min-height: 4.2rem;
                padding: 0.42rem 0.55rem;
            }

            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
                color: var(--term-muted);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.66rem;
                font-weight: 700;
                line-height: 1.1;
                text-transform: uppercase;
            }

            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: var(--term-text);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 1.12rem;
                line-height: 1.15;
            }

            div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
                color: var(--term-green);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.72rem;
            }

            .metric-strip {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                display: grid;
                grid-template-columns: repeat(var(--metric-cols), minmax(0, 1fr));
                margin: 0.25rem 0 0.5rem 0;
                width: 100%;
            }

            .metric-cell {
                border-right: 1px solid var(--term-line-soft);
                min-width: 0;
                padding: 0.34rem 0.48rem;
            }

            .metric-cell:last-child {
                border-right: 0;
            }

            .metric-label {
                color: var(--term-muted);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.62rem;
                font-weight: 700;
                line-height: 1;
                margin-bottom: 0.22rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .metric-value {
                color: var(--term-text);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.96rem;
                font-weight: 800;
                line-height: 1.08;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .metric-context {
                color: var(--term-muted);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.62rem;
                font-weight: 700;
                line-height: 1.15;
                margin-top: 0.18rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .metric-cell.good .metric-context,
            .metric-cell.good .metric-value {
                color: var(--term-green);
            }

            .metric-cell.bad .metric-context,
            .metric-cell.bad .metric-value {
                color: var(--term-red);
            }

            .metric-cell.warn .metric-context {
                color: #e6d36f;
            }

            .metric-cell.hot .metric-value {
                color: var(--term-amber);
            }

            .info-strip {
                background: #071014;
                border: 1px solid var(--term-line);
                display: grid;
                grid-template-columns: repeat(var(--info-cols), minmax(0, 1fr));
                margin: 0.25rem 0 0.45rem 0;
                width: 100%;
            }

            .info-cell {
                border-right: 1px solid var(--term-line-soft);
                min-width: 0;
                padding: 0.42rem 0.55rem;
            }

            .info-cell:last-child {
                border-right: 0;
            }

            .info-label {
                color: var(--term-muted);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.62rem;
                font-weight: 700;
                line-height: 1;
                margin-bottom: 0.22rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .info-value {
                color: var(--term-text);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.82rem;
                font-weight: 800;
                line-height: 1.12;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .equity-shell {
                background: linear-gradient(180deg, #0d1b20 0%, #0a1519 100%);
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
                margin: 0 0 0.65rem 0;
                padding: 0.85rem 0.95rem;
            }

            .equity-heading {
                align-items: flex-end;
                display: flex;
                gap: 1rem;
                justify-content: space-between;
                margin-bottom: 0.55rem;
            }

            .equity-kicker {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0.03em;
                text-transform: uppercase;
            }

            .company-title {
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 1.18rem;
                font-weight: 900;
                line-height: 1.15;
                margin: 0.14rem 0 0 0;
            }

            .company-subtitle {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.78rem;
                font-weight: 700;
                margin-top: 0.18rem;
            }

            .research-card {
                background: linear-gradient(180deg, var(--card-bg-soft) 0%, var(--card-bg) 100%);
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                box-shadow: inset 0 1px 0 rgba(154, 223, 255, 0.06), 0 8px 22px rgba(0, 0, 0, 0.14);
                height: 100%;
                padding: 0.78rem 0.82rem;
            }

            .quote-grid {
                display: grid;
                gap: 0.65rem;
                grid-template-columns: minmax(260px, 0.9fr) minmax(280px, 1.1fr);
                margin: 0 0 0.65rem 0;
            }

            .quote-top {
                align-items: center;
                display: flex;
                justify-content: space-between;
                gap: 0.7rem;
                margin-bottom: 0.55rem;
            }

            .quote-symbol {
                color: var(--term-amber);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.78rem;
                font-weight: 900;
                text-transform: uppercase;
            }

            .quote-label {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.64rem;
                font-weight: 800;
                text-transform: uppercase;
            }

            .quote-price {
                color: var(--term-text);
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 1.9rem;
                font-weight: 900;
                line-height: 1;
                margin-bottom: 0.34rem;
            }

            .quote-change {
                align-items: center;
                display: flex;
                gap: 0.35rem;
                margin-bottom: 0.55rem;
            }

            .badge {
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                color: var(--term-muted);
                display: inline-flex;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                font-weight: 900;
                line-height: 1;
                padding: 0.32rem 0.42rem;
                text-transform: uppercase;
            }

            .badge.good {
                background: rgba(54, 227, 155, 0.12);
                border-color: rgba(54, 227, 155, 0.45);
                color: var(--term-green);
            }

            .badge.bad {
                background: rgba(255, 97, 115, 0.12);
                border-color: rgba(255, 97, 115, 0.45);
                color: var(--term-red);
            }

            .badge.warn {
                background: rgba(213, 197, 111, 0.12);
                border-color: rgba(213, 197, 111, 0.42);
                color: #d5c56f;
            }

            .badge.neutral {
                background: rgba(76, 201, 240, 0.08);
                border-color: var(--term-line);
                color: var(--term-muted);
            }

            .quote-meta {
                color: var(--term-muted);
                display: grid;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                font-weight: 700;
                gap: 0.22rem;
                text-transform: uppercase;
            }

            .kpi-grid {
                display: grid;
                gap: 0.65rem;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                margin: 0 0 0.75rem 0;
            }

            .kpi-card {
                background: linear-gradient(180deg, var(--card-bg-soft) 0%, var(--card-bg) 100%);
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                box-shadow: inset 0 1px 0 rgba(154, 223, 255, 0.06);
                min-height: 6.1rem;
                min-width: 0;
                padding: 0.72rem 0.78rem;
            }

            .kpi-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.64rem;
                font-weight: 800;
                margin-bottom: 0.28rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .kpi-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 1.18rem;
                font-weight: 900;
                line-height: 1.08;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .kpi-helper {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.64rem;
                font-weight: 700;
                margin-top: 0.28rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .score-track {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                height: 0.42rem;
                margin-top: 0.5rem;
                overflow: hidden;
                width: 100%;
            }

            .score-fill {
                border-radius: 999px;
                background: linear-gradient(90deg, var(--term-green), var(--term-amber));
                height: 100%;
            }

            .driver-grid {
                display: grid;
                gap: 0.5rem;
                grid-template-columns: repeat(var(--driver-cols), minmax(0, 1fr));
                margin: 0.15rem 0 0.8rem 0;
            }

            .driver-card {
                background: var(--card-bg);
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-green);
                border-radius: 5px;
                min-width: 0;
                padding: 0.5rem 0.58rem;
            }

            .driver-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.62rem;
                font-weight: 800;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .driver-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 0.84rem;
                font-weight: 900;
                margin-top: 0.18rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .section-title {
                align-items: flex-start;
                display: flex;
                justify-content: space-between;
                gap: 0.75rem;
                margin: 0.05rem 0 0.5rem 0;
            }

            .section-title-main {
                color: var(--term-text);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.9rem;
                font-weight: 900;
                line-height: 1.15;
                text-transform: uppercase;
            }

            .section-title-sub {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.72rem;
                font-weight: 650;
                line-height: 1.25;
                margin-top: 0.18rem;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: linear-gradient(180deg, var(--card-bg-soft) 0%, var(--card-bg) 100%);
                border-color: var(--term-line-soft) !important;
                border-radius: 8px !important;
                box-shadow: inset 0 1px 0 rgba(154, 223, 255, 0.05);
            }

            .price-range {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                margin-top: 0.45rem;
                padding: 0.65rem 0.75rem;
            }

            .research-report-list {
                display: grid;
                gap: 0.48rem;
                margin-top: 0.2rem;
            }

            .research-report-card {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-amber);
                border-radius: 6px;
                padding: 0.58rem 0.68rem;
            }

            .research-report-title {
                color: var(--term-text);
                display: inline-block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.86rem;
                font-weight: 900;
                line-height: 1.2;
                margin-bottom: 0.24rem;
                text-decoration: none;
            }

            .research-report-title:hover {
                color: var(--term-amber);
                text-decoration: underline;
            }

            .research-report-meta {
                color: var(--term-muted);
                display: flex;
                flex-wrap: wrap;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.64rem;
                font-weight: 700;
                gap: 0.35rem;
                line-height: 1.25;
                margin-bottom: 0.22rem;
                text-transform: uppercase;
            }

            .research-report-summary {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.72rem;
                font-weight: 650;
                line-height: 1.3;
            }

            .home-header {
                align-items: end;
                display: grid;
                gap: 0.75rem;
                grid-template-columns: minmax(0, 1fr) minmax(220px, 0.28fr);
                margin-bottom: 0.45rem;
            }

            .home-subtitle {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.78rem;
                font-weight: 650;
                line-height: 1.25;
                margin-top: 0.2rem;
            }

            .home-market-grid,
            .home-mini-grid,
            .home-stock-grid {
                display: grid;
                gap: 0.52rem;
                margin: 0.12rem 0 0.35rem 0;
            }

            .home-market-grid {
                grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            }

            .home-mini-grid {
                grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
            }

            .home-stock-grid {
                grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
            }

            .home-card,
            .home-mini-card,
            .home-stock-card {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-radius: 7px;
                min-width: 0;
                padding: 0.55rem 0.62rem;
            }

            .home-card.good,
            .home-mini-card.good,
            .home-stock-card.good {
                border-left: 3px solid var(--term-green);
            }

            .home-card.bad,
            .home-mini-card.bad,
            .home-stock-card.bad {
                border-left: 3px solid var(--term-red);
            }

            .home-card.neutral,
            .home-mini-card.neutral,
            .home-stock-card.neutral {
                border-left: 3px solid var(--term-line);
            }

            .home-card-label,
            .home-mini-label,
            .home-stock-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.64rem;
                font-weight: 850;
                line-height: 1.15;
                margin-bottom: 0.24rem;
                text-transform: uppercase;
            }

            .home-card-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 1.14rem;
                font-weight: 900;
                line-height: 1.08;
            }

            .home-mini-value,
            .home-stock-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 1rem;
                font-weight: 900;
                line-height: 1.1;
            }

            .home-card-context,
            .home-mini-context,
            .home-stock-context {
                color: var(--term-muted);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.64rem;
                font-weight: 750;
                line-height: 1.2;
                margin-top: 0.24rem;
                text-transform: uppercase;
            }

            .home-card.good .home-card-context,
            .home-card.good .home-card-value,
            .home-mini-card.good .home-mini-context,
            .home-mini-card.good .home-mini-value,
            .home-stock-card.good .home-stock-context,
            .home-stock-card.good .home-stock-value {
                color: var(--term-green);
            }

            .home-card.bad .home-card-context,
            .home-card.bad .home-card-value,
            .home-mini-card.bad .home-mini-context,
            .home-mini-card.bad .home-mini-value,
            .home-stock-card.bad .home-stock-context,
            .home-stock-card.bad .home-stock-value {
                color: var(--term-red);
            }

            .home-group-title {
                color: var(--term-amber);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                font-weight: 900;
                margin: 0.42rem 0 0.25rem 0;
                text-transform: uppercase;
            }

            .sankey-page-subtitle {
                color: var(--term-muted);
                font-size: 0.8rem;
                font-weight: 650;
                line-height: 1.3;
                margin: -0.1rem 0 0.45rem 0;
            }

            .statement-page-subtitle {
                color: var(--term-muted);
                font-size: 0.8rem;
                font-weight: 650;
                line-height: 1.35;
                margin: -0.1rem 0 0.45rem 0;
            }

            .statement-section {
                animation: statementFadeIn 420ms ease both;
            }

            .statement-delay-1 {
                animation-delay: 40ms;
            }

            .statement-delay-2 {
                animation-delay: 150ms;
            }

            .statement-delay-3 {
                animation-delay: 260ms;
            }

            .statement-delay-4 {
                animation-delay: 370ms;
            }

            .insight-list {
                display: grid;
                gap: 0.42rem;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            }

            .insight-card {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-line);
                border-radius: 7px;
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.74rem;
                font-weight: 700;
                line-height: 1.35;
                padding: 0.52rem 0.62rem;
            }

            .insight-card.good {
                border-left-color: var(--term-green);
            }

            .insight-card.bad {
                border-left-color: var(--term-red);
            }

            .insight-card.warn {
                border-left-color: #e6d36f;
            }

            .statement-insight-grid {
                display: grid;
                gap: 0.55rem;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                margin: 0.35rem 0 0.7rem 0;
            }

            .statement-insight-tile {
                background: linear-gradient(180deg, rgba(13, 28, 34, 0.98), rgba(7, 16, 20, 0.98));
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-line);
                border-radius: 8px;
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                min-height: 218px;
                padding: 0.7rem 0.78rem;
            }

            .statement-insight-tile.good {
                border-left-color: var(--term-green);
            }

            .statement-insight-tile.bad {
                border-left-color: var(--term-red);
            }

            .statement-insight-tile.warn {
                border-left-color: #e6d36f;
            }

            .statement-insight-top {
                align-items: flex-start;
                display: flex;
                gap: 0.45rem;
                justify-content: space-between;
                margin-bottom: 0.5rem;
            }

            .statement-insight-label {
                color: var(--term-muted);
                display: block;
                font-size: 0.62rem;
                font-weight: 900;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }

            .statement-insight-headline {
                color: var(--term-text);
                display: block;
                font-size: 0.9rem;
                font-weight: 900;
                line-height: 1.16;
                margin-top: 0.12rem;
            }

            .statement-insight-status {
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                color: var(--term-muted);
                flex: 0 0 auto;
                font-size: 0.58rem;
                font-weight: 900;
                padding: 0.18rem 0.45rem;
                text-transform: uppercase;
            }

            .statement-insight-tile.good .statement-insight-status {
                background: rgba(112, 224, 163, 0.12);
                border-color: rgba(112, 224, 163, 0.45);
                color: var(--term-green);
            }

            .statement-insight-tile.bad .statement-insight-status {
                background: rgba(239, 132, 143, 0.12);
                border-color: rgba(239, 132, 143, 0.48);
                color: var(--term-red);
            }

            .statement-insight-tile.warn .statement-insight-status {
                background: rgba(230, 211, 111, 0.11);
                border-color: rgba(230, 211, 111, 0.44);
                color: #e6d36f;
            }

            .statement-insight-metrics {
                display: grid;
                gap: 0.34rem;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                margin-bottom: 0.6rem;
            }

            .statement-insight-metric {
                background: rgba(94, 199, 232, 0.045);
                border: 1px solid rgba(94, 199, 232, 0.14);
                border-radius: 6px;
                padding: 0.38rem 0.42rem;
            }

            .statement-insight-metric span {
                color: var(--term-muted);
                display: block;
                font-size: 0.55rem;
                font-weight: 900;
                text-transform: uppercase;
            }

            .statement-insight-metric strong {
                color: var(--term-text);
                display: block;
                font-size: 0.77rem;
                line-height: 1.18;
                margin-top: 0.08rem;
            }

            .statement-insight-copy {
                color: var(--term-muted);
                font-size: 0.72rem;
                font-weight: 700;
                line-height: 1.35;
                margin: 0.32rem 0 0 0;
            }

            .statement-insight-copy strong {
                color: var(--term-text);
                font-size: 0.62rem;
                text-transform: uppercase;
            }

            @keyframes statementFadeIn {
                from {
                    opacity: 0;
                    transform: translateY(8px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .sankey-tile-head {
                align-items: flex-start;
                border-bottom: 1px solid var(--term-line-soft);
                display: flex;
                gap: 0.55rem;
                justify-content: space-between;
                margin-bottom: 0.45rem;
                padding-bottom: 0.38rem;
            }

            .sankey-tile-title {
                color: var(--term-text);
                display: block;
                font-size: 0.92rem;
                font-weight: 900;
                line-height: 1.15;
                text-transform: uppercase;
            }

            .sankey-tile-meta {
                color: var(--term-muted);
                display: block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.66rem;
                font-weight: 700;
                line-height: 1.25;
                margin-top: 0.18rem;
            }

            .sankey-note,
            .sankey-empty {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                color: var(--term-muted);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.68rem;
                line-height: 1.3;
                margin: 0.35rem 0;
                padding: 0.48rem 0.58rem;
            }

            .sankey-empty {
                border-left: 3px solid var(--term-amber);
                color: var(--term-text);
            }

            .sankey-fallback {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-radius: 7px;
                display: grid;
                gap: 0.38rem;
                padding: 0.55rem;
            }

            .sankey-flow-row {
                background: #081419;
                border: 1px solid rgba(94, 199, 232, 0.14);
                border-radius: 6px;
                display: grid;
                gap: 0.35rem;
                grid-template-columns: minmax(0, 1.05fr) minmax(92px, 0.34fr) minmax(0, 1.05fr);
                min-width: 0;
                padding: 0.42rem 0.48rem;
            }

            .sankey-flow-node {
                color: var(--term-text);
                font-size: 0.72rem;
                font-weight: 850;
                line-height: 1.2;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sankey-flow-value {
                color: var(--term-muted);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.66rem;
                font-weight: 800;
                line-height: 1.2;
                text-align: center;
                white-space: nowrap;
            }

            .sankey-flow-track {
                background: #050b0d;
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                height: 0.42rem;
                margin-top: 0.2rem;
                overflow: hidden;
            }

            .sankey-flow-fill {
                background: var(--term-amber);
                border-radius: 999px;
                height: 100%;
            }

            .sankey-flow-fill.outflow {
                background: var(--term-red);
            }

            .sankey-flow-fill.inflow {
                background: var(--term-green);
            }

            .sankey-flow-fill.claim {
                background: var(--term-blue);
            }

            .sankey-svg-card {
                background: #071014;
                border: 1px solid var(--term-line-soft);
                border-radius: 8px;
                overflow: hidden;
                padding: 0.25rem;
            }

            .sankey-svg {
                display: block;
                height: auto;
                max-height: 430px;
                width: 100%;
            }

            .sankey-intro {
                animation: sankeyFadeIn 420ms ease both;
            }

            .sankey-delay-1 {
                animation-delay: 40ms;
            }

            .sankey-delay-2 {
                animation-delay: 150ms;
            }

            .sankey-delay-3 {
                animation-delay: 260ms;
            }

            @keyframes sankeyFadeIn {
                from {
                    opacity: 0;
                    transform: translateY(8px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .live-status-strip {
                display: grid;
                gap: 0.48rem;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                margin: 0.35rem 0 0.75rem 0;
            }

            .live-status-card {
                background: linear-gradient(180deg, rgba(16, 31, 37, 0.94), rgba(7, 16, 20, 0.96));
                border: 1px solid var(--term-line-soft);
                border-radius: 7px;
                min-width: 0;
                padding: 0.45rem 0.55rem;
            }

            .live-status-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.65rem;
                font-weight: 900;
                text-transform: uppercase;
            }

            .live-status-value {
                color: var(--term-text);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.92rem;
                font-weight: 900;
                line-height: 1.22;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .live-status-context {
                color: var(--term-faint);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                font-weight: 700;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .range-track {
                background: #091419;
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                height: 0.45rem;
                margin: 0.6rem 0 0.35rem 0;
                position: relative;
            }

            .range-fill {
                background: linear-gradient(90deg, var(--term-red), var(--term-amber), var(--term-green));
                border-radius: 999px;
                height: 100%;
                width: 100%;
            }

            .range-marker {
                background: var(--term-text);
                border: 2px solid #071014;
                border-radius: 999px;
                height: 0.86rem;
                position: absolute;
                top: 50%;
                transform: translate(-50%, -50%);
                width: 0.86rem;
            }

            .range-marker.target {
                background: var(--term-amber);
            }

            .range-label-row {
                color: var(--term-muted);
                display: flex;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.66rem;
                font-weight: 800;
                justify-content: space-between;
                text-transform: uppercase;
            }

            .terminal-strip {
                align-items: center;
                background: #081014;
                border: 1px solid var(--term-line);
                color: var(--term-muted);
                display: flex;
                flex-wrap: wrap;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                gap: 0;
                margin: 0.2rem 0 0.45rem 0;
                min-height: 1.85rem;
            }

            .terminal-strip span {
                border-right: 1px solid var(--term-line-soft);
                font-size: 0.72rem;
                font-weight: 700;
                line-height: 1;
                padding: 0.48rem 0.62rem;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .terminal-strip span:first-child {
                background: var(--term-amber);
                color: #050505;
            }

            .terminal-strip .hot {
                color: var(--term-green);
            }

            .dashboard-subtitle {
                color: var(--term-muted);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.78rem;
                line-height: 1.25;
                margin: -0.1rem 0 0.45rem 0;
            }

            .radar-header {
                align-items: flex-end;
                display: flex;
                gap: 1rem;
                justify-content: space-between;
                margin: 0 0 0.55rem 0;
            }

            .radar-title {
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 1.42rem;
                font-weight: 900;
                line-height: 1.08;
                margin: 0;
            }

            .radar-subtitle {
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.78rem;
                font-weight: 650;
                line-height: 1.25;
                margin-top: 0.2rem;
            }

            .scanner-toolbar {
                background: linear-gradient(180deg, var(--card-bg-soft) 0%, var(--card-bg) 100%);
                border: 1px solid var(--term-line-soft);
                border-radius: 8px;
                display: grid;
                gap: 0;
                grid-template-columns: repeat(var(--toolbar-cols), minmax(0, 1fr));
                margin: 0 0 0.5rem 0;
                overflow: hidden;
                width: 100%;
            }

            .toolbar-item {
                border-right: 1px solid var(--term-line-soft);
                min-width: 0;
                padding: 0.52rem 0.62rem;
            }

            .toolbar-item:last-child {
                border-right: 0;
            }

            .toolbar-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.62rem;
                font-weight: 800;
                line-height: 1;
                margin-bottom: 0.22rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .toolbar-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 0.82rem;
                font-weight: 850;
                line-height: 1.1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .radar-insight {
                align-items: center;
                background: rgba(94, 199, 232, 0.08);
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-amber);
                border-radius: 7px;
                color: var(--term-muted);
                display: flex;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.76rem;
                font-weight: 650;
                line-height: 1.35;
                margin: 0 0 0.65rem 0;
                padding: 0.58rem 0.68rem;
            }

            .vol-card-grid {
                display: grid;
                gap: 0.62rem;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                margin: 0 0 0.68rem 0;
            }

            .vol-card {
                background: linear-gradient(180deg, var(--card-bg-soft) 0%, var(--card-bg) 100%);
                border: 1px solid var(--term-line-soft);
                border-radius: 8px;
                box-shadow: inset 0 1px 0 rgba(154, 223, 255, 0.06);
                min-height: 6.05rem;
                min-width: 0;
                padding: 0.72rem 0.78rem;
            }

            .vol-card.hot {
                border-color: rgba(94, 199, 232, 0.48);
                box-shadow: inset 0 1px 0 rgba(94, 199, 232, 0.12), 0 10px 28px rgba(0, 0, 0, 0.16);
            }

            .vol-card.warn {
                border-color: rgba(213, 197, 111, 0.42);
            }

            .vol-label {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.64rem;
                font-weight: 850;
                line-height: 1;
                margin-bottom: 0.34rem;
                overflow: hidden;
                text-overflow: ellipsis;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .vol-value {
                color: var(--term-text);
                display: block;
                font-family: "Segoe UI", Inter, Arial, sans-serif;
                font-size: 1.22rem;
                font-weight: 950;
                line-height: 1.08;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .vol-card.hot .vol-value,
            .vol-card.hot .vol-accent {
                color: var(--term-amber);
            }

            .vol-helper {
                color: var(--term-muted);
                display: block;
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.66rem;
                font-weight: 650;
                line-height: 1.22;
                margin-top: 0.28rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .stress-chip-row {
                display: flex;
                gap: 0.42rem;
                margin: 0.05rem 0 0.72rem 0;
                overflow-x: auto;
                padding-bottom: 0.08rem;
                scrollbar-width: thin;
            }

            .stress-chip {
                background: #08151a;
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                display: inline-flex;
                flex: 0 0 auto;
                gap: 0.35rem;
                max-width: 22rem;
                padding: 0.38rem 0.55rem;
            }

            .stress-chip.high {
                background: rgba(239, 111, 123, 0.1);
                border-color: rgba(239, 111, 123, 0.38);
            }

            .stress-chip.medium {
                background: rgba(213, 197, 111, 0.1);
                border-color: rgba(213, 197, 111, 0.32);
            }

            .stress-label,
            .stress-value {
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.68rem;
                line-height: 1;
                white-space: nowrap;
            }

            .stress-label {
                color: var(--term-muted);
                font-weight: 800;
                text-transform: uppercase;
            }

            .stress-value {
                color: var(--term-text);
                font-weight: 900;
            }

            .stress-chip.high .stress-value {
                color: var(--term-red);
            }

            .stress-chip.medium .stress-value {
                color: #d5c56f;
            }

            .forecast-table {
                border: 1px solid var(--term-line-soft);
                border-radius: 8px;
                margin-top: 0.15rem;
                max-height: 33rem;
                overflow: auto;
            }

            .forecast-table table {
                border-collapse: collapse;
                min-width: 720px;
                width: 100%;
            }

            .forecast-table th {
                background: #10212a;
                border-bottom: 1px solid var(--term-line-soft);
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.66rem;
                font-weight: 900;
                padding: 0.48rem 0.55rem;
                position: sticky;
                text-align: left;
                text-transform: uppercase;
                top: 0;
                z-index: 1;
            }

            .forecast-table td {
                background: #0b171c;
                border-bottom: 1px solid rgba(25, 49, 58, 0.72);
                color: var(--term-text);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.73rem;
                font-weight: 650;
                padding: 0.46rem 0.55rem;
                vertical-align: middle;
                white-space: nowrap;
            }

            .forecast-table tr.top-row td {
                background: #0f242c;
            }

            .forecast-table tr:hover td {
                background: #10252d;
            }

            .ticker-cell {
                color: var(--term-amber);
                font-weight: 950;
            }

            .rank-cell {
                color: var(--term-muted);
                font-variant-numeric: tabular-nums;
                width: 3.2rem;
            }

            .number-cell {
                font-variant-numeric: tabular-nums;
                text-align: right;
            }

            .bias-badge {
                background: rgba(94, 199, 232, 0.08);
                border: 1px solid var(--term-line);
                border-radius: 999px;
                color: var(--term-blue);
                display: inline-flex;
                font-size: 0.64rem;
                font-weight: 900;
                line-height: 1;
                padding: 0.27rem 0.4rem;
                text-transform: uppercase;
            }

            .bias-badge.bad {
                background: rgba(239, 111, 123, 0.1);
                border-color: rgba(239, 111, 123, 0.38);
                color: var(--term-red);
            }

            .bias-badge.good {
                background: rgba(73, 214, 155, 0.1);
                border-color: rgba(73, 214, 155, 0.38);
                color: var(--term-green);
            }

            .risk-band {
                align-items: center;
                background: #070c0f;
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-amber);
                border-radius: 0;
                display: flex;
                flex-wrap: wrap;
                gap: 0.28rem;
                margin: 0.35rem 0 0.55rem 0;
                padding: 0.38rem 0.42rem;
            }

            .risk-pill,
            .sentiment-pill,
            .ticker-chip,
            .factor-chip {
                border-radius: 0;
                display: inline-flex;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.68rem;
                font-weight: 700;
                line-height: 1;
                padding: 0.28rem 0.38rem;
                text-transform: uppercase;
            }

            .risk-pill {
                background: #081820;
                border: 1px solid var(--term-line);
                color: var(--term-amber);
            }

            .news-card {
                background: #070c0f;
                border: 1px solid var(--term-line-soft);
                border-left: 3px solid var(--term-muted);
                border-radius: 6px;
                box-shadow: none;
                margin: 0 0 0.28rem 0;
                padding: 0.44rem 0.56rem;
                scroll-margin-top: 0.9rem;
            }

            .news-card.bullish {
                border-left-color: var(--term-green);
            }

            .news-card.bearish {
                border-left-color: var(--term-red);
            }

            .card-topline {
                align-items: center;
                color: var(--term-muted);
                display: flex;
                flex-wrap: wrap;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.64rem;
                font-weight: 700;
                gap: 0.28rem;
                margin-bottom: 0.18rem;
                text-transform: uppercase;
            }

            .headline {
                color: var(--term-text);
                display: inline-block;
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.8rem;
                font-weight: 700;
                line-height: 1.25;
                margin-bottom: 0.12rem;
                min-height: 1.4rem;
                text-decoration: none;
            }

            .headline:hover {
                color: var(--term-amber);
                text-decoration: underline;
            }

            .summary {
                color: var(--term-muted);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.68rem;
                line-height: 1.25;
                margin: 0.02rem 0 0.24rem 0;
            }

            .sentiment-pill.bullish {
                background: rgba(0, 208, 132, 0.12);
                border: 1px solid rgba(0, 208, 132, 0.45);
                color: var(--term-green);
            }

            .sentiment-pill.neutral {
                background: #121212;
                border: 1px solid var(--term-line-soft);
                color: var(--term-muted);
            }

            .sentiment-pill.bearish {
                background: rgba(255, 77, 77, 0.12);
                border: 1px solid rgba(255, 77, 77, 0.45);
                color: var(--term-red);
            }

            .ticker-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.2rem;
                min-height: 0.2rem;
            }

            .ticker-chip {
                background: rgba(111, 183, 255, 0.1);
                border: 1px solid rgba(111, 183, 255, 0.5);
                color: var(--term-blue);
            }

            .factor-chip {
                background: rgba(76, 201, 240, 0.1);
                border: 1px solid rgba(76, 201, 240, 0.55);
                color: var(--term-amber);
            }

            [data-testid="stSidebar"] [role="radiogroup"] {
                background: #0b171c;
                border: 1px solid var(--term-line-soft);
                border-radius: 12px;
                padding: 0.35rem;
            }

            [data-testid="stSidebar"] label[data-baseweb="radio"] {
                align-items: center;
                border: 1px solid transparent;
                border-radius: 999px;
                margin: 0.12rem 0;
                padding: 0.32rem 0.42rem;
                transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
                width: 100%;
            }

            [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
                background: rgba(94, 199, 232, 0.08);
                border-color: var(--term-line-soft);
            }

            [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
                background: rgba(94, 199, 232, 0.16);
                border-color: rgba(94, 199, 232, 0.45);
                color: var(--term-text);
            }

            .stTabs [data-baseweb="tab-list"] {
                background: #091419;
                border: 1px solid var(--term-line-soft);
                border-radius: 999px;
                gap: 0.18rem;
                margin-top: 0.45rem;
                overflow-x: auto;
                padding: 0.2rem;
                scrollbar-width: none;
            }

            .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
                display: none;
            }

            .stTabs [data-baseweb="tab"] {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 999px;
                color: var(--term-muted);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.72rem;
                font-weight: 800;
                min-height: 2.18rem;
                padding: 0.28rem 0.72rem;
                text-transform: uppercase;
                transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
                user-select: none;
                white-space: nowrap;
            }

            .stTabs [data-baseweb="tab"]:hover {
                background: rgba(94, 199, 232, 0.08);
                color: var(--term-text);
            }

            .stTabs [aria-selected="true"] {
                background: rgba(94, 199, 232, 0.18);
                border-color: rgba(94, 199, 232, 0.5);
                color: var(--term-text);
            }

            [data-testid="stDataFrame"] {
                background: var(--card-bg);
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                overflow: hidden;
            }

            [data-testid="stDataFrame"] div[role="grid"],
            [data-testid="stDataFrame"] div[role="gridcell"],
            [data-testid="stDataFrame"] div[role="columnheader"] {
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.72rem;
            }

            [data-testid="stDataFrame"] div[role="grid"] {
                background: var(--card-bg) !important;
                color: var(--term-text) !important;
            }

            [data-testid="stDataFrame"] div[role="columnheader"] {
                background: #10212a !important;
                color: #d7e7e9 !important;
                font-weight: 800 !important;
            }

            [data-testid="stDataFrame"] div[role="gridcell"] {
                background: #0b171c !important;
                color: #d7e7e9 !important;
            }

            [data-testid="stVegaLiteChart"],
            [data-testid="stArrowVegaLiteChart"],
            [data-testid="stLineChart"],
            [data-testid="stBarChart"] {
                background: var(--card-bg);
                border: 1px solid var(--term-line-soft);
                border-radius: 6px;
                padding: 0.3rem;
            }

            .stButton button,
            .stDownloadButton button {
                background: #071820;
                border: 1px solid var(--term-amber-soft);
                border-radius: 7px;
                color: var(--term-amber);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                font-size: 0.72rem;
                font-weight: 700;
                min-height: 2.25rem;
                padding: 0.36rem 0.64rem;
                text-transform: uppercase;
            }

            .stButton button[kind="primary"] {
                background: #11313b;
                border-color: var(--term-amber);
                color: var(--term-text);
            }

            .stButton button:hover,
            .stDownloadButton button:hover {
                background: #123540;
                border-color: var(--term-amber);
                box-shadow: 0 0 0 2px rgba(94, 199, 232, 0.09);
                color: var(--term-text);
                transform: translateY(-1px);
            }

            .stButton button:active,
            .stDownloadButton button:active {
                transform: translateY(0);
            }

            input,
            textarea,
            [data-baseweb="select"] > div,
            [data-baseweb="input"] > div,
            [data-baseweb="textarea"] textarea {
                background-color: #050505 !important;
                border-color: var(--term-line-soft) !important;
                border-radius: 0 !important;
                color: var(--term-text) !important;
                font-family: Consolas, "Lucida Console", "Courier New", monospace !important;
                font-size: 0.74rem !important;
                min-height: 2.35rem;
            }

            input:hover,
            textarea:hover,
            [data-baseweb="select"] > div:hover,
            [data-baseweb="input"] > div:hover,
            [data-baseweb="textarea"] textarea:hover {
                border-color: rgba(94, 199, 232, 0.48) !important;
            }

            [data-baseweb="tag"] {
                background: #081820 !important;
                border-radius: 0 !important;
                color: var(--term-amber) !important;
            }

            [data-baseweb="slider"] [role="slider"] {
                background: var(--term-amber);
                border-color: var(--term-amber);
            }

            .stAlert {
                background: #081014;
                border: 1px solid var(--term-line);
                border-radius: 0;
                color: var(--term-text);
                font-family: Consolas, "Lucida Console", "Courier New", monospace;
                font-size: 0.76rem;
                padding: 0.45rem 0.6rem;
            }

            @media (max-width: 640px) {
                .block-container {
                    padding-left: 0.45rem;
                    padding-right: 0.45rem;
                }

                .headline-scroll {
                    max-height: none;
                    overflow-y: visible;
                    padding-right: 0;
                }

                .home-aligned-card {
                    min-height: 0;
                }

                .headline {
                    font-size: 0.78rem;
                }

                .news-card {
                    padding: 0.45rem;
                }

                .sankey-tile-head {
                    flex-direction: column;
                }

                .terminal-strip span {
                    font-size: 0.66rem;
                    padding: 0.42rem 0.46rem;
                }

                .metric-strip {
                    grid-template-columns: 1fr;
                }

                .info-strip {
                    grid-template-columns: 1fr;
                }

                .equity-heading {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .quote-grid,
                .kpi-grid,
                .driver-grid,
                .vol-card-grid {
                    grid-template-columns: 1fr;
                }

                .radar-header {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .scanner-toolbar {
                    grid-template-columns: 1fr;
                }

                .toolbar-item {
                    border-bottom: 1px solid var(--term-line-soft);
                    border-right: 0;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                html,
                .stApp,
                .headline-scroll {
                    scroll-behavior: auto !important;
                }

                *,
                *::before,
                *::after {
                    transition-duration: 0.01ms !important;
                    transition-delay: 0ms !important;
                }
            }

            @media (min-width: 641px) and (max-width: 980px) {
                .metric-strip {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .info-strip {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .quote-grid {
                    grid-template-columns: 1fr;
                }

                .kpi-grid,
                .driver-grid,
                .vol-card-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .scanner-toolbar {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_risk_band(context: MacroContext, forecast_df: pd.DataFrame) -> None:
    factor_labels = [
        f"{factor}: {score:.0f}"
        for factor, score in context.factor_scores[:4]
    ]
    top_symbols = []
    if not forecast_df.empty:
        top_symbols = [
            f"{row['Ticker']} {format_move(row['Projected Move %'], 1)}"
            for _, row in forecast_df.head(4).iterrows()
        ]
    labels = [f"Macro stress {context.stress_score:.0f}/100"] + factor_labels + top_symbols
    st.markdown(
        "<div class='risk-band'>"
        + "".join(f"<span class='risk-pill'>{html.escape(label)}</span>" for label in labels)
        + "</div>",
        unsafe_allow_html=True,
    )


def metric_tone(context: object | None) -> str:
    if context is None:
        return "neutral"
    text = str(context).strip().lower()
    if not text:
        return "neutral"
    if text.startswith("-") or "miss" in text or "decline" in text or "weak" in text:
        return "bad"
    if text.startswith("+") or "beat" in text or "growth" in text or "strong" in text:
        return "good"
    return "neutral"


def render_metric_strip(items: list[dict[str, object]], columns: int) -> None:
    safe_columns = max(1, min(columns, 8))
    cells = []
    for item in items:
        label = html.escape(str(item.get("label", "")))
        value = html.escape(str(item.get("value", "N/A")))
        context = item.get("context")
        tone = html.escape(str(item.get("tone") or metric_tone(context)))
        context_html = ""
        if context not in (None, ""):
            context_html = f"<span class='metric-context'>{html.escape(str(context))}</span>"
        cells.append(
            f"<div class='metric-cell {tone}'>"
            f"<span class='metric-label'>{label}</span>"
            f"<span class='metric-value'>{value}</span>"
            f"{context_html}"
            "</div>"
        )
    st.markdown(
        f"<div class='metric-strip' style='--metric-cols: {safe_columns};'>"
        + "".join(cells)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_info_strip(items: list[dict[str, object]], columns: int) -> None:
    if not items:
        return
    safe_columns = max(1, min(columns, 8))
    cells = []
    for item in items:
        label = html.escape(str(item.get("label", "")))
        value = html.escape(str(item.get("value", "N/A")))
        cells.append(
            f"<div class='info-cell'>"
            f"<span class='info-label'>{label}</span>"
            f"<span class='info-value'>{value}</span>"
            "</div>"
        )
    st.markdown(
        f"<div class='info-strip' style='--info-cols: {safe_columns};'>"
        + "".join(cells)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_home_cards(items: list[dict[str, object]], grid_class: str = "home-mini-grid") -> None:
    if not items:
        return
    card_class = {
        "home-market-grid": "home-card",
        "home-stock-grid": "home-stock-card",
    }.get(grid_class, "home-mini-card")
    label_class = {
        "home-market-grid": "home-card-label",
        "home-stock-grid": "home-stock-label",
    }.get(grid_class, "home-mini-label")
    value_class = {
        "home-market-grid": "home-card-value",
        "home-stock-grid": "home-stock-value",
    }.get(grid_class, "home-mini-value")
    context_class = {
        "home-market-grid": "home-card-context",
        "home-stock-grid": "home-stock-context",
    }.get(grid_class, "home-mini-context")
    cells = []
    for item in items:
        label = html.escape(str(item.get("label", "")))
        value = html.escape(str(item.get("value", "N/A")))
        context = html.escape(str(item.get("context", "")))
        tone = html.escape(str(item.get("tone", "neutral") or "neutral"))
        context_html = f"<span class='{context_class}'>{context}</span>" if context else ""
        cells.append(
            f"<div class='{card_class} {tone}'>"
            f"<span class='{label_class}'>{label}</span>"
            f"<span class='{value_class}'>{value}</span>"
            f"{context_html}"
            "</div>"
        )
    st.markdown(f"<div class='{grid_class}'>" + "".join(cells) + "</div>", unsafe_allow_html=True)


def render_home_stock_group(title: str, items: list[dict[str, object]]) -> None:
    visible = [
        item
        for item in items
        if str(item.get("value", "N/A")) not in {"", "N/A", "None", "nan"}
    ]
    if not visible:
        return
    st.markdown(f"<span class='home-group-title'>{html.escape(title)}</span>", unsafe_allow_html=True)
    render_home_cards(visible, "home-stock-grid")


def age_label(timestamp: datetime | None) -> str:
    if not timestamp:
        return "unknown"
    now = eastern_now()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=now.tzinfo)
    seconds = max(0, int((now - timestamp).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return timestamp.strftime("%Y-%m-%d %I:%M %p ET").lstrip("0")


def render_global_refresh_controls() -> dict[str, object]:
    st.sidebar.header("Live Refresh")
    enabled = st.sidebar.toggle(
        "Auto-refresh",
        value=st.session_state.get("global_auto_refresh_enabled", False),
        key="global_auto_refresh_enabled",
        help="Reruns the app on a timer. Provider-specific cache TTLs prevent slow data from being refetched too often.",
    )
    interval_label = st.sidebar.selectbox(
        "Refresh interval",
        list(GLOBAL_REFRESH_INTERVALS),
        index=1,
        key="global_refresh_interval",
    )
    interval_seconds = int(GLOBAL_REFRESH_INTERVALS[interval_label])
    manual_refresh = st.sidebar.button("Refresh Now", use_container_width=True, key="global_refresh_now")
    show_provider_debug = st.sidebar.checkbox("Show provider strategy", value=False, key="global_provider_debug")
    if manual_refresh:
        clear_live_data_caches(include_slow=True)
        st.session_state["last_manual_refresh_at"] = eastern_now()
        st.session_state["last_successful_refresh_global"] = eastern_now()
        st.sidebar.success("Caches cleared. Refreshing data now.")

    if enabled:
        st.sidebar.caption("Auto-refresh keeps filters/tickers, but turn it off while making several changes.")
        if st_autorefresh is not None:
            st_autorefresh(interval=interval_seconds * 1000, key="global_live_autorefresh")
        else:
            st.sidebar.caption("Auto-refresh package unavailable; manual refresh remains available.")

    st.session_state["last_app_refresh_at"] = eastern_now()
    last_manual = st.session_state.get("last_manual_refresh_at")
    st.sidebar.caption(
        f"Last app refresh: {st.session_state['last_app_refresh_at'].strftime('%I:%M:%S %p ET').lstrip('0')}"
        + (f" | Manual: {age_label(last_manual)}" if last_manual else "")
    )
    return {
        "enabled": enabled,
        "interval_label": interval_label,
        "interval_seconds": interval_seconds,
        "manual_refresh": manual_refresh,
        "show_provider_debug": show_provider_debug,
    }


def render_global_live_status_strip(page: str, refresh_config: dict[str, object]) -> None:
    now = eastern_now()
    quote_provider = active_quote_provider_label()
    quote_status = "Delayed / near real-time"
    ticker = (
        st.session_state.get("home_quick_ticker")
        or st.session_state.get("stock_due_diligence_ticker")
        or "SPY"
    )
    items = [
        {"label": "Market Data", "value": quote_status, "context": quote_provider},
        {"label": "Headlines", "value": "Cached 10m", "context": "shared RSS/API module"},
        {"label": "Economic Calendar", "value": "Cached 6h", "context": "official sources"},
        {"label": "Selected Ticker", "value": normalize_symbol(str(ticker)) or "SPY", "context": "state preserved"},
        {"label": "Auto Refresh", "value": "On" if refresh_config.get("enabled") else "Off", "context": str(refresh_config.get("interval_label"))},
        {"label": "Last App Refresh", "value": now.strftime("%I:%M:%S %p ET").lstrip("0"), "context": "former yfinance data model"},
    ]
    cells = []
    for item in items:
        cells.append(
            "<div class='live-status-card'>"
            f"<span class='live-status-label'>{html.escape(str(item['label']))}</span>"
            f"<span class='live-status-value'>{html.escape(str(item['value']))}</span>"
            f"<span class='live-status-context'>{html.escape(str(item['context']))}</span>"
            "</div>"
        )
    st.markdown(
        f"<div class='live-status-strip' aria-label='Live data status'>{''.join(cells)}</div>",
        unsafe_allow_html=True,
    )


def render_provider_strategy_debug() -> None:
    provider_rows = []
    for data_type, hierarchy in PROVIDER_HIERARCHY.items():
        provider_rows.append(
            {
                "Data Type": data_type,
                "Primary / Fallback Order": " > ".join(hierarchy),
            }
        )
    ttl_rows = [{"Data Type": key, "Cache TTL / Cadence": value} for key, value in DATA_REFRESH_TTLS.items()]
    with st.expander("Provider and refresh strategy", expanded=False):
        render_dashboard_table(pd.DataFrame(provider_rows), height=300)
        render_dashboard_table(pd.DataFrame(ttl_rows), height=300)


def render_scanner_toolbar(items: list[dict[str, object]]) -> None:
    if not items:
        return
    columns = max(1, min(len(items), 6))
    cells = []
    for item in items:
        cells.append(
            "<div class='toolbar-item'>"
            f"<span class='toolbar-label'>{html.escape(str(item.get('label', '')))}</span>"
            f"<span class='toolbar-value'>{html.escape(str(item.get('value', 'N/A')))}</span>"
            "</div>"
        )
    st.markdown(
        f"<div class='scanner-toolbar' style='--toolbar-cols: {columns};'>"
        + "".join(cells)
        + "</div>",
        unsafe_allow_html=True,
    )


def severity_level(value: float | int | None, high: float, medium: float) -> str:
    if value is None or pd.isna(value):
        return "neutral"
    number = float(value)
    if number >= high:
        return "high"
    if number >= medium:
        return "medium"
    return "neutral"


def badge_tone_from_severity(severity: str) -> str:
    return {"high": "bad", "medium": "warn"}.get(severity, "neutral")


def render_volatility_summary_cards(
    top_row: pd.Series | None,
    macro_context: MacroContext,
    earnings_catalysts: int,
    social_mentions_total: int,
    social_lookback_days: int,
    avg_projected: float,
    ranked_count: int,
) -> None:
    if top_row is None:
        top_ticker = "N/A"
        top_company = "No matching forecast rows"
        top_move = "N/A"
        top_move_value = 0.0
    else:
        top_ticker = str(top_row.get("Ticker", "N/A"))
        top_company = str(top_row.get("Company") or "Company unavailable")
        top_move_value = float(top_row.get("Projected Move %", 0.0) or 0.0)
        top_move = format_move(top_move_value, 1)

    macro_severity = severity_level(macro_context.stress_score, high=70, medium=40)
    top_move_severity = severity_level(top_move_value, high=12, medium=6)
    avg_move_severity = severity_level(avg_projected, high=10, medium=5)
    macro_progress = max(0, min(float(macro_context.stress_score), 100))
    cards = [
        {
            "label": "Top Volatility Ticker",
            "value": top_ticker,
            "helper": f"{top_company} | {top_move} projected",
            "class": "hot" if top_move_severity in {"high", "medium"} else "neutral",
        },
        {
            "label": "Macro Stress Score",
            "value": f"{macro_context.stress_score:.0f}/100",
            "helper": "Headline and event pressure",
            "class": "warn" if macro_severity != "neutral" else "neutral",
            "progress": macro_progress,
        },
        {
            "label": "Earnings Catalyst Window",
            "value": f"{earnings_catalysts:,}",
            "helper": "Within selected horizon",
            "class": "neutral",
        },
        {
            "label": "Social Mentions",
            "value": f"{social_mentions_total:,}",
            "helper": f"Last {social_lookback_days} day{'s' if social_lookback_days != 1 else ''}",
            "class": "neutral",
        },
        {
            "label": "Average Move",
            "value": format_move(avg_projected, 1),
            "helper": f"Top {ranked_count:,} ranked names",
            "class": "hot" if avg_move_severity in {"high", "medium"} else "neutral",
        },
    ]

    card_html = []
    for card in cards:
        progress = card.get("progress")
        progress_html = ""
        if progress is not None:
            progress_html = (
                f"<div class='score-track'><div class='score-fill' "
                f"style='width:{float(progress):.0f}%;'></div></div>"
            )
        card_html.append(
            f"<div class='vol-card {html.escape(str(card.get('class', 'neutral')))}'>"
            f"<span class='vol-label'>{html.escape(str(card['label']))}</span>"
            f"<span class='vol-value'>{html.escape(str(card['value']))}</span>"
            f"<span class='vol-helper'>{html.escape(str(card['helper']))}</span>"
            f"{progress_html}"
            "</div>"
        )
    st.markdown("<div class='vol-card-grid'>" + "".join(card_html) + "</div>", unsafe_allow_html=True)


def render_stress_chip_row(context: MacroContext, forecast_df: pd.DataFrame) -> None:
    chips: list[tuple[str, str, str]] = [
        (
            "Macro Stress",
            f"{context.stress_score:.0f}/100",
            severity_level(context.stress_score, high=70, medium=40),
        )
    ]
    for factor, score in context.factor_scores[:4]:
        chips.append((factor, f"{score:.0f}", severity_level(score, high=35, medium=15)))
    if not forecast_df.empty:
        top = forecast_df.iloc[0]
        projected = float(top.get("Projected Move %", 0.0) or 0.0)
        chips.append(
            (
                str(top.get("Ticker", "Top ticker")),
                format_move(projected, 1),
                severity_level(projected, high=12, medium=6),
            )
        )
    st.markdown(
        "<div class='stress-chip-row'>"
        + "".join(
            "<div class='stress-chip {severity}'>"
            "<span class='stress-label'>{label}</span>"
            "<span class='stress-value'>{value}</span>"
            "</div>".format(
                severity=html.escape(severity),
                label=html.escape(label),
                value=html.escape(value),
            )
            for label, value, severity in chips
        )
        + "</div>",
        unsafe_allow_html=True,
    )


FORECAST_CURRENCY_COLUMNS = {"Last Price", "Market Cap", "Avg Dollar Volume"}
FORECAST_MOVE_COLUMNS = {
    "Projected Move %",
    "Options Move %",
    "30D Options Move %",
    "20D Hist Move %",
    "60D Hist Move %",
    "90D Hist Move %",
    "252D Hist Move %",
    "Backtest Move %",
}
FORECAST_PERCENT_COLUMNS = {
    "Options IV %",
    "30D Options IV %",
    "Ann. Realized Vol %",
    "Momentum %",
    "Gap Risk %",
    "Backtest Error %",
}
FORECAST_NUMBER_COLUMNS = {
    "Earnings Risk",
    "Macro Risk",
    "News Risk",
    "Social Risk",
    "Social Engagement",
    "Social Mentions",
    "Social Sentiment",
    "Volume Risk",
    "Analyst Dispersion",
    "Beta",
    "Volatility Score",
    "Confidence",
}


def direction_bias_tone(value: object) -> str:
    text = str(value).lower()
    if "upside" in text or "bull" in text or "positive" in text:
        return "good"
    if "downside" in text or "bear" in text or "negative" in text:
        return "bad"
    return "neutral"


def format_forecast_value(column: str, value: object) -> str:
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except TypeError:
        pass
    if column == "Rank":
        return f"{int(float(value))}"
    if column == "Last Price":
        return format_currency(coerce_float(value), 2)
    if column in {"Market Cap", "Avg Dollar Volume"}:
        return format_compact_currency(coerce_float(value), 2)
    if column in FORECAST_MOVE_COLUMNS:
        return format_move(coerce_float(value), 2)
    if column in FORECAST_PERCENT_COLUMNS:
        return format_percent(coerce_float(value), 2, signed=column == "Backtest Error %")
    if column == "Volume Shock":
        number = coerce_float(value)
        return "N/A" if number is None else f"{number:.2f}x"
    if column in FORECAST_NUMBER_COLUMNS:
        number = coerce_float(value)
        return "N/A" if number is None else f"{number:,.2f}"
    return str(value)


def forecast_display_label(column: str) -> str:
    return {
        "Options Move %": "Option Move %",
        "Options IV %": "IV Rank / IV %",
        "ATR Move %": "ATR %",
        "Volume Shock": "Relative Volume",
        "Social Engagement": "Social Engagement",
    }.get(column, column)


def render_forecast_table(frame: pd.DataFrame, columns: list[str]) -> None:
    if frame.empty or not columns:
        st.info("No forecast rows match the current filters.")
        return
    display = frame[columns].copy()
    headers = "".join(f"<th>{html.escape(forecast_display_label(column))}</th>" for column in columns)
    rows = []
    for row_number, (_, row) in enumerate(display.iterrows()):
        row_class = "top-row" if row_number == 0 else ""
        cells = []
        for column in columns:
            raw_value = row.get(column)
            value = html.escape(format_forecast_value(column, raw_value))
            cell_class = ""
            if column == "Rank":
                cell_class = "rank-cell"
            elif column == "Ticker":
                cell_class = "ticker-cell"
            elif column in FORECAST_CURRENCY_COLUMNS | FORECAST_MOVE_COLUMNS | FORECAST_PERCENT_COLUMNS | FORECAST_NUMBER_COLUMNS:
                cell_class = "number-cell"
            if column == "Direction Bias":
                tone = direction_bias_tone(raw_value)
                value = f"<span class='bias-badge {tone}'>{value}</span>"
                cells.append(f"<td>{value}</td>")
            else:
                cells.append(f"<td class='{cell_class}'>{value}</td>")
        rows.append(f"<tr class='{row_class}'>" + "".join(cells) + "</tr>")
    st.markdown(
        "<div class='forecast-table'><table>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )


def render_research_kpi_grid(items: list[dict[str, object]]) -> None:
    cells = []
    for item in items:
        label = html.escape(str(item.get("label", "")))
        value = html.escape(str(item.get("value", "N/A")))
        helper = html.escape(str(item.get("helper", "")))
        badge = item.get("badge")
        tone = html.escape(str(item.get("tone", "neutral")))
        progress = item.get("progress")
        badge_html = ""
        if badge not in (None, ""):
            badge_html = f"<span class='badge {tone}'>{html.escape(str(badge))}</span>"
        progress_html = ""
        if progress is not None and not pd.isna(progress):
            progress_value = max(0.0, min(float(progress), 100.0))
            progress_html = (
                f"<div class='score-track'><div class='score-fill' "
                f"style='width:{progress_value:.0f}%;'></div></div>"
            )
        cells.append(
            f"<div class='kpi-card'>"
            f"<span class='kpi-label'>{label}</span>"
            f"<span class='kpi-value'>{value}</span>"
            f"{badge_html}"
            f"<span class='kpi-helper'>{helper}</span>"
            f"{progress_html}"
            "</div>"
        )
    st.markdown("<div class='kpi-grid'>" + "".join(cells) + "</div>", unsafe_allow_html=True)


def render_driver_grid(items: list[dict[str, str]]) -> None:
    if not items:
        return
    cells = []
    for item in items:
        cells.append(
            f"<div class='driver-card'>"
            f"<span class='driver-label'>{html.escape(str(item.get('label', '')))}</span>"
            f"<span class='driver-value'>{html.escape(str(item.get('value', 'N/A')))}</span>"
            "</div>"
        )
    columns = max(1, min(len(items), 6))
    st.markdown(
        f"<div class='driver-grid' style='--driver-cols: {columns};'>"
        + "".join(cells)
        + "</div>",
        unsafe_allow_html=True,
    )


def quote_tone(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "neutral"
    return "good" if float(value) >= 0 else "bad"


@st.fragment(run_every="45s")
def render_quote_module(ticker: str, company_name: str) -> dict:
    with st.spinner("Updating quote..."):
        quote = fetch_quote_snapshot(ticker)
    price = quote.get("price")
    change = quote.get("change")
    change_pct = quote.get("change_pct")
    tone = quote_tone(change)
    change_text = "N/A"
    if change is not None and change_pct is not None:
        change_text = f"{format_currency(change, 2)} / {format_percent(change_pct, 2, signed=True)}"
    updated_at = quote.get("updated_at")
    if isinstance(updated_at, datetime):
        updated_text = updated_at.strftime("%I:%M:%S %p ET")
    else:
        updated_text = eastern_now().strftime("%I:%M:%S %p ET")
    quote_meta = quote.get("provider") or metadata_to_dict(default_yahoo_metadata("Quote", last_updated=updated_at if isinstance(updated_at, datetime) else eastern_now()))
    provider_label = quote_meta.get("source_label", "Yahoo Finance/yfinance") if isinstance(quote_meta, dict) else "Yahoo Finance/yfinance"
    refresh_label = st.session_state.get("global_refresh_interval", "1 minute")

    intraday = quote.get("intraday", pd.DataFrame())
    quote_cols = st.columns([0.9, 1.1], gap="small")
    with quote_cols[0]:
        st.markdown(
            "<div class='research-card'>"
            f"<div class='quote-top'><div><div class='quote-symbol'>{html.escape(ticker)}</div>"
            f"<div class='quote-label'>{html.escape(company_name)}</div></div>"
            f"<span class='badge neutral'>{html.escape(str(quote.get('quote_label', 'Delayed quote')))}</span></div>"
            f"<div class='quote-price'>{html.escape(format_currency(price, 2))}</div>"
            f"<div class='quote-change'><span class='badge {tone}'>{html.escape(change_text)}</span>"
            f"<span class='badge neutral'>{html.escape(str(quote.get('market_status', 'Unavailable')))}</span></div>"
            f"<div class='quote-meta'><span>Previous close: {html.escape(format_currency(quote.get('previous_close'), 2))}</span>"
            f"<span>Last updated: {html.escape(updated_text)}</span>"
            f"<span>Provider: {html.escape(str(provider_label))}</span>"
            f"<span>Auto-refresh: {html.escape(str(refresh_label))}</span></div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with quote_cols[1]:
        st.markdown(
            "<div class='research-card'><div class='quote-top'>"
            "<div><div class='quote-symbol'>Intraday Price</div>"
            "<div class='quote-label'>Current session</div></div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
        if quote.get("status") == "Error":
            st.error(f"Quote unavailable: {quote.get('message', 'Unknown error')}")
        elif intraday is None or intraday.empty:
            st.info("Intraday quote chart is unavailable for this symbol right now.")
        else:
            render_time_series_chart(
                intraday,
                "Price",
                "Price ($)",
                height=180,
                color="#5ec7e8",
            )
    return quote


def render_section_title(title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f"<span class='section-title-sub'>{html.escape(subtitle)}</span>"
        if subtitle
        else ""
    )
    st.markdown(
        "<div class='section-title'>"
        f"<div><span class='section-title-main'>{html.escape(title)}</span>{subtitle_html}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def base_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.properties(background="transparent")
        .configure_view(stroke="transparent")
        .configure_axis(
            domainColor="#23424d",
            gridColor="#19313a",
            labelColor="#92aab2",
            labelFont="Segoe UI",
            labelFontSize=11,
            titleColor="#92aab2",
            titleFont="Segoe UI",
            titleFontSize=11,
            titleFontWeight=700,
            tickColor="#23424d",
        )
        .configure_legend(
            labelColor="#d7e7e9",
            labelFont="Segoe UI",
            labelFontSize=11,
            titleColor="#92aab2",
            titleFont="Segoe UI",
            titleFontSize=11,
            orient="top",
        )
    )


def render_time_series_chart(
    frame: pd.DataFrame,
    value_column: str,
    y_title: str,
    height: int = 230,
    color: str = "#5ec7e8",
) -> None:
    if frame.empty or value_column not in frame:
        st.info("No chart data available.")
        return
    chart_frame = frame[[value_column]].dropna().reset_index()
    if chart_frame.empty:
        st.info("No chart data available.")
        return
    x_column = chart_frame.columns[0]
    chart_frame = chart_frame.rename(columns={x_column: "Date"})
    chart = (
        alt.Chart(chart_frame)
        .mark_line(color=color, strokeWidth=2)
        .encode(
            x=alt.X("Date:T", title=None, axis=alt.Axis(format="%b %d")),
            y=alt.Y(f"{value_column}:Q", title=y_title),
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip(f"{value_column}:Q", title=value_column, format=",.2f"),
            ],
        )
        .properties(height=height)
    )
    st.altair_chart(base_chart(chart), use_container_width=True)


def render_multi_series_chart(
    frame: pd.DataFrame,
    index_column: str,
    value_columns: list[str],
    chart_type: str,
    y_title: str,
    value_scale: float = 1.0,
    height: int = 240,
) -> None:
    available = [column for column in value_columns if column in frame and frame[column].notna().any()]
    if frame.empty or not available or index_column not in frame:
        st.info("No chart data available.")
        return
    chart_frame = frame[[index_column] + available].copy()
    for column in available:
        chart_frame[column] = pd.to_numeric(chart_frame[column], errors="coerce") / value_scale
    chart_frame = chart_frame.melt(index_column, var_name="Series", value_name="Value").dropna()
    if chart_frame.empty:
        st.info("No chart data available.")
        return
    encoding = dict(
        x=alt.X(f"{index_column}:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Value:Q", title=y_title),
        color=alt.Color(
            "Series:N",
            scale=alt.Scale(range=["#5ec7e8", "#49d69b", "#9bdcf3", "#ef6f7b", "#d5c56f"]),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip(f"{index_column}:N", title=index_column),
            alt.Tooltip("Series:N", title="Series"),
            alt.Tooltip("Value:Q", title=y_title, format=",.2f"),
        ],
    )
    if chart_type == "line":
        chart = alt.Chart(chart_frame).mark_line(point=True, strokeWidth=2).encode(**encoding)
    else:
        chart = (
            alt.Chart(chart_frame)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(**encoding, xOffset=alt.XOffset("Series:N"))
        )
    st.altair_chart(base_chart(chart.properties(height=height)), use_container_width=True)


def render_single_bar_chart(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    y_title: str,
    height: int = 210,
    color: str = "#5ec7e8",
) -> None:
    if frame.empty or x_column not in frame or y_column not in frame:
        st.info("No chart data available.")
        return
    chart_frame = frame[[x_column, y_column]].dropna()
    if chart_frame.empty:
        st.info("No chart data available.")
        return
    chart = (
        alt.Chart(chart_frame)
        .mark_bar(color=color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(f"{x_column}:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{y_column}:Q", title=y_title),
            tooltip=[
                alt.Tooltip(f"{x_column}:N", title=x_column),
                alt.Tooltip(f"{y_column}:Q", title=y_title, format=",.2f"),
            ],
        )
        .properties(height=height)
    )
    st.altair_chart(base_chart(chart), use_container_width=True)


def render_macro_factor_chart(frame: pd.DataFrame, refreshed_at: datetime, source_summary: str) -> None:
    if frame.empty:
        st.info("No current signals were detected for the tracked socioeconomic categories.")
        st.caption(
            "Stress scores combine macro headlines and scheduled economic releases. "
            "Categories without current inputs are treated as No current signals."
        )
        return

    chart_frame = frame.copy()
    chart_frame["Stress Score"] = pd.to_numeric(chart_frame["Stress Score"], errors="coerce")
    chart_frame["Raw Score"] = pd.to_numeric(chart_frame["Raw Score"], errors="coerce")
    chart_frame = chart_frame.dropna(subset=["Category", "Stress Score"])
    if chart_frame.empty:
        st.info("No current signals were detected for the tracked socioeconomic categories.")
        return

    height = max(210, min(380, 44 + 34 * len(chart_frame)))
    sort_order = alt.SortField(field="Stress Score", order="descending")
    bars = (
        alt.Chart(chart_frame)
        .mark_bar(color="#5ec7e8", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(
                "Stress Score:Q",
                title="Stress score",
                scale=alt.Scale(domain=[0, max(100, float(chart_frame["Stress Score"].max() or 0))]),
                axis=alt.Axis(format=".0f"),
            ),
            y=alt.Y(
                "Category:N",
                title=None,
                sort=sort_order,
                axis=alt.Axis(labelLimit=220, labelPadding=8),
            ),
            tooltip=[
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Stress Score:Q", title="Displayed stress", format=".1f"),
                alt.Tooltip("Raw Score:Q", title="Raw signal score", format=".1f"),
                alt.Tooltip("Signal State:N", title="State"),
            ],
        )
    )
    labels = (
        alt.Chart(chart_frame)
        .mark_text(align="left", baseline="middle", dx=6, color="#d7e7e9", fontSize=11, fontWeight=700)
        .encode(
            x=alt.X("Stress Score:Q", scale=alt.Scale(domain=[0, max(100, float(chart_frame["Stress Score"].max() or 0))])),
            y=alt.Y("Category:N", sort=sort_order),
            text=alt.Text("Stress Score:Q", format=".0f"),
        )
    )
    st.altair_chart(base_chart((bars + labels).properties(height=height)), use_container_width=True)
    source_text = source_summary or "RSS headlines and scheduled economic releases"
    st.caption(
        "Stress score reflects current macro headline pressure plus upcoming scheduled economic releases; "
        "category bars are capped at 100 for readability and sorted by current stress. "
        f"Categories not shown have no current signals. Last refreshed: {refreshed_at.strftime('%Y-%m-%d %I:%M %p ET').lstrip('0')} | Sources: {source_text}."
    )


def render_sector_performance_chart(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("Sector performance data is unavailable.")
        return
    chart_frame = frame[["Sector", "Daily Change %"]].dropna().copy()
    if chart_frame.empty:
        st.info("Sector performance data is unavailable.")
        return
    chart_frame["Tone"] = chart_frame["Daily Change %"].map(lambda value: "Positive" if value >= 0 else "Negative")
    sort_order = alt.SortField(field="Daily Change %", order="descending")
    bars = (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("Daily Change %:Q", title="Daily performance", axis=alt.Axis(format=".2f")),
            y=alt.Y("Sector:N", title=None, sort=sort_order, axis=alt.Axis(labelLimit=180)),
            color=alt.Color(
                "Tone:N",
                scale=alt.Scale(domain=["Positive", "Negative"], range=["#49d69b", "#ef6f7b"]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Sector:N", title="Sector"),
                alt.Tooltip("Daily Change %:Q", title="Daily change", format="+.2f"),
            ],
        )
    )
    labels = (
        alt.Chart(chart_frame)
        .mark_text(align="left", baseline="middle", dx=5, color="#d7e7e9", fontSize=10, fontWeight=700)
        .encode(
            x=alt.X("Daily Change %:Q"),
            y=alt.Y("Sector:N", sort=sort_order),
            text=alt.Text("Daily Change %:Q", format="+.2f"),
        )
    )
    st.altair_chart(base_chart((bars + labels).properties(height=285)), use_container_width=True)


def render_dashboard_table(frame: pd.DataFrame, **kwargs) -> None:
    display = frame.copy()
    display = display.fillna("N/A")
    height = kwargs.pop("height", min(420, max(130, 42 + (len(display) + 1) * 35)))
    table_styles = [
        {
            "selector": "th",
            "props": [
                ("background-color", "#10212a"),
                ("color", "#d7e7e9"),
                ("border-color", "#19313a"),
                ("font-weight", "800"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("background-color", "#0b171c"),
                ("color", "#d7e7e9"),
                ("border-color", "#19313a"),
            ],
        },
    ]
    styled = (
        display.style.set_table_styles(table_styles)
        .set_properties(**{"background-color": "#0b171c", "color": "#d7e7e9", "border-color": "#19313a"})
    )
    st.dataframe(
        styled,
        hide_index=kwargs.pop("hide_index", True),
        use_container_width=kwargs.pop("use_container_width", True),
        height=height,
        **kwargs,
    )


def render_scheduled_reports_table(frame: pd.DataFrame, **kwargs) -> None:
    if frame.empty:
        st.info("No scheduled economic releases match the current filters.")
        return
    essential_columns = [
        "Report Name",
        "Release Date",
        "Release Time",
        "Category",
        "Impact",
        "Source",
        "Previous",
        "Forecast",
        "Actual",
        "Last Updated",
    ]
    display = frame[[column for column in essential_columns if column in frame.columns]].copy().fillna("N/A")
    height = kwargs.pop("height", min(440, max(160, 42 + (len(display) + 1) * 35)))

    def impact_row_style(row: pd.Series) -> list[str]:
        impact = str(row.get("Impact", "")).casefold()
        if impact == "high":
            background = "#2a151a"
            color = "#f2f7f8"
        elif impact == "medium":
            background = "#221f14"
            color = "#edf2dc"
        else:
            background = "#0b171c"
            color = "#d7e7e9"
        return [f"background-color: {background}; color: {color}; border-color: #19313a"] * len(row)

    styled = (
        display.style.apply(impact_row_style, axis=1)
        .set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#10212a"),
                        ("color", "#d7e7e9"),
                        ("border-color", "#19313a"),
                        ("font-weight", "800"),
                    ],
                },
                {
                    "selector": "td",
                    "props": [
                        ("border-color", "#19313a"),
                    ],
                },
            ]
        )
        .set_properties(**{"font-size": "0.78rem"})
    )
    st.dataframe(
        styled,
        hide_index=kwargs.pop("hide_index", True),
        use_container_width=kwargs.pop("use_container_width", True),
        height=height,
        column_config={
            "Report Name": st.column_config.TextColumn(
                "Report Name",
                help="Scheduled economic or policy release.",
                width="large",
            ),
            "Release Date": st.column_config.TextColumn("Release Date", width="small"),
            "Release Time": st.column_config.TextColumn(
                "Release Time",
                help="Scheduled release time in Eastern Time when available.",
                width="small",
            ),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Impact": st.column_config.TextColumn(
                "Impact",
                help="Expected relative market impact from the event category.",
                width="small",
            ),
            "Source": st.column_config.TextColumn("Source", width="small"),
            "Previous": st.column_config.TextColumn(
                "Previous",
                help="Previous value if provided by the source.",
                width="small",
            ),
            "Forecast": st.column_config.TextColumn(
                "Forecast",
                help="Consensus forecast if provided by the source.",
                width="small",
            ),
            "Actual": st.column_config.TextColumn(
                "Actual",
                help="Actual value after release if provided by the source.",
                width="small",
            ),
            "Last Updated": st.column_config.TextColumn("Last Updated", width="medium"),
        },
        **kwargs,
    )


def render_compact_scheduled_reports_table(frame: pd.DataFrame, height: int = 250) -> None:
    if frame.empty:
        st.info("No scheduled economic releases match the current filters.")
        return
    columns = ["Report Name", "Release Date", "Release Time", "Category", "Impact", "Source"]
    display = frame[[column for column in columns if column in frame.columns]].copy().fillna("N/A")
    if "Release Date" in display:
        display["Release Date"] = pd.to_datetime(display["Release Date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("N/A")
    display["Impact"] = display["Impact"].map(lambda value: str(value).title())
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        height=height,
        column_config={
            "Report Name": st.column_config.TextColumn("Report Name", width="medium"),
            "Release Date": st.column_config.TextColumn("Date", width="small"),
            "Release Time": st.column_config.TextColumn("Time", width="small"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Impact": st.column_config.TextColumn("Impact", width="small"),
            "Source": st.column_config.TextColumn("Source", width="small"),
        },
    )


def render_price_target_range(price_target_df: pd.DataFrame) -> None:
    if price_target_df.empty:
        return
    row = price_target_df.iloc[0]
    current = coerce_float(row.get("Actual"))
    low = coerce_float(row.get("Target Low"))
    target = coerce_float(row.get("Target"))
    high = coerce_float(row.get("Target High"))
    values = [value for value in [current, low, target, high] if value is not None and not pd.isna(value)]
    if len(values) < 2:
        return
    range_low = min(values)
    range_high = max(values)
    if range_high == range_low:
        return

    def marker_position(value: float | None) -> float | None:
        if value is None or pd.isna(value):
            return None
        return (float(value) - range_low) / (range_high - range_low) * 100

    current_pos = marker_position(current)
    target_pos = marker_position(target)
    current_marker = (
        f"<span class='range-marker' title='Current' style='left:{current_pos:.2f}%;'></span>"
        if current_pos is not None
        else ""
    )
    target_marker = (
        f"<span class='range-marker target' title='Target' style='left:{target_pos:.2f}%;'></span>"
        if target_pos is not None
        else ""
    )
    st.markdown(
        "<div class='price-range'>"
        "<div class='range-label-row'>"
        f"<span>Low {html.escape(format_currency(low, 2))}</span>"
        f"<span>Current {html.escape(format_currency(current, 2))}</span>"
        f"<span>Target {html.escape(format_currency(target, 2))}</span>"
        f"<span>High {html.escape(format_currency(high, 2))}</span>"
        "</div>"
        f"<div class='range-track'><div class='range-fill'></div>{current_marker}{target_marker}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def format_report_date(value: object) -> str:
    parsed = parse_date(value)
    return parsed.strftime("%Y-%m-%d") if parsed else "N/A"


def render_analyst_reports(frame: pd.DataFrame, refreshed_at: datetime | None) -> None:
    if frame.empty:
        st.info("No linked analyst reports available for this ticker yet.")
        return
    st.caption(
        "Public analyst-related report pages and headlines only. Paywalled research is not scraped or bypassed. "
        + (
            f"Last refreshed: {refreshed_at.strftime('%Y-%m-%d %I:%M %p ET').lstrip('0')}"
            if refreshed_at
            else "Last refreshed: N/A"
        )
    )
    cards = ["<div class='research-report-list'>"]
    for _, row in frame.iterrows():
        title = html.escape(str(row.get("Report Title") or "Untitled report"))
        url = str(row.get("Source URL") or "").strip()
        title_html = (
            f"<a class='research-report-title' href='{html.escape(url)}' target='_blank' rel='noopener noreferrer'>{title}</a>"
            if url
            else f"<span class='research-report-title'>{title}</span>"
        )
        meta_parts = [
            str(row.get("Analyst Firm / Source") or "N/A"),
            format_report_date(row.get("Publication Date")),
            f"Rating: {row.get('Rating') or 'N/A'}",
            f"Target: {format_currency(row.get('Price Target'), 2)}",
            f"Prev: {format_currency(row.get('Previous Price Target'), 2)}",
        ]
        analyst = str(row.get("Analyst") or "N/A")
        if analyst != "N/A":
            meta_parts.insert(1, analyst)
        summary = clean_text(str(row.get("Summary") or ""))
        if len(summary) > 260:
            summary = summary[:257].rstrip() + "..."
        cards.append(
            "<div class='research-report-card'>"
            f"{title_html}"
            "<div class='research-report-meta'>"
            + "".join(f"<span>{html.escape(part)}</span>" for part in meta_parts)
            + "</div>"
            f"<div class='research-report-summary'>{html.escape(summary or 'No public summary available.')}</div>"
            "</div>"
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def safe_ui_key(value: object) -> str:
    key = re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_").lower()
    return key or "item"


def render_button_strip(
    items: list[dict[str, object]],
    state_key: str,
    default_key: str | None = None,
) -> str | None:
    if not items:
        return None
    item_keys = [str(item["key"]) for item in items]
    active_key = st.session_state.get(state_key, default_key)
    if active_key not in item_keys:
        active_key = default_key if default_key in item_keys else None

    columns = st.columns(len(items), gap="small")
    for column, item in zip(columns, items):
        item_key = str(item["key"])
        with column:
            if st.button(
                str(item.get("label", item_key)),
                key=f"{state_key}_{safe_ui_key(item_key)}",
                type="primary" if active_key == item_key else "secondary",
                use_container_width=True,
                help=str(item.get("help", "")) if item.get("help") else None,
            ):
                active_key = item_key
    st.session_state[state_key] = active_key
    return active_key


def render_sankey_header(
    title: str,
    subtitle: str,
    *,
    animate: bool,
    delay: int,
    meta_text: str,
) -> None:
    animation_class = f" sankey-intro sankey-delay-{delay}" if animate else ""
    st.markdown(
        f"<div class='sankey-tile-head{animation_class}'>"
        f"<div><span class='sankey-tile-title'>{html.escape(title)}</span>"
        f"<span class='sankey-tile-meta'>{html.escape(subtitle)}</span></div>"
        f"<span class='sankey-tile-meta'>{html.escape(meta_text)}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_sankey_plot(
    title: str,
    normalized: pd.DataFrame,
    payload_builder,
    *,
    chart_key: str,
    note: str,
) -> dict[str, object]:
    links, node_values, negative_notes = payload_builder(normalized)
    if plotly_go() is None:
        render_sankey_svg_flow(links, node_values, title=title)
        return {"links": links, "nodes": node_values, "negative_notes": negative_notes, "rendered": False}
    figure = make_sankey_figure(title, links, node_values)
    if figure is None:
        st.markdown(
            "<div class='sankey-empty'>Insufficient statement line items were returned to build this Sankey chart.</div>",
            unsafe_allow_html=True,
        )
        return {"links": links, "nodes": node_values, "negative_notes": negative_notes, "rendered": False}
    st.markdown(
        "<div class='sankey-note'>"
        + html.escape(note)
        + " Flow widths use absolute values where source data is negative; labels identify losses and outflows."
        + "</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        figure,
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
        key=chart_key,
    )
    return {"links": links, "nodes": node_values, "negative_notes": negative_notes, "rendered": True}


def render_sankey_normalized_expander(title: str, normalized: pd.DataFrame) -> None:
    with st.expander(title, expanded=False):
        if normalized.empty:
            st.info("No normalized line items available.")
        else:
            render_dashboard_table(
                normalized_sankey_display(normalized),
                height=table_height_for_rows(normalized, min_height=160, max_height=360),
            )


def render_income_sankey_tile(
    ticker: str,
    frame: pd.DataFrame,
    selected_period: object,
    previous_period: object | None,
    period_text: str,
    meta_text: str,
    *,
    chart_key_suffix: str,
    animate: bool,
    show_normalized: bool,
) -> dict[str, object]:
    with st.container(border=True):
        render_sankey_header(
            "Income Statement Flow",
            f"{ticker} | {period_text}",
            animate=animate,
            delay=1,
            meta_text=meta_text,
        )
        normalized = normalize_sankey_statement(frame, INCOME_SANKEY_FIELDS, selected_period, previous_period, "Revenue")
        revenue = sankey_value(normalized, "Revenue")
        gross_profit = sankey_value(normalized, "Gross Profit")
        operating_income = sankey_value(normalized, "Operating Income")
        net_income = sankey_value(normalized, "Net Income")
        cards = [
            {"label": "Revenue", "value": format_compact_currency(revenue, 2), "context": "top line"},
            {"label": "Gross Profit", "value": format_compact_currency(gross_profit, 2), "context": format_percent(safe_ratio(gross_profit, revenue, 100), 1)},
            {"label": "Operating Income", "value": format_compact_currency(operating_income, 2), "context": format_percent(safe_ratio(operating_income, revenue, 100), 1), "tone": quote_tone(operating_income)},
            {"label": "Net Income", "value": format_compact_currency(net_income, 2), "context": format_percent(safe_ratio(net_income, revenue, 100), 1), "tone": quote_tone(net_income)},
            {"label": "EPS", "value": format_number(sankey_value(normalized, "EPS"), 2), "context": "diluted if available"},
        ]
        render_metric_strip(cards, columns=5)
        debug = render_sankey_plot(
            "Income statement flow",
            normalized,
            income_sankey_payload,
            chart_key=f"sankey_income_{chart_key_suffix}",
            note="Income statement flow traces revenue through expenses, profit, taxes, and net income.",
        )
        if show_normalized:
            render_sankey_normalized_expander("Normalized Income Statement Data", normalized)
        available, missing = sankey_fields_debug(normalized)
        debug.update({"available_fields": available, "missing_fields": missing})
        return debug


def render_balance_sankey_tile(
    ticker: str,
    frame: pd.DataFrame,
    selected_period: object,
    previous_period: object | None,
    period_text: str,
    meta_text: str,
    *,
    chart_key_suffix: str,
    animate: bool,
    show_normalized: bool,
) -> dict[str, object]:
    with st.container(border=True):
        render_sankey_header(
            "Balance Sheet Flow",
            f"{ticker} | {period_text}",
            animate=animate,
            delay=2,
            meta_text=meta_text,
        )
        normalized = normalize_sankey_statement(frame, BALANCE_SANKEY_FIELDS, selected_period, previous_period, "Total Assets")
        total_assets = sankey_value(normalized, "Total Assets")
        cash = sankey_value(normalized, "Cash")
        total_liabilities = sankey_value(normalized, "Total Liabilities")
        total_debt = sankey_value(normalized, "Total Debt")
        equity = sankey_value(normalized, "Shareholders' Equity")
        cards = [
            {"label": "Total Assets", "value": format_compact_currency(total_assets, 2), "context": "asset base"},
            {"label": "Cash", "value": format_compact_currency(cash, 2), "context": "liquidity"},
            {"label": "Total Liabilities", "value": format_compact_currency(total_liabilities, 2), "context": "claims"},
            {"label": "Total Debt", "value": format_compact_currency(total_debt, 2), "context": format_percent(safe_ratio(total_debt, total_assets, 100), 1)},
            {"label": "Equity", "value": format_compact_currency(equity, 2), "context": "book value"},
            {"label": "Cash / Debt", "value": format_number(safe_ratio(cash, total_debt, 1), 2), "context": "coverage"},
        ]
        render_metric_strip(cards, columns=6)
        debug = render_sankey_plot(
            "Balance sheet flow",
            normalized,
            balance_sankey_payload,
            chart_key=f"sankey_balance_{chart_key_suffix}",
            note="Balance sheet flow shows asset composition and the Assets = Liabilities + Equity relationship.",
        )
        if show_normalized:
            render_sankey_normalized_expander("Normalized Balance Sheet Data", normalized)
        available, missing = sankey_fields_debug(normalized)
        debug.update({"available_fields": available, "missing_fields": missing})
        return debug


def render_cash_flow_sankey_tile(
    ticker: str,
    frame: pd.DataFrame,
    selected_period: object,
    previous_period: object | None,
    period_text: str,
    meta_text: str,
    *,
    chart_key_suffix: str,
    animate: bool,
    show_normalized: bool,
) -> dict[str, object]:
    with st.container(border=True):
        render_sankey_header(
            "Cash Flow Statement Flow",
            f"{ticker} | {period_text}",
            animate=animate,
            delay=3,
            meta_text=meta_text,
        )
        normalized = normalize_sankey_statement(frame, CASH_FLOW_SANKEY_FIELDS, selected_period, previous_period, "Operating Cash Flow")
        ocf = sankey_value(normalized, "Operating Cash Flow")
        capex = sankey_value(normalized, "Capital Expenditures")
        fcf = sankey_value(normalized, "Free Cash Flow")
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex
        investing = sankey_value(normalized, "Investing Cash Flow")
        financing = sankey_value(normalized, "Financing Cash Flow")
        net_change = sankey_value(normalized, "Net Change in Cash")
        cards = [
            {"label": "Operating CF", "value": format_compact_currency(ocf, 2), "context": "operations", "tone": quote_tone(ocf)},
            {"label": "Capex", "value": format_compact_currency(capex, 2), "context": "cash outflow", "tone": "bad" if capex is not None else "neutral"},
            {"label": "Free CF", "value": format_compact_currency(fcf, 2), "context": "post-capex", "tone": quote_tone(fcf)},
            {"label": "Investing CF", "value": format_compact_currency(investing, 2), "context": "investing", "tone": quote_tone(investing)},
            {"label": "Financing CF", "value": format_compact_currency(financing, 2), "context": "financing", "tone": quote_tone(financing)},
            {"label": "Net Cash Change", "value": format_compact_currency(net_change, 2), "context": "period", "tone": quote_tone(net_change)},
        ]
        render_metric_strip(cards, columns=6)
        debug = render_sankey_plot(
            "Cash flow statement flow",
            normalized,
            cash_flow_sankey_payload,
            chart_key=f"sankey_cash_{chart_key_suffix}",
            note="Cash-flow flow traces operating cash through capex, free cash flow, investing, financing, and net cash change.",
        )
        if show_normalized:
            render_sankey_normalized_expander("Normalized Cash Flow Data", normalized)
        available, missing = sankey_fields_debug(normalized)
        debug.update({"available_fields": available, "missing_fields": missing})
        return debug


def previous_sankey_period(periods_desc: Sequence[pd.Timestamp], selected_period: object) -> pd.Timestamp | None:
    periods_asc = sorted(periods_desc)
    try:
        selected = pd.Timestamp(selected_period)
    except Exception:
        return None
    for index, period in enumerate(periods_asc):
        if period == selected or period.date() == selected.date():
            return periods_asc[index - 1] if index > 0 else None
    return None


def normalize_statement_history(
    frame: pd.DataFrame,
    field_map: dict[str, tuple[str, ...]],
    periods: Sequence[pd.Timestamp],
    quarterly: bool,
    base_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    raw_rows = []
    previous_values: dict[str, float | None] = {}
    ordered_periods = sorted(pd.Timestamp(period) for period in periods)
    for period in ordered_periods:
        row = {"Period": period_label(period, quarterly), "Period Date": period}
        value_lookup: dict[str, float | None] = {}
        source_lookup: dict[str, str] = {}
        for label, aliases in field_map.items():
            value, source = statement_line_value(frame, period, aliases)
            row[label] = value
            value_lookup[label] = value
            source_lookup[label] = source or "N/A"
        base_value = value_lookup.get(base_label)
        for label in field_map:
            value = value_lookup.get(label)
            previous = previous_values.get(label)
            change = safe_ratio(value - previous, abs(previous), 100) if value is not None and previous not in (None, 0) else None
            raw_rows.append(
                {
                    "Period": row["Period"],
                    "Period Date": period,
                    "Line Item": label,
                    "Value": value,
                    "Percent of Base": safe_ratio(value, base_value, 100) if value is not None and base_value else None,
                    "Source Field": source_lookup.get(label, "N/A"),
                    "Change %": change,
                }
            )
            previous_values[label] = value
        rows.append(row)
    wide = pd.DataFrame(rows)
    raw = pd.DataFrame(raw_rows)
    return derive_three_statement_fields(wide, base_label), raw


def derive_three_statement_fields(frame: pd.DataFrame, base_label: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    derived = frame.copy()
    if base_label == "Revenue":
        if "Operating Expenses" not in derived or derived["Operating Expenses"].isna().all():
            if {"Gross Profit", "Operating Income"}.issubset(derived.columns):
                derived["Operating Expenses"] = derived["Gross Profit"] - derived["Operating Income"]
        if "Pretax Income" not in derived or derived["Pretax Income"].isna().all():
            if {"Net Income", "Taxes"}.issubset(derived.columns):
                derived["Pretax Income"] = derived["Net Income"] + derived["Taxes"]
        if "Revenue" in derived:
            derived["Gross Margin %"] = derived.apply(lambda row: safe_ratio(row.get("Gross Profit"), row.get("Revenue"), 100), axis=1)
            derived["Operating Margin %"] = derived.apply(lambda row: safe_ratio(row.get("Operating Income"), row.get("Revenue"), 100), axis=1)
            derived["Net Margin %"] = derived.apply(lambda row: safe_ratio(row.get("Net Income"), row.get("Revenue"), 100), axis=1)
    elif base_label == "Total Assets":
        if "Total Debt" not in derived or derived["Total Debt"].isna().all():
            debt_cols = [col for col in ["Long-term Debt", "Short-term Debt"] if col in derived]
            if debt_cols:
                derived["Total Debt"] = derived[debt_cols].sum(axis=1, min_count=1)
        if "Net Debt" not in derived:
            if {"Total Debt", "Cash"}.issubset(derived.columns):
                derived["Net Debt"] = derived["Total Debt"] - derived["Cash"]
        component_cols = [
            col
            for col in ["Cash", "Accounts Receivable", "Inventory", "PP&E", "Goodwill / Intangibles"]
            if col in derived
        ]
        if "Other Assets" not in derived and "Total Assets" in derived and component_cols:
            derived["Other Assets"] = derived["Total Assets"] - derived[component_cols].sum(axis=1, min_count=1)
        if {"Current Assets", "Current Liabilities"}.issubset(derived.columns):
            derived["Current Ratio"] = derived.apply(lambda row: safe_ratio(row.get("Current Assets"), row.get("Current Liabilities"), 1), axis=1)
        if {"Total Debt", "Shareholders' Equity"}.issubset(derived.columns):
            derived["Debt / Equity"] = derived.apply(lambda row: safe_ratio(row.get("Total Debt"), row.get("Shareholders' Equity"), 1), axis=1)
        if {"Cash", "Total Debt"}.issubset(derived.columns):
            derived["Cash / Debt"] = derived.apply(lambda row: safe_ratio(row.get("Cash"), row.get("Total Debt"), 1), axis=1)
    elif base_label == "Operating Cash Flow":
        if "Free Cash Flow" not in derived or derived["Free Cash Flow"].isna().all():
            if {"Operating Cash Flow", "Capital Expenditures"}.issubset(derived.columns):
                derived["Free Cash Flow"] = derived["Operating Cash Flow"] + derived["Capital Expenditures"]
    return derived


def add_change_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    enriched = frame.copy()
    for column in columns:
        if column in enriched:
            enriched[f"{column} Change %"] = pd.to_numeric(enriched[column], errors="coerce").pct_change() * 100
    return enriched


def latest_row(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    return frame.sort_values("Period Date").iloc[-1]


def previous_row(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or len(frame.sort_values("Period Date")) < 2:
        return pd.Series(dtype=object)
    return frame.sort_values("Period Date").iloc[-2]


def latest_change(frame: pd.DataFrame, column: str) -> float | None:
    ordered = frame.sort_values("Period Date") if "Period Date" in frame else frame
    if column not in ordered or len(ordered) < 2:
        return None
    current = coerce_float(ordered.iloc[-1].get(column))
    previous = coerce_float(ordered.iloc[-2].get(column))
    return safe_ratio(current - previous, abs(previous), 100) if current is not None and previous not in (None, 0) else None


def plotly_base_layout(fig, height: int) -> None:
    fig.update_layout(
        paper_bgcolor="#071013",
        plot_bgcolor="#071013",
        font={"color": "#d7e7e9", "family": "Inter, Segoe UI, Arial", "size": 11},
        margin={"l": 8, "r": 8, "t": 34, "b": 24},
        height=height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )


def waterfall_altair_frame(steps: list[dict[str, object]]) -> pd.DataFrame:
    rows = []
    running = 0.0
    for index, step in enumerate(steps):
        value = coerce_float(step.get("value"))
        if value is None:
            continue
        measure = str(step.get("measure") or "relative")
        if measure == "absolute":
            start, end = 0.0, value
            running = value
        elif measure == "total":
            start, end = 0.0, value
            running = value
        else:
            start, end = running, running + value
            running = end
        rows.append(
            {
                "Step": str(step.get("label")),
                "Order": index,
                "Start": min(start, end) / 1_000_000_000,
                "End": max(start, end) / 1_000_000_000,
                "Value": value / 1_000_000_000,
                "Tone": "Positive" if value >= 0 else "Negative",
            }
        )
    return pd.DataFrame(rows)


def render_waterfall_chart(title: str, steps: list[dict[str, object]], *, key: str, height: int = 295) -> bool:
    clean_steps = [step for step in steps if coerce_float(step.get("value")) is not None]
    if not clean_steps:
        st.info("No waterfall data available.")
        return False
    plotly_module = plotly_go()
    if plotly_module is not None:
        fig = plotly_module.Figure(
            plotly_module.Waterfall(
                name=title,
                orientation="v",
                measure=[str(step.get("measure") or "relative") for step in clean_steps],
                x=[str(step.get("label")) for step in clean_steps],
                y=[coerce_float(step.get("value")) or 0 for step in clean_steps],
                text=[format_compact_currency(step.get("value"), 1) for step in clean_steps],
                textposition="outside",
                connector={"line": {"color": "#23424d"}},
                increasing={"marker": {"color": "#49d69b"}},
                decreasing={"marker": {"color": "#ef6f7b"}},
                totals={"marker": {"color": "#5ec7e8"}},
                hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>",
            )
        )
        plotly_base_layout(fig, height)
        fig.update_yaxes(title="Amount ($)", gridcolor="#19313a", zerolinecolor="#23424d")
        fig.update_xaxes(tickangle=-20)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)
        return True

    chart_frame = waterfall_altair_frame(clean_steps)
    if chart_frame.empty:
        st.info("No waterfall data available.")
        return False
    chart = (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Step:N", sort=alt.SortField("Order"), title=None, axis=alt.Axis(labelAngle=-20)),
            y=alt.Y("Start:Q", title="Amount ($B)"),
            y2="End:Q",
            color=alt.Color("Tone:N", scale=alt.Scale(domain=["Positive", "Negative"], range=["#49d69b", "#ef6f7b"]), legend=None),
            tooltip=[alt.Tooltip("Step:N"), alt.Tooltip("Value:Q", title="Amount ($B)", format=",.2f")],
        )
        .properties(height=height)
    )
    st.altair_chart(base_chart(chart), use_container_width=True)
    return True


def render_line_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str, *, key: str, value_scale: float = 1.0, height: int = 250) -> bool:
    available = [column for column in columns if column in frame and pd.to_numeric(frame[column], errors="coerce").notna().any()]
    if frame.empty or "Period" not in frame or not available:
        st.info("No trend data available.")
        return False
    plotly_module = plotly_go()
    if plotly_module is not None:
        ordered = frame.sort_values("Period Date") if "Period Date" in frame else frame
        fig = plotly_module.Figure()
        colors = ["#5ec7e8", "#49d69b", "#9bdcf3", "#ef6f7b", "#d5c56f", "#a7b4ff"]
        for index, column in enumerate(available):
            fig.add_trace(
                plotly_module.Scatter(
                    x=ordered["Period"],
                    y=pd.to_numeric(ordered[column], errors="coerce") / value_scale,
                    mode="lines+markers",
                    name=column,
                    line={"color": colors[index % len(colors)], "width": 2},
                    hovertemplate=f"{column}<br>%{{x}}<br>%{{y:,.2f}}<extra></extra>",
                )
            )
        plotly_base_layout(fig, height)
        fig.update_yaxes(title=y_title, gridcolor="#19313a", zerolinecolor="#23424d")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)
        return True
    render_multi_series_chart(frame, "Period", available, "line", y_title, value_scale=value_scale, height=height)
    return True


def render_bar_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str, *, key: str, value_scale: float = 1.0, stacked: bool = False, height: int = 255) -> bool:
    available = [column for column in columns if column in frame and pd.to_numeric(frame[column], errors="coerce").notna().any()]
    if frame.empty or "Period" not in frame or not available:
        st.info("No chart data available.")
        return False
    plotly_module = plotly_go()
    if plotly_module is not None:
        ordered = frame.sort_values("Period Date") if "Period Date" in frame else frame
        fig = plotly_module.Figure()
        colors = ["#5ec7e8", "#49d69b", "#9bdcf3", "#ef6f7b", "#d5c56f", "#a7b4ff", "#92aab2"]
        for index, column in enumerate(available):
            fig.add_trace(
                plotly_module.Bar(
                    x=ordered["Period"],
                    y=pd.to_numeric(ordered[column], errors="coerce") / value_scale,
                    name=column,
                    marker={"color": colors[index % len(colors)]},
                    hovertemplate=f"{column}<br>%{{x}}<br>%{{y:,.2f}}<extra></extra>",
                )
            )
        plotly_base_layout(fig, height)
        fig.update_layout(barmode="stack" if stacked else "group")
        fig.update_yaxes(title=y_title, gridcolor="#19313a", zerolinecolor="#23424d")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)
        return True
    render_multi_series_chart(frame, "Period", available, "bar", y_title, value_scale=value_scale, height=height)
    return True


def render_balance_composition_chart(frame: pd.DataFrame, *, key: str) -> bool:
    if frame.empty:
        st.info("No balance sheet composition data available.")
        return False
    plotly_module = plotly_go()
    if plotly_module is not None:
        ordered = frame.sort_values("Period Date")
        fig = plotly_module.Figure()
        for column, color in [("Total Liabilities", "#ef6f7b"), ("Shareholders' Equity", "#49d69b")]:
            if column in ordered:
                fig.add_trace(
                    plotly_module.Bar(
                        x=ordered["Period"],
                        y=pd.to_numeric(ordered[column], errors="coerce") / 1_000_000_000,
                        name=column,
                        marker={"color": color},
                    )
                )
        if "Total Assets" in ordered:
            fig.add_trace(
                plotly_module.Scatter(
                    x=ordered["Period"],
                    y=pd.to_numeric(ordered["Total Assets"], errors="coerce") / 1_000_000_000,
                    mode="lines+markers",
                    name="Total Assets",
                    line={"color": "#5ec7e8", "width": 2},
                )
            )
        plotly_base_layout(fig, 270)
        fig.update_layout(barmode="stack")
        fig.update_yaxes(title="Amount ($B)", gridcolor="#19313a", zerolinecolor="#23424d")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)
        return True
    return render_bar_chart(frame, ["Total Liabilities", "Shareholders' Equity", "Total Assets"], "Balance Sheet Composition", "Amount ($B)", key=key, value_scale=1_000_000_000, height=270)


def period_common_size_frame(frame: pd.DataFrame, columns: list[str], base_column: str) -> pd.DataFrame:
    if frame.empty or base_column not in frame:
        return pd.DataFrame()
    rows = []
    for _, row in frame.iterrows():
        base = coerce_float(row.get(base_column))
        for column in columns:
            if column not in frame:
                continue
            value = coerce_float(row.get(column))
            pct = safe_ratio(value, base, 100) if value is not None and base else None
            rows.append({"Period": row.get("Period"), "Line Item": column, "Percent": pct})
    return pd.DataFrame(rows).dropna(subset=["Percent"])


def render_common_size_chart(frame: pd.DataFrame, columns: list[str], base_column: str, title: str, *, key: str) -> bool:
    chart_frame = period_common_size_frame(frame, columns, base_column)
    if chart_frame.empty:
        st.info("Common-size data is unavailable.")
        return False
    plotly_module = plotly_go()
    if plotly_module is not None:
        fig = plotly_module.Figure()
        for column in columns:
            subset = chart_frame[chart_frame["Line Item"].eq(column)]
            if subset.empty:
                continue
            fig.add_trace(plotly_module.Bar(x=subset["Period"], y=subset["Percent"], name=column))
        plotly_base_layout(fig, 245)
        fig.update_layout(barmode="group")
        fig.update_yaxes(title="% of base", gridcolor="#19313a", zerolinecolor="#23424d")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)
        return True
    chart = (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Period:N", title=None),
            y=alt.Y("Percent:Q", title="% of base"),
            color=alt.Color("Line Item:N", legend=alt.Legend(title=None)),
            xOffset=alt.XOffset("Line Item:N"),
            tooltip=[alt.Tooltip("Period:N"), alt.Tooltip("Line Item:N"), alt.Tooltip("Percent:Q", format=".1f")],
        )
        .properties(height=245)
    )
    st.altair_chart(base_chart(chart), use_container_width=True)
    return True


def format_normalized_history_display(raw: pd.DataFrame, show_change: bool) -> pd.DataFrame:
    if raw.empty:
        return raw
    display = raw.copy()
    if not show_change and "Change %" in display:
        display = display.drop(columns=["Change %"])
    if "Period Date" in display:
        display["Period Date"] = pd.to_datetime(display["Period Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "Value" in display:
        display["Value"] = display["Value"].map(lambda value: format_compact_currency(value, 2))
    if "Percent of Base" in display:
        display["Percent of Base"] = display["Percent of Base"].map(lambda value: format_percent(value, 1))
    if "Change %" in display:
        display["Change %"] = display["Change %"].map(lambda value: format_percent(value, 1, signed=True))
    return display.fillna("N/A")


def latest_period_label(frame: pd.DataFrame) -> str:
    row = latest_row(frame)
    return str(row.get("Period", "N/A")) if not row.empty else "N/A"


def generate_three_statement_insights(income: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    latest_income = latest_row(income)
    prev_income = previous_row(income)
    latest_balance = latest_row(balance)
    prev_balance = previous_row(balance)
    latest_cash = latest_row(cashflow)
    prev_cash = previous_row(cashflow)

    revenue_growth = latest_change(income, "Revenue")
    if revenue_growth is not None:
        insights.append({
            "tone": "good" if revenue_growth >= 0 else "bad",
            "text": f"Revenue {'grew' if revenue_growth >= 0 else 'declined'} {format_percent(revenue_growth, 1)} in the latest selected period.",
        })

    for margin_name in ("Gross Margin %", "Operating Margin %", "Net Margin %"):
        current = coerce_float(latest_income.get(margin_name)) if not latest_income.empty else None
        previous = coerce_float(prev_income.get(margin_name)) if not prev_income.empty else None
        if current is not None and previous is not None:
            delta = current - previous
            insights.append({
                "tone": "good" if delta >= 0 else "bad",
                "text": f"{margin_name.replace(' %', '')} {'expanded' if delta >= 0 else 'contracted'} by {format_percent(delta, 1)} versus the prior selected period.",
            })

    net_income = coerce_float(latest_income.get("Net Income")) if not latest_income.empty else None
    fcf = coerce_float(latest_cash.get("Free Cash Flow")) if not latest_cash.empty else None
    if fcf is not None:
        insights.append({
            "tone": "good" if fcf >= 0 else "bad",
            "text": f"Free cash flow is {'positive' if fcf >= 0 else 'negative'} at {format_compact_currency(fcf, 2)}.",
        })
    if net_income is not None and fcf is not None and net_income:
        conversion = safe_ratio(fcf, net_income, 100)
        insights.append({
            "tone": "good" if conversion is not None and conversion >= 75 else "warn",
            "text": f"Free cash flow equals {format_percent(conversion, 1)} of net income, highlighting earnings-to-cash conversion quality.",
        })

    debt = coerce_float(latest_balance.get("Total Debt")) if not latest_balance.empty else None
    prev_debt = coerce_float(prev_balance.get("Total Debt")) if not prev_balance.empty else None
    if debt is not None and prev_debt not in (None, 0):
        debt_change = safe_ratio(debt - prev_debt, abs(prev_debt), 100)
        insights.append({
            "tone": "bad" if debt_change is not None and debt_change > 0 else "good",
            "text": f"Total debt {'increased' if (debt_change or 0) > 0 else 'decreased'} {format_percent(debt_change, 1)} versus the prior selected period.",
        })

    cash = coerce_float(latest_balance.get("Cash")) if not latest_balance.empty else None
    prev_cash_balance = coerce_float(prev_balance.get("Cash")) if not prev_balance.empty else None
    if cash is not None and prev_cash_balance not in (None, 0):
        cash_change = safe_ratio(cash - prev_cash_balance, abs(prev_cash_balance), 100)
        insights.append({
            "tone": "good" if cash_change is not None and cash_change >= 0 else "warn",
            "text": f"Cash balance {'increased' if (cash_change or 0) >= 0 else 'decreased'} {format_percent(cash_change, 1)} versus the prior selected period.",
        })

    capex = coerce_float(latest_cash.get("Capital Expenditures")) if not latest_cash.empty else None
    revenue = coerce_float(latest_income.get("Revenue")) if not latest_income.empty else None
    if capex is not None and revenue:
        capex_intensity = safe_ratio(abs(capex), revenue, 100)
        insights.append({
            "tone": "neutral",
            "text": f"Capital expenditures represent {format_percent(capex_intensity, 1)} of revenue in the latest selected period.",
        })

    if not insights:
        insights.append({"tone": "neutral", "text": "Not enough normalized statement history is available to generate dashboard signals."})
    return insights[:10]


def statement_row_value(row: pd.Series, column: str) -> float | None:
    return coerce_float(row.get(column)) if not row.empty else None


def statement_row_delta(current_row: pd.Series, previous_row_value: pd.Series, column: str) -> float | None:
    current = statement_row_value(current_row, column)
    previous = statement_row_value(previous_row_value, column)
    return current - previous if current is not None and previous is not None else None


def structured_statement_insight_tiles(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> list[dict[str, object]]:
    latest_income = latest_row(income)
    prev_income = previous_row(income)
    latest_balance = latest_row(balance)
    prev_balance = previous_row(balance)
    latest_cash = latest_row(cashflow)

    revenue = statement_row_value(latest_income, "Revenue")
    revenue_growth = latest_change(income, "Revenue")
    gross_margin = statement_row_value(latest_income, "Gross Margin %")
    operating_margin = statement_row_value(latest_income, "Operating Margin %")
    net_margin = statement_row_value(latest_income, "Net Margin %")
    net_income = statement_row_value(latest_income, "Net Income")
    operating_margin_delta = statement_row_delta(latest_income, prev_income, "Operating Margin %")
    net_margin_delta = statement_row_delta(latest_income, prev_income, "Net Margin %")

    if revenue is None and net_income is None:
        income_tone = "neutral"
        income_headline = "Income statement data is limited"
        income_suggests = "May suggest the provider did not return enough income statement history to judge growth quality."
        income_watch = "Confirm revenue, margin, and EPS history once more periods are available."
    elif net_income is not None and net_income < 0:
        income_tone = "bad"
        income_headline = "Profitability is under pressure"
        income_suggests = "May suggest the current cost structure or demand environment is not yet supporting positive earnings."
        income_watch = "Watch operating margin, gross margin, and whether losses narrow in the next reported period."
    elif revenue_growth is not None and revenue_growth >= 0 and (operating_margin_delta is None or operating_margin_delta >= 0):
        income_tone = "good"
        income_headline = "Growth is converting into operating leverage"
        income_suggests = "May suggest the business is scaling revenue while preserving or improving profitability."
        income_watch = "Watch whether margin expansion persists after mix, pricing, or one-time benefits normalize."
    elif revenue_growth is not None and revenue_growth >= 0 and operating_margin_delta is not None and operating_margin_delta < 0:
        income_tone = "warn"
        income_headline = "Growth is coming with margin pressure"
        income_suggests = "May suggest revenue growth is being offset by cost inflation, weaker mix, or heavier investment."
        income_watch = "Watch operating expenses, gross margin, and whether incremental revenue restores earnings leverage."
    elif revenue_growth is not None and revenue_growth < 0:
        income_tone = "warn"
        income_headline = "Revenue momentum is softening"
        income_suggests = "May suggest demand, pricing, product mix, or cyclical exposure is weighing on the top line."
        income_watch = "Watch whether margins hold if revenue remains below the prior period."
    else:
        income_tone = "neutral"
        income_headline = "Profitability signal is mixed"
        income_suggests = "May suggest the latest period has usable earnings data, but not enough trend evidence for a strong call."
        income_watch = "Watch revenue growth, margin direction, and EPS consistency across additional periods."

    cash = statement_row_value(latest_balance, "Cash")
    total_debt = statement_row_value(latest_balance, "Total Debt")
    net_debt = statement_row_value(latest_balance, "Net Debt")
    current_ratio = statement_row_value(latest_balance, "Current Ratio")
    debt_to_equity = statement_row_value(latest_balance, "Debt / Equity")
    cash_to_debt = statement_row_value(latest_balance, "Cash / Debt")
    debt_delta_pct = latest_change(balance, "Total Debt")
    cash_delta_pct = latest_change(balance, "Cash")

    if cash is None and total_debt is None and debt_to_equity is None:
        balance_tone = "neutral"
        balance_headline = "Balance sheet data is limited"
        balance_suggests = "May suggest the provider did not return enough asset, liability, or liquidity detail."
        balance_watch = "Confirm cash, debt, liabilities, and equity once more complete balance sheet data is available."
    elif debt_to_equity is not None and debt_to_equity > 2:
        balance_tone = "bad"
        balance_headline = "Leverage looks elevated"
        balance_suggests = "May suggest capital structure risk is higher, especially if earnings or cash flow weaken."
        balance_watch = "Watch debt maturities, interest expense, refinancing terms, and debt-to-equity direction."
    elif cash_to_debt is not None and cash_to_debt >= 1:
        balance_tone = "good"
        balance_headline = "Liquidity covers debt"
        balance_suggests = "May suggest the company has balance sheet flexibility to fund operations, investment, or shareholder returns."
        balance_watch = "Watch whether cash balances are durable or temporarily boosted by working capital timing."
    elif net_debt is not None and net_debt > 0:
        balance_tone = "warn"
        balance_headline = "Net debt position requires monitoring"
        balance_suggests = "May suggest the company depends more on future cash generation to protect financial flexibility."
        balance_watch = "Watch cash-to-debt, debt-to-equity, and whether debt growth is outpacing equity or cash flow."
    else:
        balance_tone = "neutral"
        balance_headline = "Capital structure appears balanced"
        balance_suggests = "May suggest neither liquidity nor leverage is sending an extreme signal from the latest period."
        balance_watch = "Watch changes in cash, current ratio, total debt, and shareholders' equity."

    ocf = statement_row_value(latest_cash, "Operating Cash Flow")
    capex = statement_row_value(latest_cash, "Capital Expenditures")
    fcf = statement_row_value(latest_cash, "Free Cash Flow")
    fcf_margin = statement_row_value(latest_cash, "FCF Margin %")
    conversion = statement_row_value(latest_cash, "NI to FCF Conversion %")
    if conversion is None and fcf is not None and net_income not in (None, 0):
        conversion = safe_ratio(fcf, net_income, 100)
    fcf_change_pct = latest_change(cashflow, "Free Cash Flow")

    if ocf is None and fcf is None:
        cash_tone = "neutral"
        cash_headline = "Cash flow data is limited"
        cash_suggests = "May suggest the provider did not return enough cash flow detail to evaluate earnings quality."
        cash_watch = "Confirm operating cash flow, capex, and free cash flow when more statement detail is available."
    elif fcf is not None and fcf < 0:
        cash_tone = "bad"
        cash_headline = "Free cash flow is negative"
        cash_suggests = "May suggest reinvestment needs, working capital, or weaker operating cash flow are consuming cash."
        cash_watch = "Watch operating cash flow recovery, capex intensity, and whether financing activity funds the gap."
    elif conversion is not None and conversion >= 100:
        cash_tone = "good"
        cash_headline = "Earnings are converting strongly to cash"
        cash_suggests = "May suggest high earnings quality, favorable working capital, or disciplined reinvestment."
        cash_watch = "Watch whether conversion remains above net income without relying on one-time working capital benefits."
    elif conversion is not None and conversion < 50:
        cash_tone = "warn"
        cash_headline = "Cash conversion is light"
        cash_suggests = "May suggest reported earnings are not fully translating into free cash flow in the latest period."
        cash_watch = "Watch receivables, inventory, capex, and non-cash earnings adjustments."
    elif fcf is not None and fcf > 0:
        cash_tone = "good"
        cash_headline = "Free cash flow is positive"
        cash_suggests = "May suggest the company is generating cash after reinvestment needs."
        cash_watch = "Watch whether free cash flow grows with revenue and remains resilient through investment cycles."
    else:
        cash_tone = "neutral"
        cash_headline = "Cash generation signal is mixed"
        cash_suggests = "May suggest cash flow is directionally usable, but not enough trend evidence is available for a stronger read."
        cash_watch = "Watch operating cash flow, capex, free cash flow, and financing cash flow over additional periods."

    return [
        {
            "statement": "Income Statement",
            "tone": income_tone,
            "headline": income_headline,
            "status": "Profitability",
            "metrics": [
                ("Revenue", format_compact_currency(revenue, 2)),
                ("Revenue growth", format_percent(revenue_growth, 1, signed=True)),
                ("Gross margin", format_percent(gross_margin, 1)),
                ("Operating margin", format_percent(operating_margin, 1)),
                ("Net margin", format_percent(net_margin, 1)),
                ("Net income", format_compact_currency(net_income, 2)),
            ],
            "suggests": income_suggests,
            "watch": income_watch,
        },
        {
            "statement": "Balance Sheet",
            "tone": balance_tone,
            "headline": balance_headline,
            "status": "Liquidity & Leverage",
            "metrics": [
                ("Cash", format_compact_currency(cash, 2)),
                ("Total debt", format_compact_currency(total_debt, 2)),
                ("Net debt", format_compact_currency(net_debt, 2)),
                ("Current ratio", format_number(current_ratio, 2)),
                ("Debt / equity", format_number(debt_to_equity, 2)),
                ("Cash / debt", format_number(cash_to_debt, 2)),
                ("Debt change", format_percent(debt_delta_pct, 1, signed=True)),
                ("Cash change", format_percent(cash_delta_pct, 1, signed=True)),
            ],
            "suggests": balance_suggests,
            "watch": balance_watch,
        },
        {
            "statement": "Cash Flow",
            "tone": cash_tone,
            "headline": cash_headline,
            "status": "Cash Quality",
            "metrics": [
                ("Operating CF", format_compact_currency(ocf, 2)),
                ("Capex", format_compact_currency(capex, 2)),
                ("Free CF", format_compact_currency(fcf, 2)),
                ("FCF margin", format_percent(fcf_margin, 1)),
                ("FCF / NI", format_percent(conversion, 1)),
                ("FCF change", format_percent(fcf_change_pct, 1, signed=True)),
            ],
            "suggests": cash_suggests,
            "watch": cash_watch,
        },
    ]


def render_structured_statement_insight_tiles(tiles: list[dict[str, object]]) -> None:
    tile_html: list[str] = []
    for tile in tiles:
        tone = html.escape(str(tile.get("tone", "neutral")))
        statement = html.escape(str(tile.get("statement", "Statement")))
        headline = html.escape(str(tile.get("headline", "Signal unavailable")))
        status = html.escape(str(tile.get("status", "Signal")))
        suggests = html.escape(str(tile.get("suggests", "Not enough data to infer a signal.")))
        watch = html.escape(str(tile.get("watch", "Review additional periods as data becomes available.")))
        metrics = tile.get("metrics", [])
        metric_html = ""
        if isinstance(metrics, list):
            for metric in metrics[:8]:
                if not isinstance(metric, tuple) or len(metric) != 2:
                    continue
                label, value = metric
                metric_html += (
                    "<div class='statement-insight-metric'>"
                    f"<span>{html.escape(str(label))}</span>"
                    f"<strong>{html.escape(str(value))}</strong>"
                    "</div>"
                )
        tile_html.append(
            f"<article class='statement-insight-tile {tone}'>"
            "<div class='statement-insight-top'>"
            "<div>"
            f"<span class='statement-insight-label'>{statement}</span>"
            f"<span class='statement-insight-headline'>{headline}</span>"
            "</div>"
            f"<span class='statement-insight-status'>{status}</span>"
            "</div>"
            f"<div class='statement-insight-metrics'>{metric_html}</div>"
            f"<p class='statement-insight-copy'><strong>What it may suggest</strong><br>{suggests}</p>"
            f"<p class='statement-insight-copy'><strong>What to watch</strong><br>{watch}</p>"
            "</article>"
        )
    st.markdown("<div class='statement-insight-grid'>" + "".join(tile_html) + "</div>", unsafe_allow_html=True)


def render_insight_cards(insights: list[dict[str, str]]) -> None:
    cards = [
        f"<div class='insight-card {html.escape(str(item.get('tone', 'neutral')))}'>{html.escape(str(item.get('text', '')))}</div>"
        for item in insights
    ]
    st.markdown("<div class='insight-list'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_statement_section_title(title: str, subtitle: str, *, animate: bool, delay: int) -> None:
    klass = f"statement-section statement-delay-{delay}" if animate else ""
    st.markdown(
        f"<div class='{klass}'>"
        f"<div class='section-title'><div><span class='section-title-main'>{html.escape(title)}</span>"
        f"<span class='section-title-sub'>{html.escape(subtitle)}</span></div></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def income_waterfall_steps(row: pd.Series) -> list[dict[str, object]]:
    revenue = coerce_float(row.get("Revenue"))
    cost = coerce_float(row.get("Cost of Revenue"))
    gross = coerce_float(row.get("Gross Profit"))
    opex = coerce_float(row.get("Operating Expenses"))
    operating_income = coerce_float(row.get("Operating Income"))
    pretax = coerce_float(row.get("Pretax Income"))
    taxes = coerce_float(row.get("Taxes"))
    net_income = coerce_float(row.get("Net Income"))
    interest_other = None
    if pretax is not None and operating_income is not None:
        interest_other = pretax - operating_income
    return [
        {"label": "Revenue", "value": revenue, "measure": "absolute"},
        {"label": "Cost of Revenue", "value": -abs(cost) if cost is not None else None, "measure": "relative"},
        {"label": "Gross Profit", "value": gross, "measure": "total"},
        {"label": "Operating Expenses", "value": -abs(opex) if opex is not None else None, "measure": "relative"},
        {"label": "Operating Income", "value": operating_income, "measure": "total"},
        {"label": "Interest / Other", "value": interest_other, "measure": "relative"},
        {"label": "Taxes", "value": -abs(taxes) if taxes is not None else None, "measure": "relative"},
        {"label": "Net Income", "value": net_income, "measure": "total"},
    ]


def cash_flow_waterfall_steps(row: pd.Series) -> list[dict[str, object]]:
    net_income = coerce_float(row.get("Net Income"))
    da = coerce_float(row.get("D&A"))
    wc = coerce_float(row.get("Change in Working Capital"))
    ocf = coerce_float(row.get("Operating Cash Flow"))
    capex = coerce_float(row.get("Capital Expenditures"))
    fcf = coerce_float(row.get("Free Cash Flow"))
    investing = coerce_float(row.get("Investing Cash Flow"))
    financing = coerce_float(row.get("Financing Cash Flow"))
    net_change = coerce_float(row.get("Net Change in Cash"))
    return [
        {"label": "Net Income", "value": net_income, "measure": "absolute"},
        {"label": "D&A", "value": da, "measure": "relative"},
        {"label": "Working Capital", "value": wc, "measure": "relative"},
        {"label": "Operating CF", "value": ocf, "measure": "total"},
        {"label": "Capex", "value": capex, "measure": "relative"},
        {"label": "Free CF", "value": fcf, "measure": "total"},
        {"label": "Investing CF", "value": investing, "measure": "relative"},
        {"label": "Financing CF", "value": financing, "measure": "relative"},
        {"label": "Net Change Cash", "value": net_change, "measure": "total"},
    ]


def render_income_statement_analysis(
    ticker: str,
    income: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    animate: bool,
    show_raw: bool,
    show_common_size: bool,
    show_change: bool,
    key_suffix: str,
    meta_caption: str,
) -> dict[str, object]:
    with st.container(border=True):
        render_statement_section_title("Income Statement Analysis", "Revenue growth, profitability, and margin structure.", animate=animate, delay=1)
        st.caption(meta_caption)
        if income.empty:
            st.info("Income statement data is unavailable for this ticker.")
            return {"charts": 0, "available_fields": [], "missing_fields": list(INCOME_SANKEY_FIELDS)}
        income = add_change_columns(income, ["Revenue", "Gross Profit", "Operating Income", "Net Income"])
        latest = latest_row(income)
        revenue = coerce_float(latest.get("Revenue"))
        cards = [
            {"label": "Revenue", "value": format_compact_currency(revenue, 2), "context": format_percent(latest_change(income, "Revenue"), 1, signed=True), "tone": quote_tone(latest_change(income, "Revenue"))},
            {"label": "Gross Profit", "value": format_compact_currency(latest.get("Gross Profit"), 2), "context": format_percent(latest.get("Gross Margin %"), 1)},
            {"label": "Operating Income", "value": format_compact_currency(latest.get("Operating Income"), 2), "context": format_percent(latest.get("Operating Margin %"), 1), "tone": quote_tone(latest.get("Operating Income"))},
            {"label": "Net Income", "value": format_compact_currency(latest.get("Net Income"), 2), "context": format_percent(latest.get("Net Margin %"), 1), "tone": quote_tone(latest.get("Net Income"))},
            {"label": "EPS", "value": format_number(latest.get("EPS"), 2), "context": "diluted if available"},
        ]
        render_metric_strip(cards, columns=5)
        chart_cols = st.columns([1.05, 0.95], gap="small")
        chart_count = 0
        with chart_cols[0]:
            render_section_title("Revenue to Net Income Waterfall", f"Latest period: {latest.get('Period', 'N/A')}")
            chart_count += int(render_waterfall_chart("Revenue to Net Income", income_waterfall_steps(latest), key=f"income_waterfall_{key_suffix}"))
        with chart_cols[1]:
            render_section_title("Margin Trend", "Gross, operating, and net margin")
            chart_count += int(render_line_chart(income, ["Gross Margin %", "Operating Margin %", "Net Margin %"], "Margin Trend", "Margin (%)", key=f"income_margin_{key_suffix}", height=295))
        if show_common_size:
            render_section_title("Common-Size Income Statement", "Line items as a percentage of revenue")
            chart_count += int(render_common_size_chart(income, ["Cost of Revenue", "Gross Profit", "Operating Expenses", "Operating Income", "Net Income"], "Revenue", "Common-size income statement", key=f"income_common_{key_suffix}"))
        if show_raw:
            with st.expander("Normalized Income Statement Data", expanded=False):
                render_dashboard_table(format_normalized_history_display(raw, show_change), height=360)
        available, missing = sankey_fields_debug(normalize_sankey_statement(pd.DataFrame(), {}, None, None, "")) if False else (
            [col for col in INCOME_SANKEY_FIELDS if col in income and income[col].notna().any()],
            [col for col in INCOME_SANKEY_FIELDS if col not in income or not income[col].notna().any()],
        )
        return {"charts": chart_count, "available_fields": available, "missing_fields": missing}


def render_balance_sheet_analysis(
    ticker: str,
    balance: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    animate: bool,
    show_raw: bool,
    show_common_size: bool,
    show_change: bool,
    key_suffix: str,
    meta_caption: str,
) -> dict[str, object]:
    with st.container(border=True):
        render_statement_section_title("Balance Sheet Analysis", "Financial position, liquidity, leverage, and capital structure.", animate=animate, delay=2)
        st.caption(meta_caption)
        if balance.empty:
            st.info("Balance sheet data is unavailable for this ticker.")
            return {"charts": 0, "available_fields": [], "missing_fields": list(BALANCE_SANKEY_FIELDS)}
        latest = latest_row(balance)
        cards = [
            {"label": "Total Assets", "value": format_compact_currency(latest.get("Total Assets"), 2), "context": "asset base"},
            {"label": "Cash", "value": format_compact_currency(latest.get("Cash"), 2), "context": "liquidity"},
            {"label": "Liabilities", "value": format_compact_currency(latest.get("Total Liabilities"), 2), "context": "claims"},
            {"label": "Total Debt", "value": format_compact_currency(latest.get("Total Debt"), 2), "context": format_number(latest.get("Debt / Equity"), 2) + " debt/equity"},
            {"label": "Equity", "value": format_compact_currency(latest.get("Shareholders' Equity"), 2), "context": "book value"},
            {"label": "Net Debt", "value": format_compact_currency(latest.get("Net Debt"), 2), "context": "debt less cash", "tone": "bad" if (coerce_float(latest.get("Net Debt")) or 0) > 0 else "good"},
        ]
        render_metric_strip(cards, columns=6)
        top_cols = st.columns([1, 1], gap="small")
        chart_count = 0
        with top_cols[0]:
            render_section_title("Balance Sheet Composition", "Assets versus liabilities and equity")
            chart_count += int(render_balance_composition_chart(balance, key=f"balance_comp_{key_suffix}"))
        with top_cols[1]:
            render_section_title("Asset Composition", "Cash, receivables, inventory, PP&E, intangibles, and other assets")
            chart_count += int(render_bar_chart(balance, ["Cash", "Accounts Receivable", "Inventory", "PP&E", "Goodwill / Intangibles", "Other Assets"], "Asset Composition", "Amount ($B)", key=f"asset_comp_{key_suffix}", value_scale=1_000_000_000, stacked=True, height=270))
        lower_cols = st.columns([1, 1], gap="small")
        with lower_cols[0]:
            render_section_title("Cash, Debt, and Net Debt", "Liquidity and leverage in dollars")
            chart_count += int(render_line_chart(balance, ["Cash", "Total Debt", "Net Debt"], "Cash and debt trend", "Amount ($B)", key=f"debt_cash_{key_suffix}", value_scale=1_000_000_000, height=235))
        with lower_cols[1]:
            render_section_title("Leverage & Liquidity Ratios", "Current ratio, debt/equity, and cash/debt")
            chart_count += int(render_line_chart(balance, ["Current Ratio", "Debt / Equity", "Cash / Debt"], "Liquidity ratios", "Ratio", key=f"balance_ratios_{key_suffix}", height=235))
        if show_common_size:
            render_section_title("Common-Size Balance Sheet", "Line items as a percentage of total assets")
            chart_count += int(render_common_size_chart(balance, ["Cash", "Accounts Receivable", "Inventory", "PP&E", "Goodwill / Intangibles", "Total Liabilities", "Shareholders' Equity"], "Total Assets", "Common-size balance sheet", key=f"balance_common_{key_suffix}"))
        if show_raw:
            with st.expander("Normalized Balance Sheet Data", expanded=False):
                render_dashboard_table(format_normalized_history_display(raw, show_change), height=360)
        available = [col for col in BALANCE_SANKEY_FIELDS if col in balance and balance[col].notna().any()]
        missing = [col for col in BALANCE_SANKEY_FIELDS if col not in balance or not balance[col].notna().any()]
        return {"charts": chart_count, "available_fields": available, "missing_fields": missing}


def render_cash_flow_analysis(
    ticker: str,
    cashflow: pd.DataFrame,
    income: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    animate: bool,
    show_raw: bool,
    show_change: bool,
    key_suffix: str,
    meta_caption: str,
) -> dict[str, object]:
    with st.container(border=True):
        render_statement_section_title("Cash Flow Analysis", "Cash generation, reinvestment, financing activity, and free cash flow quality.", animate=animate, delay=3)
        st.caption(meta_caption)
        if cashflow.empty:
            st.info("Cash flow statement data is unavailable for this ticker.")
            return {"charts": 0, "available_fields": [], "missing_fields": list(CASH_FLOW_SANKEY_FIELDS)}
        merged = cashflow.copy()
        if not income.empty:
            income_subset = income[["Period Date", "Net Income", "Revenue"]].copy() if {"Period Date", "Net Income", "Revenue"}.issubset(income.columns) else pd.DataFrame()
            if not income_subset.empty:
                merged = merged.merge(income_subset, on="Period Date", how="left", suffixes=("", " Income"))
                if "Net Income Income" in merged:
                    merged["Net Income"] = merged["Net Income"].combine_first(merged["Net Income Income"])
        if "Revenue" in merged:
            merged["FCF Margin %"] = merged.apply(lambda row: safe_ratio(row.get("Free Cash Flow"), row.get("Revenue"), 100), axis=1)
        if "Net Income" in merged:
            merged["NI to FCF Conversion %"] = merged.apply(lambda row: safe_ratio(row.get("Free Cash Flow"), row.get("Net Income"), 100), axis=1)
        latest = latest_row(merged)
        cards = [
            {"label": "Operating CF", "value": format_compact_currency(latest.get("Operating Cash Flow"), 2), "context": "operations", "tone": quote_tone(latest.get("Operating Cash Flow"))},
            {"label": "Capex", "value": format_compact_currency(latest.get("Capital Expenditures"), 2), "context": "reinvestment", "tone": "bad" if coerce_float(latest.get("Capital Expenditures")) is not None else "neutral"},
            {"label": "Free CF", "value": format_compact_currency(latest.get("Free Cash Flow"), 2), "context": format_percent(latest.get("FCF Margin %"), 1), "tone": quote_tone(latest.get("Free Cash Flow"))},
            {"label": "FCF / NI", "value": format_percent(latest.get("NI to FCF Conversion %"), 1), "context": "cash conversion"},
            {"label": "Investing CF", "value": format_compact_currency(latest.get("Investing Cash Flow"), 2), "context": "investing", "tone": quote_tone(latest.get("Investing Cash Flow"))},
            {"label": "Financing CF", "value": format_compact_currency(latest.get("Financing Cash Flow"), 2), "context": "financing", "tone": quote_tone(latest.get("Financing Cash Flow"))},
        ]
        render_metric_strip(cards, columns=6)
        chart_cols = st.columns([1.05, 0.95], gap="small")
        chart_count = 0
        with chart_cols[0]:
            render_section_title("Cash Flow Bridge", f"Latest period: {latest.get('Period', 'N/A')}")
            chart_count += int(render_waterfall_chart("Cash flow bridge", cash_flow_waterfall_steps(latest), key=f"cash_waterfall_{key_suffix}"))
        with chart_cols[1]:
            render_section_title("Free Cash Flow Trend", "Operating cash flow, capex, and FCF")
            chart_count += int(render_bar_chart(merged, ["Operating Cash Flow", "Capital Expenditures", "Free Cash Flow"], "FCF Trend", "Amount ($B)", key=f"fcf_trend_{key_suffix}", value_scale=1_000_000_000, height=295))
        render_section_title("Cash Conversion", "Net income versus operating cash flow and free cash flow")
        chart_count += int(render_bar_chart(merged, ["Net Income", "Operating Cash Flow", "Free Cash Flow"], "Cash conversion", "Amount ($B)", key=f"cash_conversion_{key_suffix}", value_scale=1_000_000_000, height=250))
        if show_raw:
            with st.expander("Normalized Cash Flow Data", expanded=False):
                render_dashboard_table(format_normalized_history_display(raw, show_change), height=360)
        available = [col for col in CASH_FLOW_SANKEY_FIELDS if col in cashflow and cashflow[col].notna().any()]
        missing = [col for col in CASH_FLOW_SANKEY_FIELDS if col not in cashflow or not cashflow[col].notna().any()]
        return {"charts": chart_count, "available_fields": available, "missing_fields": missing, "merged": merged}


def render_three_statement_insights(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
    *,
    animate: bool,
    meta_caption: str,
) -> list[dict[str, str]]:
    with st.container(border=True):
        render_statement_section_title("3-Statement Insights", "Rule-based dashboard signals generated from the selected financial statements.", animate=animate, delay=4)
        st.caption(meta_caption + " | Signals are dashboard context, not investment advice.")
        tiles = structured_statement_insight_tiles(income, balance, cashflow)
        render_structured_statement_insight_tiles(tiles)
        render_section_title("Supporting Signals", "Additional deterministic checks from the normalized statement history")
        insights = generate_three_statement_insights(income, balance, cashflow)
        render_insight_cards(insights)
        return insights


def render_three_statement_analysis_dashboard() -> None:
    st.sidebar.header("3-Statement Analysis")
    show_debug = st.sidebar.checkbox("Show 3-statement debug", value=False, key="three_statement_debug")

    st.title("3-Statement Analysis")
    st.markdown(
        "<div class='statement-page-subtitle'>Analyze profitability, balance sheet strength, cash generation, and financial trend quality across the income statement, balance sheet, and cash flow statement.</div>",
        unsafe_allow_html=True,
    )

    if "three_statement_ticker_input" not in st.session_state:
        st.session_state["three_statement_ticker_input"] = st.session_state.get("sankey_ticker", "")
    control_cols = st.columns([1.0, 0.72, 0.64, 0.58, 0.72, 0.72, 0.72], gap="small")
    with control_cols[0]:
        ticker_input = st.text_input("Ticker", placeholder="Enter ticker", key="three_statement_ticker_input")
    ticker = normalize_symbol(ticker_input)
    with control_cols[1]:
        statement_period = st.selectbox("Statement period", ["Annual", "Quarterly"], index=0, key="three_statement_period")
    with control_cols[2]:
        periods_to_show = int(st.selectbox("Periods", [4, 8, 12, 16], index=1, key="three_statement_periods"))
    with control_cols[3]:
        refresh_clicked = st.button("Refresh", use_container_width=True, key="three_statement_refresh")
    with control_cols[4]:
        show_raw = st.toggle("Raw data", value=False, key="three_statement_show_raw")
    with control_cols[5]:
        show_common_size = st.toggle("Common-size", value=False, key="three_statement_common_size")
    with control_cols[6]:
        animate_charts = st.toggle("Animate charts", value=True, key="three_statement_animate")
    show_change = st.toggle("Show YoY / QoQ change", value=True, key="three_statement_show_change")

    if refresh_clicked:
        fetch_company_financials.clear()
        st.session_state["three_statement_last_manual_refresh"] = eastern_now()

    if not ticker:
        st.markdown(
            "<div class='sankey-empty'>Enter a ticker to generate 3-statement financial analysis.</div>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner(f"Fetching financial statements for {ticker}..."):
        payload = fetch_company_financials(ticker, statement_period, periods_to_show, date.today().year)
    if payload.get("status") != "OK":
        st.error(payload.get("message", "Unable to fetch financial statement data."))
        return

    income_statement, balance_statement, cash_statement, quarterly = company_statement_set(payload, statement_period)
    all_periods = statement_period_options([income_statement, balance_statement, cash_statement])
    if not all_periods:
        st.warning("No financial statement periods were returned for this ticker.")
        return
    selected_periods = sorted(all_periods)[-periods_to_show:]
    if len(selected_periods) < periods_to_show:
        st.caption(
            f"Showing {len(selected_periods)} available {statement_period.lower()} periods. "
            "Additional historical periods were not returned by the data source."
        )

    income_frame, income_raw = normalize_statement_history(income_statement, INCOME_SANKEY_FIELDS, selected_periods, quarterly, "Revenue")
    balance_frame, balance_raw = normalize_statement_history(balance_statement, BALANCE_SANKEY_FIELDS, selected_periods, quarterly, "Total Assets")
    cash_frame, cash_raw = normalize_statement_history(cash_statement, CASH_FLOW_SANKEY_FIELDS, selected_periods, quarterly, "Operating Cash Flow")

    refreshed_at = payload.get("financials_refreshed") or eastern_now()
    financial_meta = provider_metadata(
        "Yahoo Finance/yfinance",
        "Financial Statements",
        "Cached / delayed",
        last_updated=refreshed_at if isinstance(refreshed_at, datetime) else eastern_now(),
        is_delayed=True,
        is_cached=True,
        delay_disclaimer="Financial statements are filing/provider data and are not real-time.",
        source_label="Yahoo Finance/yfinance",
    )
    meta_caption = (
        f"{ticker} | {statement_period} | {len(selected_periods)} periods | "
        + freshness_caption(financial_meta, "Yahoo Finance/yfinance")
    )
    signature = f"{ticker}|{statement_period}|{periods_to_show}|{selected_periods[-1].date() if selected_periods else 'na'}"
    animation_triggered = st.session_state.get("three_statement_last_signature") != signature
    st.session_state["three_statement_last_signature"] = signature
    section_animate = bool(animate_charts and animation_triggered)
    key_suffix = safe_ui_key(signature)

    income_debug = render_income_statement_analysis(
        ticker,
        income_frame,
        income_raw,
        animate=section_animate,
        show_raw=show_raw,
        show_common_size=show_common_size,
        show_change=show_change,
        key_suffix=key_suffix,
        meta_caption=meta_caption,
    )
    balance_debug = render_balance_sheet_analysis(
        ticker,
        balance_frame,
        balance_raw,
        animate=section_animate,
        show_raw=show_raw,
        show_common_size=show_common_size,
        show_change=show_change,
        key_suffix=key_suffix,
        meta_caption=meta_caption,
    )
    cash_debug = render_cash_flow_analysis(
        ticker,
        cash_frame,
        income_frame,
        cash_raw,
        animate=section_animate,
        show_raw=show_raw,
        show_change=show_change,
        key_suffix=key_suffix,
        meta_caption=meta_caption,
    )
    cash_for_insights = cash_debug.get("merged") if isinstance(cash_debug.get("merged"), pd.DataFrame) else cash_frame
    insights = render_three_statement_insights(
        income_frame,
        balance_frame,
        cash_for_insights,
        animate=section_animate,
        meta_caption=meta_caption,
    )

    if show_debug:
        with st.expander("3-statement debug", expanded=False):
            debug_rows = [
                {"Metric": "Selected ticker", "Value": ticker},
                {"Metric": "Statement period", "Value": statement_period},
                {"Metric": "Periods requested", "Value": periods_to_show},
                {"Metric": "Periods displayed", "Value": len(selected_periods)},
                {"Metric": "Provider used", "Value": "Yahoo Finance/yfinance"},
                {"Metric": "Cache TTL", "Value": "6 hours"},
                {"Metric": "Animation triggered", "Value": str(section_animate)},
                {"Metric": "Income charts generated", "Value": income_debug.get("charts", 0)},
                {"Metric": "Balance charts generated", "Value": balance_debug.get("charts", 0)},
                {"Metric": "Cash flow charts generated", "Value": cash_debug.get("charts", 0)},
                {"Metric": "Insights generated", "Value": len(insights)},
                {"Metric": "Income fields available", "Value": ", ".join(income_debug.get("available_fields", [])) or "None"},
                {"Metric": "Income fields missing", "Value": ", ".join(income_debug.get("missing_fields", [])) or "None"},
                {"Metric": "Balance fields available", "Value": ", ".join(balance_debug.get("available_fields", [])) or "None"},
                {"Metric": "Balance fields missing", "Value": ", ".join(balance_debug.get("missing_fields", [])) or "None"},
                {"Metric": "Cash flow fields available", "Value": ", ".join(cash_debug.get("available_fields", [])) or "None"},
                {"Metric": "Cash flow fields missing", "Value": ", ".join(cash_debug.get("missing_fields", [])) or "None"},
            ]
            render_dashboard_table(pd.DataFrame(debug_rows), height=460)


def render_sankey_flow_dashboard() -> None:
    st.sidebar.header("Sankey Flow Chart")
    show_debug = st.sidebar.checkbox("Show Sankey debug", value=False, key="sankey_debug")

    st.title("Sankey Flow Chart")
    st.markdown(
        "<div class='sankey-page-subtitle'>Financial statement flow charts for income statement, balance sheet, and cash flow statement data.</div>",
        unsafe_allow_html=True,
    )

    if "sankey_ticker_input" not in st.session_state:
        st.session_state["sankey_ticker_input"] = st.session_state.get("sankey_ticker", "")
    control_cols = st.columns([1.05, 0.78, 0.62, 0.72, 0.88], gap="small")
    with control_cols[0]:
        ticker_input = st.text_input("Ticker", placeholder="Enter ticker", key="sankey_ticker_input")
    ticker = normalize_symbol(ticker_input)
    st.session_state["sankey_ticker"] = ticker
    with control_cols[1]:
        statement_period = st.selectbox("Statement period", ["Annual", "Quarterly"], index=0, key="sankey_statement_period")
    with control_cols[2]:
        refresh_clicked = st.button("Refresh", use_container_width=True, key="sankey_refresh")
    with control_cols[3]:
        animate_chart = st.toggle("Animate chart", value=True, key="sankey_animate")
    with control_cols[4]:
        show_normalized = st.toggle("Show normalized data", value=False, key="sankey_show_normalized")

    if refresh_clicked:
        fetch_company_financials.clear()
        st.session_state["sankey_last_manual_refresh"] = eastern_now()

    if not ticker:
        st.markdown(
            "<div class='sankey-empty'>Enter a ticker to generate Sankey flow charts for the income statement, balance sheet, and cash flow statement.</div>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner(f"Fetching financial statement data for {ticker}..."):
        payload = fetch_company_financials(ticker, statement_period, 8, date.today().year)

    if payload.get("status") != "OK":
        st.error(payload.get("message", "Unable to fetch financial statement data."))
        return

    income, balance, cashflow, quarterly = company_statement_set(payload, statement_period)
    periods = statement_period_options([income, balance, cashflow])
    if not periods:
        st.warning("No financial statement periods were returned for this ticker.")
        return

    period_col, source_col = st.columns([0.7, 1.3], gap="small")
    with period_col:
        selected_period = st.selectbox(
            "Fiscal period",
            periods,
            index=0,
            format_func=lambda value: period_label(value, quarterly),
            key=f"sankey_fiscal_period_{safe_ui_key(ticker)}_{safe_ui_key(statement_period)}",
        )
    refreshed_at = payload.get("financials_refreshed") or eastern_now()
    financial_meta = provider_metadata(
        "Yahoo Finance/yfinance",
        "Financial Statements",
        "Cached / delayed",
        last_updated=refreshed_at if isinstance(refreshed_at, datetime) else eastern_now(),
        is_delayed=True,
        is_cached=True,
        delay_disclaimer="Financial statements are filing/provider data and are not real-time.",
        source_label="Yahoo Finance/yfinance",
    )
    with source_col:
        st.caption(
            f"Fiscal period shown: {period_label(selected_period, quarterly)} | Statement period: {statement_period} | "
            + freshness_caption(financial_meta, "Yahoo Finance/yfinance")
        )

    signature = f"{ticker}|{statement_period}|{pd.Timestamp(selected_period).date()}"
    animation_triggered = st.session_state.get("sankey_last_signature") != signature
    st.session_state["sankey_last_signature"] = signature
    chart_key_suffix = safe_ui_key(signature)
    previous_period = previous_sankey_period(periods, selected_period)
    updated_short = (
        refreshed_at.strftime("%I:%M %p ET").lstrip("0")
        if isinstance(refreshed_at, datetime)
        else eastern_now().strftime("%I:%M %p ET").lstrip("0")
    )
    meta_text = f"Yahoo Finance/yfinance | {statement_period} | {period_label(selected_period, quarterly)} | Updated {updated_short}"
    tile_animate = bool(animate_chart and animation_triggered)

    debug_payload = {
        "income": render_income_sankey_tile(
            ticker,
            income,
            selected_period,
            previous_period,
            period_label(selected_period, quarterly),
            meta_text,
            chart_key_suffix=chart_key_suffix,
            animate=tile_animate,
            show_normalized=show_normalized,
        ),
        "balance": render_balance_sankey_tile(
            ticker,
            balance,
            selected_period,
            previous_period,
            period_label(selected_period, quarterly),
            meta_text,
            chart_key_suffix=chart_key_suffix,
            animate=tile_animate,
            show_normalized=show_normalized,
        ),
        "cash_flow": render_cash_flow_sankey_tile(
            ticker,
            cashflow,
            selected_period,
            previous_period,
            period_label(selected_period, quarterly),
            meta_text,
            chart_key_suffix=chart_key_suffix,
            animate=tile_animate,
            show_normalized=show_normalized,
        ),
    }

    if show_debug:
        with st.expander("Sankey debug", expanded=False):
            debug_rows = [
                {"Metric": "Selected ticker", "Value": ticker},
                {"Metric": "Statement period", "Value": statement_period},
                {"Metric": "Fiscal period", "Value": period_label(selected_period, quarterly)},
                {"Metric": "Previous period for YoY", "Value": period_label(previous_period, quarterly) if previous_period is not None else "N/A"},
                {"Metric": "Provider used", "Value": "Yahoo Finance/yfinance"},
                {"Metric": "Cache TTL", "Value": "6 hours"},
                {"Metric": "Animation triggered", "Value": str(tile_animate)},
                {"Metric": "Chart key suffix", "Value": chart_key_suffix},
                {"Metric": "Income fields available", "Value": ", ".join(debug_payload["income"].get("available_fields", [])) or "None"},
                {"Metric": "Income fields missing", "Value": ", ".join(debug_payload["income"].get("missing_fields", [])) or "None"},
                {"Metric": "Balance fields available", "Value": ", ".join(debug_payload["balance"].get("available_fields", [])) or "None"},
                {"Metric": "Balance fields missing", "Value": ", ".join(debug_payload["balance"].get("missing_fields", [])) or "None"},
                {"Metric": "Cash flow fields available", "Value": ", ".join(debug_payload["cash_flow"].get("available_fields", [])) or "None"},
                {"Metric": "Cash flow fields missing", "Value": ", ".join(debug_payload["cash_flow"].get("missing_fields", [])) or "None"},
                {"Metric": "Negative values detected", "Value": "; ".join(sorted({note for payload_part in debug_payload.values() for note in payload_part.get("negative_notes", [])})) or "None"},
                {"Metric": "Income links", "Value": str(len(debug_payload["income"].get("links", [])))},
                {"Metric": "Balance links", "Value": str(len(debug_payload["balance"].get("links", [])))},
                {"Metric": "Cash flow links", "Value": str(len(debug_payload["cash_flow"].get("links", [])))},
            ]
            render_dashboard_table(pd.DataFrame(debug_rows), height=420)


def available_forecast_display_columns(
    show_30d_benchmark: bool,
    realized_windows: list[str],
    show_backtest: bool,
) -> list[str]:
    excluded = set(PINNED_FORECAST_COLUMNS)
    if not show_30d_benchmark:
        excluded.update(BENCHMARK_30D_COLUMNS)
    enabled_history_columns = {
        HISTORICAL_WINDOW_COLUMNS[window]
        for window in realized_windows
        if window in HISTORICAL_WINDOW_COLUMNS
    }
    excluded.update(
        column
        for column in HISTORICAL_WINDOW_COLUMNS.values()
        if column not in enabled_history_columns
    )
    if not show_backtest:
        excluded.update(BACKTEST_COLUMNS)
    return [column for column in FORECAST_COLUMNS if column not in excluded]


def default_feed_text() -> str:
    return "\n".join(f"{name} | {url}" for name, url in DEFAULT_FEEDS)


def forecast_column_config() -> dict:
    move_columns = [
        "Projected Move %",
        "Options Move %",
        "30D Options Move %",
        "20D Hist Move %",
        "60D Hist Move %",
        "90D Hist Move %",
        "252D Hist Move %",
        "Backtest Move %",
    ]
    config = {
        "Last Price": st.column_config.NumberColumn(format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn(format="$%.0f"),
        "Avg Dollar Volume": st.column_config.NumberColumn(format="$%.0f"),
        "Options IV %": st.column_config.NumberColumn(format="%.2f%%"),
        "30D Options IV %": st.column_config.NumberColumn(format="%.2f%%"),
        "Volatility Score": st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100),
        "Confidence": st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100),
        "Base Move %": st.column_config.NumberColumn(format="%.2f%%"),
        "Earnings Risk": st.column_config.NumberColumn(format="%.2f"),
        "Macro Risk": st.column_config.NumberColumn(format="%.2f"),
        "News Risk": st.column_config.NumberColumn(format="%.2f"),
        "Social Risk": st.column_config.NumberColumn(format="%.2f"),
        "Social Mentions": st.column_config.NumberColumn(format="%d"),
        "Social Engagement": st.column_config.NumberColumn(format="%d"),
        "Social Sentiment": st.column_config.NumberColumn(format="%.2f"),
        "Volume Risk": st.column_config.NumberColumn(format="%.2f"),
        "Analyst Dispersion": st.column_config.NumberColumn(format="%.2f"),
        "Beta": st.column_config.NumberColumn(format="%.2f"),
        "Volume Shock": st.column_config.NumberColumn(format="%.2fx"),
        "ATR Move %": st.column_config.NumberColumn(format="%.2f%%"),
        "Ann. Realized Vol %": st.column_config.NumberColumn(format="%.1f%%"),
        "Backtest Error %": st.column_config.NumberColumn(format="%+.2f%%"),
    }
    for column in move_columns:
        config[column] = st.column_config.NumberColumn(format="+/-%.2f%%")
    return config

def render_volatility_radar() -> None:
    st.sidebar.header("Volatility Radar")
    include_etfs = st.sidebar.checkbox("Include ETFs and funds", value=False)
    refresh_requested = st.sidebar.button("Refresh live data", use_container_width=True)
    if refresh_requested:
        fetch_feeds.clear()
        fetch_market_macro_headlines.clear()
        fetch_social_mentions.clear()
        fetch_market_payloads.clear()
        fetch_benchmark_history.clear()
        fetch_us_listed_symbols.clear()
        fetch_index_memberships.clear()
        load_symbol_universe.clear()
        fetch_scheduled_macro_events.clear()

    universe_df, universe_status_df = load_symbol_universe(include_etfs)
    universe_preset = st.sidebar.selectbox("Universe preset", UNIVERSE_PRESETS, index=0)

    available_exchanges = sorted(universe_df["Exchange"].dropna().unique().tolist()) if not universe_df.empty else []
    exchange_filters = st.sidebar.multiselect(
        "Exchange filter",
        available_exchanges,
        default=[],
        disabled=universe_preset in {"Custom list"},
    )
    index_options = list(INDEX_SOURCES)
    index_filters = st.sidebar.multiselect(
        "Index filter",
        index_options,
        default=[],
        disabled=universe_preset in {"Custom list"},
    )
    symbol_query = st.sidebar.text_input("Symbol or company search")
    custom_input = st.sidebar.text_area(
        "Custom or add-on tickers",
        DEFAULT_UNIVERSE if universe_preset == "Custom list" else "",
        height=68,
    )
    custom_tickers = parse_watchlist(custom_input)
    scan_strategy = st.sidebar.selectbox(
        "Scan selection",
        ["Broad universe sample", "Random sample", "Ticker A-Z"],
        index=0,
        key="volatility_scan_strategy_v2",
        help=(
            "Broad universe sample spreads the scan across the selected universe before "
            "ranking results by volatility. Ticker A-Z is available only when you explicitly "
            "want the first alphabetical symbols."
        ),
    )
    sort_mode = st.sidebar.selectbox(
        "Sort forecasts by",
        ["Option Move %", "IV Rank / IV Percentile", "ATR %", "Volume Spike", "Social Engagement", "Ticker A-Z"],
        index=0,
        key="volatility_sort_mode_v1",
        help="Metric sorting is descending. Option Move % is the market-implied expected magnitude, not direction.",
    )
    show_debug = st.sidebar.checkbox("Show developer diagnostics", value=False)
    random_seed = st.sidebar.number_input("Random seed", min_value=1, max_value=9999, value=42, step=1)
    max_symbols = st.sidebar.slider("Max symbols to scan", min_value=10, max_value=500, value=50, step=10)

    scan_universe = select_scan_universe(
        universe_df,
        universe_preset,
        exchange_filters,
        index_filters,
        symbol_query,
        custom_tickers,
        scan_strategy,
        max_symbols,
        int(random_seed),
    )
    candidate_count = len(
        select_scan_universe(
            universe_df,
            universe_preset,
            exchange_filters,
            index_filters,
            symbol_query,
            custom_tickers,
            "Ticker A-Z",
            1_000_000,
            int(random_seed),
        )
    )
    tickers = scan_universe["Ticker"].tolist()
    st.sidebar.caption(f"{candidate_count:,} candidates; scanning {len(tickers):,} symbols this run.")
    scan_limited = candidate_count > len(tickers)

    horizon_days = st.sidebar.slider("Forecast horizon", min_value=1, max_value=7, value=5)
    lookback_period = st.sidebar.selectbox("Price lookback", ["3mo", "6mo", "1y", "2y"], index=1)
    include_options = st.sidebar.checkbox("Use options implied volatility", value=True)
    st.sidebar.subheader("Volatility Setups")
    show_30d_benchmark = st.sidebar.checkbox(
        "30D options IV benchmark",
        value=True,
        disabled=not include_options,
    )
    if not include_options:
        show_30d_benchmark = False
    realized_windows = st.sidebar.multiselect(
        "Historical volatility windows",
        list(HISTORICAL_WINDOW_COLUMNS),
        default=["20D", "60D"],
    )
    show_backtest = st.sidebar.checkbox("Same-horizon trailing backtest", value=True)
    top_n = st.sidebar.slider("Ranked rows", min_value=5, max_value=50, value=20, step=5)
    available_table_columns = available_forecast_display_columns(
        show_30d_benchmark,
        realized_windows,
        show_backtest,
    )
    default_table_columns = [
        column
        for column in DEFAULT_FORECAST_DISPLAY_COLUMNS
        if column in available_table_columns
    ]
    forecast_display_columns = st.sidebar.multiselect(
        "Highest Projected Volatility columns",
        available_table_columns,
        default=default_table_columns,
    )
    size_filters = st.sidebar.multiselect(
        "Market cap filter",
        list(MARKET_CAP_BUCKETS),
        default=[],
    )
    sector_filters = st.sidebar.multiselect("Sector filter", SECTOR_OPTIONS, default=[])
    min_price = st.sidebar.number_input("Min last price", min_value=0.0, value=0.0, step=1.0)
    min_dollar_volume = st.sidebar.number_input(
        "Min avg dollar volume",
        min_value=0.0,
        value=0.0,
        step=1_000_000.0,
        format="%.0f",
    )

    enable_social = st.sidebar.checkbox("Include social mention signals", value=True)
    social_lookback_days = st.sidebar.slider(
        "Social lookback",
        min_value=1,
        max_value=7,
        value=3,
        disabled=not enable_social,
    )
    social_feed_input = st.sidebar.text_area(
        "Social RSS feeds",
        default_social_feed_text(),
        height=92,
        disabled=not enable_social,
    )
    include_stocktwits = st.sidebar.checkbox(
        "Add Stocktwits streams",
        value=False,
        disabled=not enable_social,
    )
    max_stocktwits_symbols = st.sidebar.slider(
        "Stocktwits symbol cap",
        min_value=5,
        max_value=100,
        value=25,
        step=5,
        disabled=not enable_social or not include_stocktwits,
    )

    feed_input = st.sidebar.text_area("News and macro feeds", default_feed_text(), height=120)
    include_ticker_feeds = st.sidebar.checkbox("Add ticker-specific Yahoo feeds", value=False)
    macro_events_text = st.sidebar.text_area(
        "Scheduled macro events",
        DEFAULT_MACRO_EVENTS,
        height=82,
        placeholder="YYYY-MM-DD | FOMC decision | 5 | rates\nYYYY-MM-DD | Nonfarm payrolls | 5 | labor",
    )
    query = st.sidebar.text_input("Headline filter")

    feeds = add_ticker_feeds(parse_feed_lines(feed_input), tickers, include_ticker_feeds)
    social_feeds = parse_feed_lines(social_feed_input) if enable_social else tuple()

    refreshed_at = eastern_now()
    refreshed_clock = refreshed_at.strftime("%I:%M:%S %p ET").lstrip("0")
    st.markdown(
        "<div class='radar-header'>"
        "<div>"
        "<div class='equity-kicker'>Equity Analysis</div>"
        "<div class='radar-title'>Volatility Radar</div>"
        "<div class='radar-subtitle'>Market volatility scanner and catalyst monitor.</div>"
        "</div>"
        "<span class='badge neutral'>VOLR</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_scanner_toolbar(
        [
            {"label": "Universe", "value": universe_preset},
            {"label": "Symbols matched", "value": f"{len(tickers):,}/{candidate_count:,}"},
            {"label": "Horizon", "value": f"{horizon_days}D"},
            {"label": "Options", "value": "On" if include_options else "Off"},
            {"label": "Sort", "value": sort_mode},
            {"label": "Last refreshed", "value": refreshed_clock},
        ]
    )
    st.markdown(
        "<div class='radar-insight'>"
        f"{html.escape(universe_preset)} scan found {len(tickers):,} of {candidate_count:,} "
        f"matching symbols over a {horizon_days}-day horizon. Last refreshed {html.escape(refreshed_clock)}."
        "</div>",
        unsafe_allow_html=True,
    )
    if scan_limited:
        if scan_strategy == "Broad universe sample":
            st.caption(
                f"Scan is limited to {len(tickers):,} symbols for responsiveness and is spread across "
                f"the full {candidate_count:,}-symbol candidate universe before ranking by volatility."
            )
        elif scan_strategy == "Ticker A-Z":
            st.caption(
                f"Ticker A-Z mode is limited to the first {len(tickers):,} alphabetical symbols. "
                "Use Broad universe sample or Random sample to avoid an A-heavy scan."
            )
        else:
            st.caption(
                f"Random sample is limited to {len(tickers):,} symbols from the "
                f"{candidate_count:,}-symbol candidate universe before ranking by volatility."
            )

    if not tickers:
        st.warning("No symbols match the current universe filters.")
        return
    if not feeds:
        st.warning("Add at least one valid RSS feed URL.")
        return

    with st.spinner("Fetching prices, earnings, analyst targets, macro headlines, and socioeconomic signals..."):
        all_articles, feed_statuses, headline_refreshed_at, headline_stats = fetch_market_macro_headlines(feeds, tuple(tickers))
        social_mentions, social_statuses = fetch_social_mentions(
            social_feeds,
            tuple(tickers),
            enable_social,
            include_stocktwits,
            int(max_stocktwits_symbols),
        )
        scheduled_events, scheduled_statuses, scheduled_refreshed_at = fetch_scheduled_macro_events(lookahead_days=90)
        macro_context = build_macro_context(
            all_articles,
            horizon_days,
            macro_events_text,
            scheduled_events,
        )
        payloads = enrich_payloads_with_universe(
            fetch_market_payloads(
                tuple(tickers),
                lookback_period,
                horizon_days,
                include_options,
                show_30d_benchmark,
            ),
            scan_universe,
        )
        benchmark_history = fetch_benchmark_history(lookback_period)
        forecast_df = build_forecast_frame(
            payloads,
            benchmark_history,
            macro_context,
            all_articles,
            social_mentions,
            social_lookback_days,
            horizon_days,
        )
        forecast_df = apply_forecast_filters(
            forecast_df,
            size_filters,
            sector_filters,
            min_price,
            min_dollar_volume,
        )
        sort_column_used = sort_metric_for_mode(forecast_df, sort_mode) if not forecast_df.empty else "N/A"
        forecast_df = sort_forecast_for_mode(forecast_df, sort_mode)

    scheduled_df_all = event_frame(macro_context.events)
    scheduled_source_summary = scheduled_report_source_summary(scheduled_statuses)
    factor_df = macro_factor_frame(macro_context)
    ranked_df = forecast_df.head(top_n)
    top_row = ranked_df.iloc[0] if not ranked_df.empty else None
    earnings_catalysts = int(
        ranked_df["Days To Earnings"].between(0, horizon_days).fillna(False).sum()
    ) if not ranked_df.empty else 0
    avg_projected = float(ranked_df["Projected Move %"].mean()) if not ranked_df.empty else 0.0
    social_mentions_total = len(social_mentions)
    social_sort_label = (
        "Sorted by total engagement."
        if any(get_total_reactions(mention) > 0 for mention in social_mentions)
        else "Engagement unavailable; sorted by recency as fallback."
    )

    render_volatility_summary_cards(
        top_row,
        macro_context,
        earnings_catalysts,
        social_mentions_total,
        social_lookback_days,
        avg_projected,
        len(ranked_df),
    )
    render_stress_chip_row(macro_context, ranked_df)
    volatility_meta = provider_metadata(
        "Yahoo Finance/yfinance",
        "Volatility / Options Signals",
        "Delayed / cached",
        last_updated=refreshed_at,
        is_delayed=True,
        is_cached=True,
        delay_disclaimer="Options chains and quote history use yfinance fallback unless an options-capable provider is configured.",
        rate_limit_notes="Volatility and options fetches are cached for 5 minutes.",
        source_label="Yahoo Finance/yfinance",
    )
    headlines_meta = provider_metadata(
        "Shared RSS/API feeds",
        "Market & Macro Headlines",
        "Cached / refreshed",
        last_updated=headline_refreshed_at,
        is_delayed=False,
        is_cached=True,
        source_label=", ".join(headline_stats.get("sources", [])) or "RSS/API feeds",
        rate_limit_notes="Headline feeds are cached for 10 minutes.",
    )
    scheduled_meta = provider_metadata(
        "Official economic calendars",
        "Scheduled Reports / Economic Calendar",
        "Cached",
        last_updated=scheduled_refreshed_at,
        is_delayed=False,
        is_cached=True,
        source_label=scheduled_source_summary or "Official/reputable calendars",
        rate_limit_notes="Economic calendar sources are cached for 6 hours.",
    )
    st.caption(
        freshness_caption(volatility_meta, "Yahoo Finance/yfinance")
        + " | "
        + freshness_caption(headlines_meta, "RSS/API feeds")
        + " | "
        + freshness_caption(scheduled_meta, "Official calendars")
    )

    if show_debug:
        with st.expander("Developer diagnostics", expanded=False):
            diagnostics = pd.DataFrame(
                [
                    {"Metric": "Selected page", "Value": "Volatility Radar"},
                    {"Metric": "Candidate tickers", "Value": f"{candidate_count:,}"},
                    {"Metric": "Tickers fetched", "Value": f"{len(tickers):,}"},
                    {"Metric": "Rows after filters", "Value": f"{len(forecast_df):,}"},
                    {"Metric": "Rows displayed", "Value": f"{len(ranked_df):,}"},
                    {"Metric": "Scan mode", "Value": scan_strategy},
                    {"Metric": "Sort mode", "Value": sort_mode},
                    {"Metric": "Sort column used", "Value": sort_column_used},
                    {"Metric": "Last refresh", "Value": refreshed_clock},
                    {"Metric": "Auto-refresh enabled", "Value": st.session_state.get("global_auto_refresh_enabled", False)},
                    {"Metric": "Selected refresh interval", "Value": st.session_state.get("global_refresh_interval", "1 minute")},
                    {"Metric": "Volatility data freshness", "Value": freshness_caption(volatility_meta, "Yahoo Finance/yfinance")},
                    {"Metric": "Headline freshness", "Value": freshness_caption(headlines_meta, "RSS/API feeds")},
                    {"Metric": "Scheduled reports fetched", "Value": f"{len(scheduled_df_all):,}"},
                    {
                        "Metric": "Scheduled report sources",
                        "Value": scheduled_source_summary or "N/A",
                    },
                    {
                        "Metric": "Scheduled reports refreshed",
                        "Value": scheduled_refreshed_at.strftime("%Y-%m-%d %I:%M %p ET").lstrip("0"),
                    },
                ]
            )
            render_dashboard_table(diagnostics, height=360)
            if not factor_df.empty:
                st.caption("Socioeconomic feed and scheduled-event stress by category.")
                render_dashboard_table(factor_df, height=min(260, 42 + (len(factor_df) + 1) * 35))
            signal_debug = macro_signal_debug_frame(all_articles, factor_df)
            if not signal_debug.empty:
                st.caption("Socioeconomic feed item counts by category.")
                render_dashboard_table(signal_debug, height=min(260, 42 + (len(signal_debug) + 1) * 35))

    forecast_tab, catalysts_tab, news_tab, social_tab, health_tab = st.tabs(
        ["Forecasts", "Catalysts", "News Pulse", "Social Pulse", "Data Health"]
    )

    with forecast_tab:
        left_col, right_col = st.columns([1.45, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title(
                    "Highest Projected Volatility",
                    f"Sorted by {sort_column_used} descending. Option Move % is expected magnitude, not direction.",
                )
                table_columns = PINNED_FORECAST_COLUMNS + [
                    column
                    for column in forecast_display_columns
                    if column not in PINNED_FORECAST_COLUMNS
                ]
                table_columns = [column for column in table_columns if column in ranked_df.columns]
                render_forecast_table(ranked_df, table_columns)
        with right_col:
            with st.container(border=True):
                render_section_title(
                    "Tactical vs Benchmark",
                    "Projected move compared with options-implied benchmarks.",
                )
                if not ranked_df.empty:
                    chart_columns = ["Projected Move %"]
                    if "Options Move %" in ranked_df:
                        chart_columns.append("Options Move %")
                    if show_30d_benchmark and "30D Options Move %" in ranked_df:
                        chart_columns.append("30D Options Move %")
                    chart_df = ranked_df[["Ticker"] + chart_columns].head(10)
                    render_multi_series_chart(
                        chart_df,
                        "Ticker",
                        chart_columns,
                        "bar",
                        "Expected Move (%)",
                        height=245,
                    )
                else:
                    st.info("No forecast rows available.")

            if realized_windows and not ranked_df.empty:
                historical_columns = [
                    HISTORICAL_WINDOW_COLUMNS[window]
                    for window in realized_windows
                    if HISTORICAL_WINDOW_COLUMNS[window] in ranked_df.columns
                ]
                if historical_columns:
                    with st.container(border=True):
                        render_section_title(
                            "Historical Range Windows",
                            "Realized move references for selected lookbacks.",
                        )
                        history_chart = ranked_df[["Ticker"] + historical_columns].head(10)
                        render_multi_series_chart(
                            history_chart,
                            "Ticker",
                            historical_columns,
                            "bar",
                            "Historical Move (%)",
                            height=210,
                        )

            with st.container(border=True):
                render_section_title(
                    "Risk Components",
                    "Contributions feeding the volatility score.",
                )
                component_cols = [
                    "Base Move %",
                    "Earnings Risk",
                    "Macro Risk",
                    "News Risk",
                    "Social Risk",
                    "Volume Risk",
                    "Analyst Dispersion",
                ]
                component_cols = [column for column in component_cols if column in ranked_df.columns]
                if not ranked_df.empty and component_cols:
                    component_df = ranked_df[["Ticker"] + component_cols].head(10)
                    render_multi_series_chart(
                        component_df,
                        "Ticker",
                        component_cols,
                        "bar",
                        "Risk Contribution",
                        height=230,
                    )
                else:
                    st.info("No component data available.")

    with catalysts_tab:
        left_col, right_col = st.columns([1, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title(
                    "Earnings Window",
                    f"Companies with earnings inside the next {horizon_days} trading days.",
                )
                earnings_rows = ranked_df[
                    ranked_df["Days To Earnings"].between(0, horizon_days).fillna(False)
                ][
                    [
                        "Ticker",
                        "Company",
                        "Earnings Date",
                        "Days To Earnings",
                        "Projected Move %",
                        "Earnings Risk",
                    ]
                ]
                earnings_rows = sort_descending_by_metric(earnings_rows, "Earnings Risk")
                st.dataframe(
                    earnings_rows,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Projected Move %": st.column_config.NumberColumn(format="+/-%.2f%%"),
                        "Earnings Risk": st.column_config.NumberColumn(format="%.2f"),
                    },
                    height=min(300, max(130, 42 + (len(earnings_rows) + 1) * 35)),
                )

        with right_col:
            with st.container(border=True):
                render_section_title(
                    "Socioeconomic Factor Load",
                    "Macro stress by category from feeds and scheduled events.",
                )
                render_macro_factor_chart(factor_df, scheduled_refreshed_at, scheduled_source_summary)

            with st.container(border=True):
                render_section_title(
                    "Macro-Sensitive Names",
                    "Highest ranked macro-risk exposure in the scan.",
                )
                macro_sensitive = sort_descending_by_metric(ranked_df, "Macro Risk").head(10)
                st.dataframe(
                    macro_sensitive[
                        ["Ticker", "Exchange", "Sector", "Beta", "Macro Risk", "Main Drivers"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Beta": st.column_config.NumberColumn(format="%.2f"),
                        "Macro Risk": st.column_config.NumberColumn(format="%.2f"),
                    },
                    height=min(360, max(160, 42 + (len(macro_sensitive) + 1) * 35)),
                )

        with st.container(border=True):
            render_section_title(
                "Scheduled Reports",
                "Official and reputable economic calendars, sorted by upcoming release time.",
            )
            st.caption(freshness_caption(scheduled_meta, "Official/reputable calendars"))
            filter_cols = st.columns([1.1, 0.9, 1.0, 0.9], gap="small")
            category_options = sorted(scheduled_df_all["Category"].dropna().astype(str).unique()) if not scheduled_df_all.empty else []
            impact_options = [impact for impact in ["High", "Medium", "Low"] if scheduled_df_all.empty or impact in set(scheduled_df_all["Impact"].astype(str))]
            source_options = sorted(scheduled_df_all["Source"].dropna().astype(str).unique()) if not scheduled_df_all.empty else []
            with filter_cols[0]:
                scheduled_categories = st.multiselect(
                    "Category",
                    category_options,
                    default=[],
                    key="scheduled_report_categories",
                )
            with filter_cols[1]:
                scheduled_impacts = st.multiselect(
                    "Impact",
                    impact_options,
                    default=[],
                    key="scheduled_report_impacts",
                )
            with filter_cols[2]:
                scheduled_sources = st.multiselect(
                    "Source",
                    source_options,
                    default=[],
                    key="scheduled_report_sources",
                )
            with filter_cols[3]:
                scheduled_date_range = st.selectbox(
                    "Date range",
                    ["Today", "This Week", "Next 30 Days"],
                    index=2,
                    key="scheduled_report_date_range",
                )

            scheduled_df = filter_scheduled_reports(
                scheduled_df_all,
                scheduled_categories,
                scheduled_impacts,
                scheduled_sources,
                scheduled_date_range,
            )
            render_metric_strip(
                scheduled_reports_summary_items(scheduled_df, scheduled_refreshed_at),
                columns=4,
            )
            render_scheduled_reports_table(scheduled_df, height=360)

            source_issues = [
                f"{status.get('source')}: {status.get('message')}"
                for status in scheduled_statuses
                if str(status.get("status", "")).lower() in {"error", "warning"}
            ]
            if source_issues:
                with st.expander("Scheduled report source notes", expanded=False):
                    for issue in source_issues:
                        st.caption(issue)
            if show_debug:
                st.caption(
                    f"Developer diagnostics: {len(scheduled_df_all):,} scheduled reports fetched; "
                    f"{len(scheduled_df):,} after filters; sources: {scheduled_source_summary or 'N/A'}."
                )

    with news_tab:
        left_col, right_col = st.columns([1.3, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_market_macro_headlines(
                    all_articles,
                    feed_statuses,
                    headline_refreshed_at,
                    key_prefix="vol_market_macro",
                    title="Market & Macro Headlines",
                    subtitle="Ticker and macro headlines feeding the news-risk score.",
                    compact=False,
                    limit=40,
                    default_keyword=query,
                    show_debug=show_debug,
                    stats=headline_stats,
                )

        with right_col:
            with st.container(border=True):
                render_section_title(
                    "Ticker News Risk",
                    "Headline density and sentiment by scanned ticker.",
                )
                news_rows = []
                for ticker in tickers:
                    risk, sentiment, mentions = ticker_news_risk(ticker, all_articles)
                    news_rows.append(
                        {
                            "Ticker": ticker,
                            "News Risk": risk,
                            "Mentions": mentions,
                            "Avg Sentiment": sentiment,
                        }
                    )
                news_df = sort_descending_by_metric(pd.DataFrame(news_rows), "News Risk")
                st.dataframe(
                    news_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "News Risk": st.column_config.NumberColumn(format="%.2f"),
                        "Avg Sentiment": st.column_config.NumberColumn(format="%.2f"),
                    },
                    height=min(300, max(150, 42 + (len(news_df) + 1) * 35)),
                )
                if not news_df.empty:
                    render_single_bar_chart(
                        news_df.head(12),
                        "Ticker",
                        "News Risk",
                        "News Risk",
                        height=220,
                        color="#5ec7e8",
                    )

            with st.container(border=True):
                render_section_title(
                    "Macro Headlines",
                    "Top macro headlines contributing to stress.",
                )
                if not macro_context.top_headlines:
                    st.info("No macro headlines detected in the current feed set.")
                for article in sort_articles_by_relevance(macro_context.top_headlines)[:6]:
                    render_article(article)

    with social_tab:
        left_col, right_col = st.columns([1.25, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title(
                    "Social Mentions",
                    f"Matched posts and social RSS items in the selected lookback. {social_sort_label}",
                )
                st.caption(
                    f"Cached / refreshed: updated {refreshed_at.strftime('%I:%M:%S %p ET').lstrip('0')} | "
                    "Source: configured social RSS/Stocktwits feeds | Cache TTL: 10 minutes"
                )
                if not social_mentions:
                    st.info("No social mentions returned for the current scan.")
                for mention in sort_social_mentions_by_reactions(social_mentions)[:60]:
                    render_social_mention(mention)

        with right_col:
            with st.container(border=True):
                render_section_title(
                    "Ticker Social Risk",
                    "Mention velocity and sentiment by scanned ticker.",
                )
                social_rows = []
                for ticker in tickers:
                    risk, sentiment, mentions = ticker_social_risk(
                        ticker,
                        social_mentions,
                        social_lookback_days,
                    )
                    engagement = ticker_social_engagement(ticker, social_mentions, social_lookback_days)
                    social_rows.append(
                        {
                            "Ticker": ticker,
                            "Social Risk": risk,
                            "Mentions": mentions,
                            "Social Engagement": engagement,
                            "Avg Sentiment": sentiment,
                        }
                    )
                social_df = sort_descending_by_metric(pd.DataFrame(social_rows), "Social Risk")
                st.dataframe(
                    social_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Social Risk": st.column_config.NumberColumn(format="%.2f"),
                        "Avg Sentiment": st.column_config.NumberColumn(format="%.2f"),
                    },
                    height=min(300, max(150, 42 + (len(social_df) + 1) * 35)),
                )
                if not social_df.empty:
                    render_single_bar_chart(
                        social_df.head(12),
                        "Ticker",
                        "Social Risk",
                        "Social Risk",
                        height=220,
                        color="#49d69b",
                    )

            with st.container(border=True):
                render_section_title(
                    "Most Mentioned",
                    "Ticker counts across social sources.",
                )
                mention_counter: Counter[str] = Counter()
                for mention in sort_social_mentions_by_reactions(social_mentions):
                    for ticker in mention.mentions:
                        mention_counter[ticker] += 1
                mention_df = pd.DataFrame(
                    [
                        {"Ticker": ticker, "Mentions": count}
                        for ticker, count in mention_counter.most_common(15)
                    ]
                )
                if mention_df.empty:
                    st.caption("No ticker mentions in the social feed set.")
                else:
                    render_single_bar_chart(
                        mention_df,
                        "Ticker",
                        "Mentions",
                        "Mentions",
                        height=210,
                        color="#9bdcf3",
                    )

    with health_tab:
        market_health_df, feed_health_df = data_health_frame(payloads, feed_statuses)
        left_col, right_col = st.columns([1, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title(
                    "Universe Source Health",
                    "Exchange and index constituent source status.",
                )
                render_dashboard_table(universe_status_df, height=220)

            with st.container(border=True):
                render_section_title(
                    "Scanned Universe",
                    "Symbols included after sidebar filters and scan cap.",
                )
                render_dashboard_table(scan_universe, height=260)

            with st.container(border=True):
                render_section_title(
                    "Market Data Health",
                    "Per-symbol price, options, and fundamentals availability.",
                )
                render_dashboard_table(market_health_df, height=260)

        with right_col:
            with st.container(border=True):
                render_section_title(
                    "Feed Health",
                    "News and macro RSS status.",
                )
                render_dashboard_table(feed_health_df, height=220)

            with st.container(border=True):
                render_section_title(
                    "Social Source Health",
                    "Social RSS and optional Stocktwits source status.",
                )
                render_dashboard_table(sort_status_frame(pd.DataFrame(social_statuses)), height=220)

            with st.container(border=True):
                render_section_title(
                    "Scheduled Reports Source Health",
                    "Economic calendar source status and refresh metadata.",
                )
                render_dashboard_table(sort_status_frame(pd.DataFrame(scheduled_statuses)), height=220)

            with st.container(border=True):
                render_section_title(
                    "Model Notes",
                    "How to interpret the risk ranking.",
                )
                st.markdown(
                    "- Forecasts estimate absolute volatility, not investment direction.\n"
                    "- Broad universes come from Nasdaq Trader symbol directories; index filters come from public index constituent pages when available.\n"
                    "- The scan cap keeps free data calls responsive. Use exchange, index, search, size, sector, price, and liquidity filters to narrow broad universes.\n"
                    "- Base move uses realized return volatility and ATR. Catalysts add risk from earnings timing, macro stress, ticker news, social mentions, volume shock, analyst target dispersion, momentum, and gaps.\n"
                    "- Macro and socioeconomic factors come from RSS headlines, cached economic-calendar sources, and any sidebar scheduled events."
                )

        article_df = articles_to_frame(all_articles)
        social_mention_df = social_mentions_to_frame(social_mentions)
        download_cols = st.columns(4)
        download_cols[0].download_button(
            "Download forecasts",
            forecast_df.to_csv(index=False),
            file_name="volatility_forecasts.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=forecast_df.empty,
        )
        download_cols[1].download_button(
            "Download articles",
            article_df.to_csv(index=False),
            file_name="catalyst_articles.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=article_df.empty,
        )
        download_cols[2].download_button(
            "Download data health",
            market_health_df.to_csv(index=False),
            file_name="market_data_health.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=market_health_df.empty,
        )
        download_cols[3].download_button(
            "Download social mentions",
            social_mention_df.to_csv(index=False),
            file_name="social_mentions.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=social_mention_df.empty,
        )


def render_home_dashboard() -> None:
    st.sidebar.header("Home")
    refresh_requested = st.sidebar.button("Refresh home data", use_container_width=True)
    if refresh_requested:
        fetch_home_market_snapshot.clear()
        fetch_sector_performance.clear()
        fetch_home_stock_snapshot.clear()
        fetch_feeds.clear()
        fetch_market_macro_headlines.clear()
        fetch_scheduled_macro_events.clear()
        fetch_performance_history.clear()
    show_debug = st.sidebar.checkbox("Show Home diagnostics", value=False, key="home_debug")

    default_ticker = st.session_state.get("stock_due_diligence_ticker", "SPY")
    st.markdown("<div class='equity-kicker'>Market Dashboard</div>", unsafe_allow_html=True)
    st.title("Home")
    st.markdown(
        "<div class='home-subtitle'>U.S. market snapshot, macro catalysts, major headlines, and quick stock view.</div>",
        unsafe_allow_html=True,
    )

    if "home_quick_ticker" not in st.session_state:
        st.session_state["home_quick_ticker"] = default_ticker
    home_ticker = normalize_symbol(str(st.session_state.get("home_quick_ticker") or "SPY")) or "SPY"
    home_ticker = normalize_symbol(home_ticker) or "SPY"

    with st.spinner("Loading market snapshot, sector performance, headlines, and catalysts..."):
        market_df, market_status, market_refreshed = fetch_home_market_snapshot()
        sector_df, sector_status, sector_refreshed = fetch_sector_performance()
        stock_snapshot, stock_status, stock_refreshed = fetch_home_stock_snapshot(home_ticker)
        home_articles, home_statuses, headline_refreshed, headline_stats = fetch_market_macro_headlines(
            MARKET_MACRO_FEEDS,
            (home_ticker,),
        )
        scheduled_events, scheduled_statuses, scheduled_refreshed = fetch_scheduled_macro_events(lookahead_days=30)

    scheduled_df_all = event_frame(scheduled_events)
    catalysts_df = filter_scheduled_reports(scheduled_df_all, [], [], [], "This Week")
    mood_score, mood_label = market_mood_score(market_df, sector_df, home_articles, catalysts_df)
    refreshed_text = market_refreshed.strftime("%I:%M:%S %p ET").lstrip("0")
    market_meta = metadata_from_status_frame(market_status, "Market Snapshot", market_refreshed)
    sector_meta = metadata_from_status_frame(sector_status, "Sector Performance", sector_refreshed)
    stock_meta = stock_snapshot.get("Provider Metadata") or metadata_to_dict(default_yahoo_metadata("Quick Stock Snapshot", last_updated=stock_refreshed))
    headline_meta = provider_metadata(
        "Shared RSS/API feeds",
        "Market & Macro Headlines",
        "Cached / refreshed",
        last_updated=headline_refreshed,
        is_delayed=False,
        is_cached=True,
        source_label=", ".join(headline_stats.get("sources", [])) or "RSS/API feeds",
        rate_limit_notes="RSS feeds are cached for 10 minutes.",
    )
    scheduled_meta = provider_metadata(
        "Official economic calendars",
        "Scheduled Reports / Economic Calendar",
        "Cached",
        last_updated=scheduled_refreshed,
        is_delayed=False,
        is_cached=True,
        source_label=scheduled_report_source_summary(scheduled_statuses) or "Official/reputable calendars",
        rate_limit_notes="Economic calendars are cached for 6 hours.",
    )

    with st.container(border=True):
        render_section_title(
            "Market Snapshot",
            "Major U.S. index, volatility, and rates indicators.",
        )
        market_items = []
        for _, row in market_df.iterrows():
            change = coerce_float(row.get("Change"))
            change_pct = coerce_float(row.get("Change %"))
            change_text = (
                f"{format_number(change, 2)} / {format_percent(change_pct, 2, signed=True)}"
                if change is not None and change_pct is not None
                else "N/A"
            )
            market_items.append(
                {
                    "label": row.get("Label"),
                    "value": format_market_snapshot_value(row),
                    "context": change_text,
                    "tone": "good" if (change_pct or 0) >= 0 else "bad",
                }
            )
        render_home_cards(market_items, "home-market-grid")
        st.caption(freshness_caption(market_meta, "Yahoo Finance/yfinance"))

    top_left, top_right = st.columns([1.25, 1], gap="small")
    with top_left:
        with st.container(border=True):
            render_section_title(
                "Sector Performance",
                "Major U.S. sector ETFs sorted best to worst by daily move.",
            )
            render_sector_performance_chart(sector_df)
            st.caption(
                "Sector proxy: SPDR sector ETFs | "
                + freshness_caption(sector_meta, "Yahoo Finance/yfinance")
            )

    with top_right:
        with st.container(border=True):
            render_section_title(
                "Market Mood",
                "Heuristic risk gauge from index moves, VIX, sectors, headlines, and macro-event density.",
            )
            render_home_cards(
                [
                    {
                        "label": "Risk Gauge",
                        "value": f"{mood_score}/100",
                        "context": mood_label,
                        "tone": "good" if mood_score >= 62 else "bad" if mood_score <= 42 else "neutral",
                    },
                    {
                        "label": "High Impact Events",
                        "value": int(catalysts_df["Impact"].astype(str).str.casefold().eq("high").sum()) if not catalysts_df.empty else 0,
                        "context": "this week",
                    },
                    {
                        "label": "Headlines",
                        "value": len(home_articles),
                        "context": "quality-filtered",
                    },
                    {
                        "label": "Quick Ticker",
                        "value": home_ticker,
                        "context": stock_snapshot.get("Quote Label", "quote"),
                    },
                ],
                "home-mini-grid",
            )
            st.caption("Market Mood is a heuristic signal for dashboard context, not investment advice.")

    news_col, stock_col = st.columns([1.25, 1], gap="small")
    with news_col:
        with st.container(border=True):
            headline_render = render_market_macro_headlines(
                home_articles,
                home_statuses,
                headline_refreshed,
                key_prefix="home_market_macro",
                title="Market & Macro Headlines",
                subtitle="Reputable market and macro feeds sorted newest first.",
                compact=True,
                limit=10,
                show_debug=show_debug,
                stats=headline_stats,
            )

    with stock_col:
        with st.container(border=True):
            home_ticker = st.text_input(
                "Ticker",
                value=home_ticker,
                placeholder="SPY",
                key="home_quick_ticker",
                help="Updates the Quick Stock Snapshot.",
            ).upper().strip() or "SPY"
            home_ticker = normalize_symbol(home_ticker) or "SPY"
            render_section_title(
                "Quick Stock Snapshot",
                f"Selected ticker: {home_ticker}",
            )
            next_earnings = stock_snapshot.get("Next Earnings")
            daily_change_pct = stock_snapshot.get("Daily Change %")
            render_home_stock_group(
                "Price & Trading",
                [
                    {
                        "label": "Last Price",
                        "value": format_currency(stock_snapshot.get("Last Price"), 2),
                        "context": stock_snapshot.get("Quote Label", "quote"),
                        "tone": "good" if (daily_change_pct or 0) >= 0 else "bad",
                    },
                    {
                        "label": "Daily Change",
                        "value": format_percent(daily_change_pct, 2, signed=True),
                        "context": "today",
                        "tone": "good" if (daily_change_pct or 0) >= 0 else "bad",
                    },
                    {
                        "label": "Market Cap",
                        "value": format_compact_currency(stock_snapshot.get("Market Cap"), 2),
                        "context": "equity value",
                    },
                    {
                        "label": "Volume",
                        "value": format_number(stock_snapshot.get("Volume"), 0),
                        "context": f"Rel Vol {format_number(stock_snapshot.get('Relative Volume'), 2)}",
                    },
                    {
                        "label": "52W Range",
                        "value": f"{format_currency(stock_snapshot.get('52W Low'), 2)} - {format_currency(stock_snapshot.get('52W High'), 2)}",
                        "context": "low / high",
                    },
                ],
            )
            render_home_stock_group(
                "Valuation",
                [
                    {"label": "P/E", "value": format_number(stock_snapshot.get("Trailing PE"), 2), "context": "trailing"},
                    {"label": "Forward P/E", "value": format_number(stock_snapshot.get("Forward PE"), 2), "context": "estimate"},
                    {"label": "EPS", "value": format_number(stock_snapshot.get("EPS"), 2), "context": "ttm"},
                ],
            )
            render_home_stock_group(
                "Growth",
                [
                    {"label": "Rev Growth", "value": format_percent(stock_snapshot.get("Revenue Growth %"), 1, signed=True), "context": "reported"},
                    {"label": "Dividend", "value": format_percent(stock_snapshot.get("Dividend Yield %"), 2), "context": "yield"},
                ],
            )
            render_home_stock_group(
                "Analyst View",
                [
                    {"label": "Rating", "value": stock_snapshot.get("Analyst Rating") or "N/A", "context": "consensus"},
                    {"label": "Avg Target", "value": format_currency(stock_snapshot.get("Avg Target"), 2), "context": "analyst mean"},
                ],
            )
            render_home_stock_group(
                "Event Risk",
                [
                    {"label": "Option Move", "value": format_move(stock_snapshot.get("Option Move %"), 2), "context": "nearest expiry"},
                    {"label": "IV", "value": format_percent(stock_snapshot.get("IV %"), 1), "context": "atm proxy"},
                    {"label": "Next Earnings", "value": next_earnings.strftime("%Y-%m-%d") if isinstance(next_earnings, date) else "N/A", "context": "if available"},
                    {"label": "Short Interest", "value": format_percent(stock_snapshot.get("Short Interest %"), 2), "context": "float"},
                    {"label": "IV Rank", "value": format_number(stock_snapshot.get("IV Rank"), 1), "context": "unavailable"},
                ],
            )
            stock_history = fetch_performance_history(home_ticker, "1M")
            stock_frame = performance_frame(stock_history)
            if stock_frame.empty:
                st.info("No compact price chart is available for this ticker.")
            else:
                render_time_series_chart(stock_frame, "Stock Price", "Stock Price ($)", height=180)
            st.caption(
                freshness_caption(stock_meta, "Yahoo Finance/yfinance")
            )

    with st.container(border=True):
        render_section_title(
            "Today's Market Catalysts",
            "Upcoming economic reports, Fed events, Treasury auctions, and energy inventory releases.",
        )
        catalyst_view = catalysts_df.head(12)
        render_compact_scheduled_reports_table(
            catalyst_view,
            height=min(360, max(190, 38 + (len(catalyst_view) + 1) * 32)),
        )
        st.caption(
            freshness_caption(scheduled_meta, "Official/reputable calendars")
        )

    if show_debug:
        with st.expander("Home diagnostics", expanded=False):
            newest, oldest = article_timestamp_bounds(home_articles)
            diagnostics = pd.DataFrame(
                [
                    {"Metric": "Raw headlines fetched", "Value": headline_stats.get("raw_count", "N/A")},
                    {"Metric": "Headlines filtered out", "Value": headline_stats.get("filtered_out", "N/A")},
                    {"Metric": "Quality-filtered headlines", "Value": len(home_articles)},
                    {"Metric": "Headlines displayed", "Value": headline_render.get("displayed_count", "N/A")},
                    {"Metric": "Headline summaries hidden", "Value": headline_render.get("summaries_hidden", True)},
                    {"Metric": "HTML-like headline summaries detected", "Value": headline_render.get("html_summary_count", "N/A")},
                    {"Metric": "Newest headline", "Value": newest},
                    {"Metric": "Oldest headline", "Value": oldest},
                    {"Metric": "News sources used", "Value": ", ".join(sorted({article.source for article in home_articles})) or "N/A"},
                    {"Metric": "Selected ticker state", "Value": home_ticker},
                    {"Metric": "Market data source", "Value": "Yahoo Finance/yfinance"},
                    {"Metric": "Sector data source", "Value": "Yahoo Finance/yfinance sector ETFs"},
                    {"Metric": "Quick Stock Snapshot provider", "Value": stock_snapshot.get("Provider", "Yahoo Finance/yfinance")},
                    {"Metric": "Scheduled reports fetched", "Value": len(scheduled_df_all)},
                    {"Metric": "Today's Market Catalysts displayed rows", "Value": min(12, len(catalysts_df))},
                    {"Metric": "Scheduled report source status", "Value": scheduled_report_source_summary(scheduled_statuses) or "N/A"},
                    {"Metric": "Home layout mode", "Value": "Header > Snapshot > Sector/Mood > Headlines+Quick Stock > Full-width Catalysts"},
                    {"Metric": "Stock snapshot fields available", "Value": sum(1 for value in stock_snapshot.values() if value not in (None, "", "N/A"))},
                    {"Metric": "Stock snapshot fields missing", "Value": sum(1 for value in stock_snapshot.values() if value in (None, "", "N/A"))},
                    {"Metric": "Auto-refresh enabled", "Value": st.session_state.get("global_auto_refresh_enabled", False)},
                    {"Metric": "Selected refresh interval", "Value": st.session_state.get("global_refresh_interval", "1 minute")},
                    {"Metric": "Cache TTLs", "Value": "; ".join(f"{key}: {value}" for key, value in DATA_REFRESH_TTLS.items())},
                    {"Metric": "Provider hierarchy", "Value": " | ".join(f"{key}: {' > '.join(value)}" for key, value in PROVIDER_HIERARCHY.items())},
                    {"Metric": "Last refresh", "Value": refreshed_text},
                ]
            )
            render_dashboard_table(diagnostics, height=320)
            status_frames = [
                market_status.assign(Area="Market"),
                sector_status.assign(Area="Sector"),
                stock_status.assign(Area="Stock"),
                pd.DataFrame(home_statuses).rename(columns={"source": "Source", "status": "Status", "message": "Message"}).assign(Area="News"),
                pd.DataFrame(scheduled_statuses).rename(columns={"source": "Source", "status": "Status", "message": "Message"}).assign(Area="Scheduled Reports"),
            ]
            combined_status = pd.concat(status_frames, ignore_index=True, sort=False)
            render_dashboard_table(combined_status[["Area", "Source", "Status", "Message"]].fillna(""), height=320)


def render_home_financials() -> None:
    st.sidebar.header("Stock Due Diligence")
    period = st.sidebar.radio("Statement period", ["Annual", "Quarterly"], index=0)
    periods_to_show = st.sidebar.slider("Periods to show", min_value=3, max_value=8, value=5)
    target_year = st.sidebar.number_input(
        "Actuals/targets year",
        min_value=2020,
        max_value=date.today().year + 2,
        value=date.today().year,
        step=1,
    )
    show_raw_statements = st.sidebar.checkbox("Show raw statements", value=False)
    if st.sidebar.button("Refresh company data", use_container_width=True):
        fetch_company_financials.clear()

    header_cols = st.columns([0.72, 0.28], gap="small")
    with header_cols[0]:
        st.markdown("<div class='equity-kicker'>Equity Research Dashboard</div>", unsafe_allow_html=True)
        st.title("Stock Due Diligence")
    with header_cols[1]:
        ticker_input = st.text_input(
            "Company selector",
            "AAPL",
            placeholder="Ticker",
            help="Enter a publicly traded ticker symbol.",
            key="stock_due_diligence_ticker",
        ).upper().strip()

    ticker = normalize_symbol(ticker_input)
    if not ticker:
        st.warning("Enter a valid ticker symbol.")
        return

    with st.spinner(f"Fetching financial statements for {ticker}..."):
        payload = fetch_company_financials(
            ticker,
            period,
            int(periods_to_show),
            int(target_year),
        )

    if payload.get("status") != "OK":
        st.error(payload.get("message", "Unable to fetch company financials."))
        return

    info = payload.get("info", {})
    income, balance, cashflow, quarterly = company_statement_set(payload, period)
    series_map = financial_series_map(income, balance, cashflow)
    financial_df = align_financial_series(series_map, quarterly, periods_to_show)
    quarterly_income, quarterly_balance, quarterly_cashflow, _ = company_statement_set(payload, "Quarterly")
    quarterly_series_map = financial_series_map(
        quarterly_income,
        quarterly_balance,
        quarterly_cashflow,
    )
    quarterly_financial_df = align_financial_series(quarterly_series_map, True, 12)
    annual_income, annual_balance, annual_cashflow, _ = company_statement_set(payload, "Annual")
    annual_financial_df = align_financial_series(
        financial_series_map(annual_income, annual_balance, annual_cashflow),
        False,
        8,
    )
    actuals_targets_df, price_target_df = build_actuals_targets_frame(
        quarterly_financial_df,
        annual_financial_df,
        payload.get("revenue_estimate", pd.DataFrame()),
        payload.get("earnings_estimate", pd.DataFrame()),
        info,
        int(target_year),
    )
    quarterly_breakout_df = build_quarterly_actuals_targets_breakout(
        quarterly_financial_df,
        annual_financial_df,
        payload.get("revenue_estimate", pd.DataFrame()),
        payload.get("earnings_estimate", pd.DataFrame()),
        payload.get("earnings_expectations", pd.DataFrame()),
        int(target_year),
    )
    ratios = ratio_frame(financial_df)
    metrics = latest_financial_metrics(financial_df, ratios, info)
    score, score_notes = financial_health_score(metrics)
    earnings_expectations = payload.get("earnings_expectations", pd.DataFrame())
    analyst_reports = payload.get("analyst_reports", pd.DataFrame())
    analyst_reports_refreshed = payload.get("analyst_reports_refreshed")
    next_earnings = next_company_earnings_date(payload, info)

    company_name = (
        info.get("longName")
        or info.get("shortName")
        or info.get("displayName")
        or ticker
    )
    sector = info.get("sector") or "Unknown sector"
    industry = info.get("industry") or "Unknown industry"
    latest_price = coerce_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    rendered_at = eastern_now()
    rendered_time = rendered_at.strftime("%H:%M:%S")
    quote_snapshot = fetch_quote_snapshot(ticker)
    quote_price = quote_snapshot.get("price") or latest_price
    quote_meta = quote_snapshot.get("provider") or metadata_to_dict(default_yahoo_metadata("Company Quote", last_updated=rendered_at))
    financial_meta = provider_metadata(
        "Yahoo Finance/yfinance",
        "Financial Statements / Fundamentals",
        "Cached",
        last_updated=rendered_at,
        is_cached=True,
        delay_disclaimer="Fundamentals and analyst data are slow-moving and cached for 6 hours.",
        rate_limit_notes="Manual Refresh Now clears the fundamentals cache when explicitly requested.",
        source_label="Yahoo Finance/yfinance",
    )

    st.markdown(
        "<div class='equity-shell'>"
        "<div class='equity-heading'>"
        f"<div><div class='equity-kicker'>Selected Company</div>"
        f"<div class='company-title'>{html.escape(ticker)} - {html.escape(company_name)}</div>"
        f"<div class='company-subtitle'>{html.escape(sector)} / {html.escape(industry)}</div></div>"
        f"<span class='badge neutral'>{html.escape(str(quote_snapshot.get('quote_label', 'Delayed quote')))}</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    render_quote_module(ticker, company_name)

    render_info_strip(
        [
            {"label": "Workspace", "value": "Equity Analysis"},
            {"label": "Statements", "value": period},
            {"label": "Targets", "value": str(int(target_year))},
            {"label": "Industry", "value": industry},
            {"label": "Refreshed", "value": f"{rendered_time} ET"},
        ],
        columns=5,
    )
    st.caption(
        freshness_caption(quote_meta, "Yahoo Finance/yfinance")
        + " | "
        + freshness_caption(financial_meta, "Yahoo Finance/yfinance")
    )

    revenue_growth_text = format_percent(metrics.get("Revenue Growth %"), signed=True)
    render_research_kpi_grid(
        [
            {
                "label": "Price",
                "value": "N/A" if quote_price is None else f"${quote_price:,.2f}",
                "helper": "Last trade",
                "badge": (
                    f"{format_currency(quote_snapshot.get('change'), 2)} "
                    f"({format_percent(quote_snapshot.get('change_pct'), 2, signed=True)})"
                    if quote_snapshot.get("change") is not None
                    and quote_snapshot.get("change_pct") is not None
                    else "No change data"
                ),
                "tone": quote_tone(quote_snapshot.get("change")),
            },
            {
                "label": "Mkt Cap",
                "value": format_compact_currency(metrics.get("Market Cap"), 2),
                "helper": "Equity value",
            },
            {
                "label": "Revenue",
                "value": format_compact_currency(metrics.get("Revenue"), 1),
                "helper": "Latest period",
                "badge": None if revenue_growth_text == "N/A" else f"{revenue_growth_text} growth",
                "tone": metric_tone(revenue_growth_text),
            },
            {
                "label": "Net Margin",
                "value": format_percent(metrics.get("Net Margin %")),
                "helper": "Latest period",
            },
            {
                "label": "Score",
                "value": f"{score}/100",
                "helper": score_notes[0].title() if score_notes else "Financial health",
                "tone": "good" if score >= 70 else "warn" if score >= 45 else "bad",
                "progress": score,
            },
        ]
    )

    if score_notes:
        st.subheader("Score Drivers")
        render_driver_grid(score_driver_items(score_notes, metrics))

    overview_tab, targets_tab, expectations_tab, statements_tab, ratios_tab, valuation_tab, raw_tab = st.tabs(
        ["Overview", f"{int(target_year)} Actuals & Targets", "Analyst Expectations", "Statements", "Margins & Cash Flow", "Valuation", "Raw Data"]
    )

    with overview_tab:
        with st.container(border=True):
            render_section_title(
                "Stock Performance",
                "Selected-range price action with performance, high, and low.",
            )
            range_actions = [
                {
                    "key": range_key,
                    "label": range_key,
                    "help": config["label"],
                }
                for range_key, config in PERFORMANCE_RANGES.items()
            ]
            selected_range = render_button_strip(
                range_actions,
                "home_performance_range",
                default_key="1Y",
            ) or "1Y"
            performance_history = fetch_performance_history(ticker, selected_range)
            performance_df = performance_frame(performance_history)
            performance_stats = performance_summary(performance_df)
            render_metric_strip(
                [
                    {
                        "label": "Range",
                        "value": selected_range,
                        "context": PERFORMANCE_RANGES.get(selected_range, {}).get("label", ""),
                    },
                    {
                        "label": "Performance",
                        "value": format_percent(performance_stats.get("return"), decimals=2),
                        "context": "selected range",
                        "tone": "good" if (performance_stats.get("return") or 0) >= 0 else "bad",
                    },
                    {
                        "label": "High",
                        "value": format_currency(performance_stats.get("high"), 2),
                        "context": "range high",
                    },
                    {
                        "label": "Low",
                        "value": format_currency(performance_stats.get("low"), 2),
                        "context": "range low",
                    },
                ],
                columns=4,
            )
            if performance_df.empty:
                st.info("No stock performance history returned for the selected range.")
            else:
                render_time_series_chart(
                    performance_df,
                    "Stock Price",
                    "Stock Price ($)",
                    height=245,
                    color="#5ec7e8",
                )

        left_col, right_col = st.columns([1.2, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title("Revenue and Profit", f"{period} statement trend")
                if financial_df.empty:
                    st.info("No statement rows were returned for this company.")
                else:
                    chart_cols = [
                        column
                        for column in ["Revenue", "Gross Profit", "Operating Income", "Net Income"]
                        if column in financial_df and financial_df[column].notna().any()
                    ]
                    render_multi_series_chart(
                        financial_df,
                        "Period",
                        chart_cols,
                        "bar",
                        "Amount ($B)",
                        value_scale=1_000_000_000,
                        height=245,
                    )

        with right_col:
            with st.container(border=True):
                render_section_title("Balance Sheet Snapshot", "Latest reported balance sheet")
                snapshot_rows = [
                    ("Cash", latest_value(series_map["Cash"])),
                    ("Total Debt", latest_value(series_map["Total Debt"])),
                    ("Stockholders Equity", latest_value(series_map["Stockholders Equity"])),
                    ("Total Assets", latest_value(series_map["Total Assets"])),
                ]
                snapshot_df = pd.DataFrame(snapshot_rows, columns=["Metric", "Value"])
                render_dashboard_table(
                    format_financial_table(snapshot_df, currency_columns=["Value"]),
                    height=190,
                )

            with st.container(border=True):
                render_section_title("Key Ratios", "Latest period")
                ratio_snapshot = pd.DataFrame(
                    [
                        {"Metric": "Current Ratio", "Value": metrics.get("Current Ratio")},
                        {"Metric": "Debt / Equity", "Value": metrics.get("Debt / Equity")},
                        {"Metric": "Cash / Debt", "Value": metrics.get("Cash / Debt")},
                        {"Metric": "FCF Margin %", "Value": metrics.get("FCF Margin %")},
                    ]
                )
                ratio_snapshot_display = ratio_snapshot.copy()
                ratio_snapshot_display["Value"] = ratio_snapshot_display.apply(
                    lambda row: format_percent(row["Value"])
                    if row["Metric"] == "FCF Margin %"
                    else format_number(row["Value"]),
                    axis=1,
                )
                render_dashboard_table(ratio_snapshot_display, height=190)

    with targets_tab:
        with st.container(border=True):
            render_section_title(
                f"{int(target_year)} Actuals & Analyst Targets",
                "Reported actuals compared with available analyst annual targets.",
            )
            actual_quarters = actual_quarters_for_target_year(
                quarterly_financial_df,
                annual_financial_df,
                int(target_year),
            )
            reported_quarters = len(actual_quarters)
            revenue_progress = actuals_targets_df.loc[
                actuals_targets_df["Metric"].eq("Revenue"),
                "Progress %",
            ].dropna()
            eps_progress = actuals_targets_df.loc[
                actuals_targets_df["Metric"].eq("Diluted EPS"),
                "Progress %",
            ].dropna()

            render_metric_strip(
                [
                    {
                        "label": "Reported Qtrs",
                        "value": reported_quarters,
                        "context": "actuals loaded",
                    },
                    {
                        "label": "Revenue Prog",
                        "value": format_percent(revenue_progress.iloc[0], 1) if not revenue_progress.empty else "N/A",
                        "context": "vs analyst target",
                        "tone": "good" if not revenue_progress.empty and revenue_progress.iloc[0] >= 75 else "neutral",
                    },
                    {
                        "label": "EPS Prog",
                        "value": format_percent(eps_progress.iloc[0], 1) if not eps_progress.empty else "N/A",
                        "context": "vs analyst target",
                        "tone": "good" if not eps_progress.empty and eps_progress.iloc[0] >= 75 else "neutral",
                    },
                    {
                        "label": "Target Year",
                        "value": str(int(target_year)),
                        "context": "actuals + estimates",
                    },
                ],
                columns=4,
            )

            if actuals_targets_df.empty:
                st.info("No actuals or annual targets were returned for the selected target year.")
            else:
                render_dashboard_table(
                    format_actuals_targets_frame(actuals_targets_df),
                    height=245,
                )

                progress_rows = actuals_targets_df.dropna(subset=["Progress %"])
                if not progress_rows.empty:
                    render_section_title("Progress vs Target", "Percent of analyst annual target achieved.")
                    progress_chart = progress_rows[["Metric", "Progress %"]]
                    render_single_bar_chart(
                        progress_chart,
                        "Metric",
                        "Progress %",
                        "Progress (%)",
                        height=210,
                        color="#49d69b",
                    )

        with st.container(border=True):
            render_section_title(
                f"Q1-Q4 {int(target_year)} Breakout",
                "Quarter-level actuals, targets, variance, and progress.",
            )
            if quarterly_breakout_df.empty:
                st.info("No quarterly actuals or targets were returned for the selected target year.")
            else:
                render_dashboard_table(
                    format_quarterly_breakout_frame(quarterly_breakout_df),
                    height=245,
                )
                breakout_chart = quarterly_breakout_df[
                    ["Quarter", "Revenue Actual", "Revenue Target"]
                ].dropna(how="all")
                if not breakout_chart.empty:
                    render_multi_series_chart(
                        breakout_chart,
                        "Quarter",
                        ["Revenue Actual", "Revenue Target"],
                        "bar",
                        "Revenue ($B)",
                        value_scale=1_000_000_000,
                        height=230,
                    )

        with st.container(border=True):
            render_section_title("Price Target", "Current price and analyst target range.")
            render_dashboard_table(
                format_actuals_targets_frame(price_target_df),
                height=130,
            )
            render_price_target_range(price_target_df)

    with expectations_tab:
        with st.container(border=True):
            render_section_title(
                "Analyst Consensus",
                "Price-target and rating snapshot from the available public market-data provider.",
            )
            st.caption(freshness_caption(financial_meta, "Yahoo Finance/yfinance"))
            consensus_rating = info.get("recommendationKey") or info.get("recommendationMean")
            if isinstance(consensus_rating, str):
                consensus_rating = consensus_rating.replace("_", " ").title()
            else:
                consensus_rating = format_number(consensus_rating, 2)
            analyst_count = info.get("numberOfAnalystOpinions") or info.get("numberOfAnalysts")
            render_metric_strip(
                [
                    {
                        "label": "Consensus",
                        "value": consensus_rating or "N/A",
                        "context": "rating",
                    },
                    {
                        "label": "Avg Target",
                        "value": format_currency(info.get("targetMeanPrice"), 2),
                        "context": "mean estimate",
                    },
                    {
                        "label": "High Target",
                        "value": format_currency(info.get("targetHighPrice"), 2),
                        "context": "analyst high",
                    },
                    {
                        "label": "Low Target",
                        "value": format_currency(info.get("targetLowPrice"), 2),
                        "context": "analyst low",
                    },
                    {
                        "label": "Analysts",
                        "value": format_number(analyst_count, 0),
                        "context": "opinions",
                    },
                    {
                        "label": "Next Earnings",
                        "value": next_earnings.strftime("%Y-%m-%d") if next_earnings else "N/A",
                        "context": "if available",
                    },
                ],
                columns=6,
            )

        with st.container(border=True):
            render_section_title(
                "Analyst EPS Expectations vs Actuals",
                "Last four reported quarters.",
            )
            st.caption(freshness_caption(financial_meta, "Yahoo Finance/yfinance"))
            if earnings_expectations.empty:
                st.info("No analyst expectation history was returned for the last four reported quarters.")
            else:
                beat_count = int((earnings_expectations["Result"] == "Beat").sum())
                avg_surprise = coerce_float(earnings_expectations["Surprise %"].dropna().mean())
                render_metric_strip(
                    [
                        {
                            "label": "Reported Qtrs",
                            "value": len(earnings_expectations),
                            "context": "expectation history",
                        },
                        {
                            "label": "Beats",
                            "value": f"{beat_count}/{len(earnings_expectations)}",
                            "context": "last four quarters",
                            "tone": "good" if beat_count >= 3 else "neutral",
                        },
                        {
                            "label": "Avg Surprise",
                            "value": format_percent(avg_surprise, signed=True),
                            "context": "EPS actual vs est.",
                            "tone": "good" if avg_surprise is not None and avg_surprise >= 0 else "bad",
                        },
                    ],
                    columns=3,
                )

                display_expectations = earnings_expectations.copy()
                display_expectations["Report Date"] = pd.to_datetime(
                    display_expectations["Report Date"],
                    errors="coerce",
                ).dt.strftime("%Y-%m-%d").fillna("N/A")
                for column in ["EPS Estimate", "Reported EPS", "EPS Surprise"]:
                    display_expectations[column] = display_expectations[column].map(
                        lambda value: format_number(value, 2)
                    )
                display_expectations["Surprise %"] = display_expectations["Surprise %"].map(
                    lambda value: format_percent(value, 1, signed=True)
                )
                render_dashboard_table(display_expectations, height=table_height_for_rows(display_expectations, max_height=260))

                chart_expectations = earnings_expectations[["Quarter", "EPS Estimate", "Reported EPS"]].sort_values("Quarter")
                render_multi_series_chart(
                    chart_expectations,
                    "Quarter",
                    ["EPS Estimate", "Reported EPS"],
                    "bar",
                    "EPS ($)",
                    height=220,
                )

        with st.container(border=True):
            render_section_title(
                "Research Reports",
                "Public analyst-related report pages and source links for the selected ticker.",
            )
            st.caption(freshness_caption(financial_meta, "Yahoo Finance/yfinance"))
            render_analyst_reports(analyst_reports, analyst_reports_refreshed)

    with statements_tab:
        with st.container(border=True):
            render_section_title(f"{period} Financial Statement Summary", "Core income, balance sheet, and cash-flow lines.")
            if financial_df.empty:
                st.info("No statement summary available.")
            else:
                statement_df = statement_display_frame(financial_df)
                displayed_periods = len(statement_df)
                if displayed_periods < int(periods_to_show):
                    st.caption(
                        f"Showing {displayed_periods} available {period.lower()} periods. "
                        "Additional historical periods were not returned by the data source."
                    )
                st.caption(
                    f"Periods requested: {int(periods_to_show)} | Periods displayed: {displayed_periods} | "
                    + freshness_caption(financial_meta, "Yahoo Finance/yfinance")
                )
                display_df = statement_df.drop(columns=["Period Date"], errors="ignore")
                currency_columns = [
                    column
                    for column in display_df.columns
                    if column not in {"Period", "Diluted EPS"}
                ]
                number_columns = ["Diluted EPS"] if "Diluted EPS" in display_df.columns else []
                render_dashboard_table(
                    format_financial_table(
                        display_df,
                        currency_columns=currency_columns,
                        number_columns=number_columns,
                    ),
                    height=table_height_for_rows(display_df),
                )
                st.download_button(
                    "Download statement summary",
                    display_df.to_csv(index=False),
                    file_name=f"{ticker.lower()}_financial_summary.csv",
                    mime="text/csv",
                )

    with ratios_tab:
        left_col, right_col = st.columns([1, 1], gap="small")
        with left_col:
            with st.container(border=True):
                render_section_title("Profitability Margins", f"{period} margin trend")
                margin_cols = [
                    column
                    for column in ["Gross Margin %", "Operating Margin %", "Net Margin %", "FCF Margin %"]
                    if column in ratios and ratios[column].notna().any()
                ]
                if margin_cols:
                    render_multi_series_chart(
                        ratios,
                        "Period",
                        margin_cols,
                        "line",
                        "Margin (%)",
                        height=240,
                    )
                else:
                    st.info("Margin data is unavailable for the selected statement period.")

        with right_col:
            with st.container(border=True):
                render_section_title("Cash Flow", f"{period} cash-flow trend")
                cash_cols = [
                    column
                    for column in ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"]
                    if column in financial_df and financial_df[column].notna().any()
                ]
                if cash_cols:
                    render_multi_series_chart(
                        financial_df,
                        "Period",
                        cash_cols,
                        "bar",
                        "Cash Flow ($B)",
                        value_scale=1_000_000_000,
                        height=240,
                    )
                else:
                    st.info("Cash-flow data is unavailable for the selected statement period.")

        with st.container(border=True):
            render_section_title("Ratio Table", "Period-by-period ratio summary")
            ratio_display = format_financial_table(
                ratios,
                percent_columns=["Gross Margin %", "Operating Margin %", "Net Margin %", "FCF Margin %"],
                number_columns=["Current Ratio", "Debt / Equity", "Cash / Debt", "Asset Turnover"],
            )
            render_dashboard_table(ratio_display, height=300)

    with valuation_tab:
        valuation_df = pd.DataFrame(
            [
                {"Metric": "Market Cap", "Value": metrics.get("Market Cap")},
                {"Metric": "Enterprise Value", "Value": metrics.get("Enterprise Value")},
                {"Metric": "Trailing PE", "Value": metrics.get("Trailing PE")},
                {"Metric": "Forward PE", "Value": metrics.get("Forward PE")},
                {"Metric": "Price / Sales", "Value": metrics.get("Price / Sales")},
                {"Metric": "EV / EBITDA", "Value": metrics.get("EV / EBITDA")},
                {"Metric": "Dividend Yield %", "Value": metrics.get("Dividend Yield %")},
            ]
        )
        with st.container(border=True):
            render_section_title("Valuation Snapshot", "Market value and key trading multiples")
            valuation_display = valuation_df.copy()
            currency_metrics = {"Market Cap", "Enterprise Value"}
            percent_metrics = {"Dividend Yield %"}
            valuation_display["Value"] = valuation_display.apply(
                lambda row: format_compact_currency(row["Value"], 2)
                if row["Metric"] in currency_metrics
                else format_percent(row["Value"])
                if row["Metric"] in percent_metrics
                else format_number(row["Value"]),
                axis=1,
            )
            render_dashboard_table(valuation_display, height=280)

        history = payload.get("history", empty_history())
        if history is not None and not history.empty and "Close" in history:
            with st.container(border=True):
                render_section_title("One-Year Price", "Daily close from available history")
                history_frame = pd.DataFrame(
                    {"Stock Price": pd.to_numeric(history["Close"], errors="coerce").dropna()}
                )
                render_time_series_chart(
                    history_frame,
                    "Stock Price",
                    "Stock Price ($)",
                    height=240,
                    color="#5ec7e8",
                )

    with raw_tab:
        if not show_raw_statements:
            st.info("Enable 'Show raw statements' in the sidebar to inspect full statement tables.")
        else:
            with st.container(border=True):
                render_section_title("Income Statement", "Raw source matrix")
                render_dashboard_table(format_statement_matrix(income), hide_index=False, height=360)
            with st.container(border=True):
                render_section_title("Balance Sheet", "Raw source matrix")
                render_dashboard_table(format_statement_matrix(balance), hide_index=False, height=360)
            with st.container(border=True):
                render_section_title("Cash Flow", "Raw source matrix")
                render_dashboard_table(format_statement_matrix(cashflow), hide_index=False, height=360)


def main() -> None:
    st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")
    inject_css()
    refresh_config = render_global_refresh_controls()
    st.sidebar.divider()
    page = st.sidebar.radio(
        "Tabs",
        ["Home", "Stock Due Diligence", "Volatility Radar", "3-Statement Analysis"],
        index=0,
        key="main_tab",
    )
    st.sidebar.divider()
    render_global_live_status_strip(page, refresh_config)
    if refresh_config.get("show_provider_debug"):
        render_provider_strategy_debug()

    if page == "Home":
        render_home_dashboard()
    elif page == "Stock Due Diligence":
        render_home_financials()
    elif page == "3-Statement Analysis":
        render_three_statement_analysis_dashboard()
    else:
        render_volatility_radar()


if __name__ == "__main__":
    main()
