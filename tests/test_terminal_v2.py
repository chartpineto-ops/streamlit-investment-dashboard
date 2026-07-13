from __future__ import annotations

import pandas as pd

from terminal_v2.integrity import classify_frame, provider_health
from terminal_v2.main import _parse_command
from terminal_v2.views import _return_pct, _social_readthrough


def test_terminal_commands_open_workspaces_and_tickers() -> None:
    assert _parse_command("DATA <GO>") == ("DATA", None, "")
    assert _parse_command("SEC NVDA") == ("SECURITY", "NVDA", "")
    assert _parse_command("MRVL") == ("SECURITY", "MRVL", "")


def test_provider_registry_never_calls_unwired_feeds_live() -> None:
    health = provider_health()
    polygon = health[health["feed"] == "Consolidated trade feed"].iloc[0]
    social = health[health["domain"] == "Social"].iloc[0]
    assert "Live" not in str(polygon["status"])
    assert "Live" not in str(social["status"])


def test_frame_classification_preserves_demo_and_delayed_labels() -> None:
    assert classify_frame(pd.DataFrame({"data_source": ["Provider not configured - demo news fallback"]})) == "Demo"
    assert classify_frame(pd.DataFrame({"data_source": ["Yahoo Finance delayed fallback"]})) == "Delayed"


def test_valuation_return_formatter_accepts_fraction_or_percent() -> None:
    assert _return_pct(0.125) == "+12.5%"
    assert _return_pct(12.5) == "+12.5%"
    assert _return_pct(-0.31) == "-31.0%"


def test_social_readthrough_is_honest_when_missing() -> None:
    assert "No reliable social data available" in _social_readthrough(pd.DataFrame())
