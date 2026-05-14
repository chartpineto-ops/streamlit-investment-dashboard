from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from zoneinfo import ZoneInfo

import pandas as pd

EASTERN = ZoneInfo("America/New_York")
DEFAULT_TZ = "America/New_York"
DATE_NORMALIZATION_WARNINGS: list[dict] = []


def now_et() -> datetime:
    return datetime.now(EASTERN)


def _is_nullish(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.upper() in {"N/A", "NA", "NONE", "NAN", "NAT", "NULL", "-", "--"}:
            return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _strip_display_timezone_label(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    upper = text.upper()
    for suffix in (" ET", " EST", " EDT"):
        if upper.endswith(suffix):
            return text[: -len(suffix)].strip()
    return value


def _record_date_warning(value, error: Exception | str, field: str | None = None, ticker: str | None = None) -> None:
    DATE_NORMALIZATION_WARNINGS.append(
        {
            "field": field or "unknown",
            "ticker": ticker or "",
            "value": str(value)[:120],
            "error": str(error)[:240],
            "timestamp": now_et(),
        }
    )
    del DATE_NORMALIZATION_WARNINGS[:-25]


def normalize_timestamp(value, default_tz: str = DEFAULT_TZ, field: str | None = None, ticker: str | None = None) -> pd.Timestamp | None:
    if _is_nullish(value):
        return None
    try:
        ts = pd.Timestamp(_strip_display_timezone_label(value))
        if pd.isna(ts):
            return None
        tz = ZoneInfo(default_tz)
        if ts.tz is None:
            return ts.tz_localize(tz)
        return ts.tz_convert(tz)
    except Exception as exc:
        _record_date_warning(value, exc, field=field, ticker=ticker)
        return None


def safe_to_datetime(value, default_tz: str = DEFAULT_TZ, field: str | None = None, ticker: str | None = None) -> pd.Timestamp | None:
    return normalize_timestamp(value, default_tz=default_tz, field=field, ticker=ticker)


def _safe_raw_timestamp(value, field: str | None = None, ticker: str | None = None) -> pd.Timestamp | None:
    if _is_nullish(value):
        return None
    try:
        parsed = pd.to_datetime(_strip_display_timezone_label(value), errors="coerce")
        if pd.isna(parsed):
            return None
        return pd.Timestamp(parsed)
    except Exception as exc:
        _record_date_warning(value, exc, field=field, ticker=ticker)
        return None


def _is_midnight(ts: pd.Timestamp) -> bool:
    return ts.hour == 0 and ts.minute == 0 and ts.second == 0 and ts.microsecond == 0 and ts.nanosecond == 0


def safe_format_date(value, field: str | None = None, ticker: str | None = None) -> str:
    ts = _safe_raw_timestamp(value, field=field, ticker=ticker)
    if ts is None:
        return "N/A"
    return ts.strftime("%m/%d/%Y").lstrip("0")


def safe_format_datetime(value, default_tz: str = DEFAULT_TZ, field: str | None = None, ticker: str | None = None) -> str:
    ts = normalize_timestamp(value, default_tz=default_tz, field=field, ticker=ticker)
    if ts is None:
        return "N/A"
    return ts.strftime("%m/%d/%Y %I:%M %p ET").lstrip("0")


def get_date_normalization_status() -> dict:
    latest = DATE_NORMALIZATION_WARNINGS[-1] if DATE_NORMALIZATION_WARNINGS else {}
    return {
        "Source": "Date/time normalization",
        "Status": "Partial" if DATE_NORMALIZATION_WARNINGS else "OK",
        "Last Updated": now_et(),
        "Error": latest.get("error", ""),
        "Affected Field": latest.get("field", ""),
        "Ticker": latest.get("ticker", ""),
    }


def to_float(value) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        number = float(value)
        return number if isfinite(number) else None
    except Exception:
        return None


def is_missing(value) -> bool:
    return to_float(value) is None if not isinstance(value, str) else value.strip() in {"", "N/A", "NM", "None", "nan"}


def clean_ticker(value: str | None) -> str:
    text = str(value or "").strip().upper()
    return "".join(ch for ch in text if ch.isalnum() or ch in ".-^")[:16]


def fmt_number(value, decimals: int = 1) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    return f"{number:,.{decimals}f}"


def fmt_compact(value, decimals: int = 1, prefix: str = "") -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    sign = "-" if number < 0 else ""
    abs_value = abs(number)
    for unit, divisor in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs_value >= divisor:
            return f"{sign}{prefix}{abs_value / divisor:,.{decimals}f}{unit}"
    return f"{sign}{prefix}{abs_value:,.{decimals}f}"


def fmt_currency(value, decimals: int = 2) -> str:
    return fmt_compact(value, decimals=decimals, prefix="$")


def fmt_price(value) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    return f"${number:,.2f}"


def fmt_percent(value, decimals: int = 1, signed: bool = False) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:,.{decimals}f}%"


def fmt_daily_move(value) -> str:
    return fmt_percent(value, decimals=2, signed=True)


def fmt_bps(value, signed: bool = True) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:,.0f} bps"


def fmt_meaningful_percent(value, decimals: int = 1, signed: bool = False, nm_threshold: float = 300) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if abs(number) > nm_threshold:
        return "NM"
    return fmt_percent(number, decimals=decimals, signed=signed)


def fmt_growth(value, base_effect: bool = False, signed: bool = True) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    if base_effect or abs(number) > 500:
        return "NM / base effect"
    return fmt_percent(number, signed=signed)


def fmt_multiple(value) -> str:
    number = to_float(value)
    if number is None or number <= 0:
        return "NM" if number is not None else "N/A"
    return f"{number:,.1f}x"


def fmt_eps(value, signed: bool = False) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    prefix = "+" if signed and number > 0 else "-" if number < 0 else ""
    return f"{prefix}${abs(number):,.2f}"


def fmt_date(value) -> str:
    if _is_nullish(value):
        return "N/A"
    if isinstance(value, date) and not isinstance(value, datetime):
        return safe_format_date(value)
    raw = _safe_raw_timestamp(value)
    if raw is None:
        return "N/A"
    if _is_midnight(raw):
        return safe_format_date(value)
    return safe_format_datetime(value)


def safe_div(numerator, denominator, multiplier: float = 1.0) -> float | None:
    top = to_float(numerator)
    bottom = to_float(denominator)
    if top is None or bottom in (None, 0):
        return None
    return top / bottom * multiplier


def tone_for_number(value) -> str:
    number = to_float(value)
    if number is None or abs(number) < 1e-9:
        return "neutral"
    return "good" if number > 0 else "bad"


def as_percent_from_ratio(value) -> float | None:
    number = to_float(value)
    if number is None:
        return None
    return number * 100 if abs(number) <= 2 else number
