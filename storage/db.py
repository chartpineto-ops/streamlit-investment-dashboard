from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DB_PATH = Path(os.getenv("RESEARCH_TERMINAL_DB", "research_terminal.db"))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                added_at TEXT NOT NULL,
                category TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                composite_score REAL,
                signal_label TEXT,
                confidence TEXT,
                growth_score REAL,
                profitability_score REAL,
                balance_sheet_score REAL,
                valuation_score REAL,
                momentum_score REAL,
                catalyst_score REAL,
                key_strengths TEXT,
                key_weaknesses TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                alert_message TEXT NOT NULL,
                dismissed INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
