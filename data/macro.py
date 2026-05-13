from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.formatting import now_et


@st.cache_data(ttl=21_600, show_spinner=False)
def fetch_macro_catalysts() -> tuple[pd.DataFrame, dict]:
    rows = [
        {"Theme": "Rates", "Catalyst": "Fed speakers, Treasury auctions, and inflation prints", "Status": "Monitor"},
        {"Theme": "Inflation", "Catalyst": "CPI/PPI releases can shift equity duration and growth multiples", "Status": "Monitor"},
        {"Theme": "Jobs", "Catalyst": "Payrolls and claims data can move rates and cyclicals", "Status": "Monitor"},
    ]
    return pd.DataFrame(rows), {"Source": "Static V1 macro checklist", "Status": "OK", "Last Updated": now_et(), "Error": ""}

