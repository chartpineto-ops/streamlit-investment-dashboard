from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Iterable


OFFICIAL_RELEASE_ACTUALS: dict[str, dict[str, object]] = {
    "ISM Manufacturing PMI (May)": {
        "actual": "54.0",
        "estimate": "53.3",
        "previous": "52.7",
        "status": "Released",
        "source_label": "ISM",
        "source_url": "https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/pmi/irun202605pmi.pdf",
        "data_mode": "Official actual",
        "release_note": "May Manufacturing PMI rose to 54.0 from 52.7.",
    },
    "JOLTS Job Openings (Apr)": {
        "actual": "7.6M",
        "estimate": "6.8M",
        "previous": "6.9M",
        "status": "Released",
        "source_label": "BLS",
        "source_url": "https://www.bls.gov/news.release/jolts.nr0.htm",
        "data_mode": "Official actual",
        "release_note": "April job openings increased to 7.6M.",
    },
    "ISM Services PMI (May)": {
        "actual": "54.5",
        "estimate": "53.8",
        "previous": "53.6",
        "status": "Released",
        "source_label": "ISM",
        "source_url": "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/services/may/",
        "data_mode": "Official actual",
        "release_note": "Services PMI expanded to 54.5 in May.",
    },
    "Initial Jobless Claims": {
        "actual": "225K",
        "estimate": "233K",
        "previous": "212K",
        "status": "Released",
        "source_label": "DOL",
        "source_url": "https://www.dol.gov/ui/data.pdf",
        "data_mode": "Official actual",
        "release_note": "Week ended May 30; previous week revised to 212K.",
    },
    "Employment Situation / Nonfarm Payrolls (May)": {
        "actual": "+172K",
        "estimate": "+77K",
        "previous": "+179K",
        "status": "Released",
        "source_label": "BLS",
        "source_url": "https://www.bls.gov/news.release/archives/empsit_06052026.htm",
        "data_mode": "Official actual",
        "release_note": "May payrolls increased by 172K; April revised to 179K.",
    },
    "Unemployment Rate (May)": {
        "actual": "4.3%",
        "estimate": "4.3%",
        "previous": "4.3%",
        "status": "Released",
        "source_label": "BLS",
        "source_url": "https://www.bls.gov/news.release/archives/empsit_06052026.htm",
        "data_mode": "Official actual",
        "release_note": "Unemployment rate was unchanged at 4.3%.",
    },
}


def _event_date(row: dict[str, object]) -> date | None:
    try:
        return datetime.strptime(str(row.get("date", "")), "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_pending(value: object) -> bool:
    return str(value or "").strip().casefold() in {"", "pending", "tbd", "n/a"}


def enrich_economic_calendar_events(
    events: Iterable[dict[str, object]],
    *,
    current_date: date | None = None,
    refresh_token: int | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Return calendar rows with released official actuals overlaid.

    ``refresh_token`` is intentionally accepted so Streamlit reruns can bust any
    upstream cache without changing the public call shape.
    """
    del refresh_token
    as_of = current_date or date.today()
    rows = deepcopy(list(events))
    updated = 0

    for row in rows:
        event_day = _event_date(row)
        official = OFFICIAL_RELEASE_ACTUALS.get(str(row.get("event", "")))
        if not event_day or not official or event_day > as_of:
            continue
        was_pending = _is_pending(row.get("actual")) or str(row.get("status", "")).casefold() != "released"
        row.update(official)
        row["last_updated"] = "2026-06-05 08:30 ET"
        if was_pending:
            updated += 1

    released = sum(1 for row in rows if str(row.get("status", "")).casefold() == "released")
    pending = sum(1 for row in rows if _is_pending(row.get("actual")))
    return rows, {
        "released_count": released,
        "pending_count": pending,
        "updated_count": updated,
        "last_updated": "2026-06-05 08:30 ET",
        "data_mode": "Official-source actuals",
    }
