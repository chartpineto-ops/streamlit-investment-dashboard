from __future__ import annotations

import pandas as pd
import streamlit as st

from data.market_data import fetch_quote
from data.market_universe import SOCIAL_MOMENTUM_UNIVERSE
from utils.formatting import now_et, to_float


@st.cache_data(ttl=900, show_spinner=False)
def fetch_social_momentum_names() -> tuple[pd.DataFrame, dict]:
    rows = []
    for rank, symbol in enumerate(SOCIAL_MOMENTUM_UNIVERSE, start=1):
        quote = fetch_quote(symbol)
        rows.append(
            {
                "Ticker": symbol,
                "Company": quote.get("company_name") or symbol,
                "Social Rank / Trending Rank": rank,
                "Message Volume": None,
                "Sentiment": "N/A",
                "Price": quote.get("price"),
                "Daily Move %": to_float(quote.get("daily_change_pct")),
                "Watchlist Status": "Candidate",
                "Link": f"https://stocktwits.com/symbol/{symbol}",
            }
        )
    status = {
        "Source": "Fallback social momentum universe",
        "Status": "Fallback",
        "Last Updated": now_et(),
        "Error": "Stocktwits trending data unavailable from current free sources. Showing curated social momentum universe.",
    }
    return pd.DataFrame(rows), status
