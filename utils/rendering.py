from __future__ import annotations

from html import escape as _escape
import textwrap
from typing import Any

import streamlit as st


def render_html(markup: Any) -> None:
    """Render trusted internal UI HTML with the strongest Streamlit renderer available."""

    if markup is None:
        return
    if not isinstance(markup, str):
        markup = str(markup)

    compact_markup = textwrap.dedent(markup).strip()
    if not compact_markup:
        return

    if hasattr(st, "html"):
        st.html(compact_markup)
    else:
        st.markdown(compact_markup, unsafe_allow_html=True)


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return _escape(str(value))
