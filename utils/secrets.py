from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def _secrets_file_available() -> bool:
    candidates = (
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    )
    return any(path.is_file() for path in candidates)


def secret_or_env(name: str, *, section: str | None = None, default: str = "") -> str:
    value = str(os.getenv(name, "")).strip()
    if value:
        return value
    if not _secrets_file_available():
        return default
    try:
        secrets = st.secrets
        value = secrets.get(name, "")
        if not value and section:
            group = secrets.get(section, {})
            value = group.get(name, "") if hasattr(group, "get") else ""
    except Exception:
        return default
    return str(value or default).strip()
