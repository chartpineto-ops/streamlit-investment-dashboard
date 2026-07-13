from __future__ import annotations

import pandas as pd

import services.economic_data_service as economic
from services.macro_alert_service import _recent_official_release, _release_changed


BLS_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20260610T083000
SUMMARY:Consumer Price Index
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20260714T083000
SUMMARY:Real Earnings
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20260714T083000
SUMMARY:Consumer Price Index
END:VEVENT
END:VCALENDAR
"""


def test_bls_calendar_preserves_official_release_time() -> None:
    calendar = economic._parse_bls_calendar(BLS_ICS)
    cpi = calendar[calendar["release_name"] == "Consumer Price Index"].sort_values("release_at")
    assert len(cpi) == 2
    assert cpi.iloc[-1]["release_at"].isoformat() == "2026-07-14T08:30:00-04:00"


def test_cpi_observation_is_not_mislabeled_as_refresh_date() -> None:
    calendar = economic._parse_bls_calendar(BLS_ICS)
    observations = pd.DataFrame(
        [
            {"observation_date": pd.Timestamp("2026-05-01"), "observation_period": "May 2026", "value": 333.979},
            {"observation_date": pd.Timestamp("2026-04-01"), "observation_period": "April 2026", "value": 332.407},
        ]
    )
    current = pd.Timestamp("2026-07-13T14:00:00", tz="America/New_York")
    row = economic._build_row(
        "CUSR0000SA0",
        economic.BLS_SERIES["CUSR0000SA0"],
        observations,
        calendar,
        "BLS Public Data API",
        current,
    )
    assert row is not None
    assert row["observation_period"] == "May 2026"
    assert pd.Timestamp(row["official_release_at"]).isoformat() == "2026-06-10T08:30:00-04:00"
    assert pd.Timestamp(row["next_release_at"]).isoformat() == "2026-07-14T08:30:00-04:00"
    assert row["official_release_at"] != row["last_refresh"]
    assert row["audit_status"] == "VERIFIED"


def test_future_release_is_blocked() -> None:
    current = pd.Timestamp("2026-07-13T14:00:00", tz="America/New_York")
    status, message = economic._audit_row(
        {
            "value": 335.0,
            "observation_date": "2026-06-01",
            "official_release_at": "2026-07-14T08:30:00-04:00",
            "frequency": "Monthly",
            "source_url": "https://www.bls.gov/cpi/",
        },
        current,
    )
    assert status == "BLOCKED"
    assert "scheduled" in message.casefold() or "embargoed" in message.casefold()


def test_old_cpi_period_is_not_retimestamped_after_new_release() -> None:
    calendar = economic._parse_bls_calendar(BLS_ICS)
    observations = pd.DataFrame(
        [
            {"observation_date": pd.Timestamp("2026-05-01"), "observation_period": "May 2026", "value": 333.979},
            {"observation_date": pd.Timestamp("2026-04-01"), "observation_period": "April 2026", "value": 332.407},
        ]
    )
    row = economic._build_row(
        "CUSR0000SA0",
        economic.BLS_SERIES["CUSR0000SA0"],
        observations,
        calendar,
        "BLS Public Data API",
        pd.Timestamp("2026-07-14T08:31:00", tz="America/New_York"),
    )

    assert row is not None
    assert pd.Timestamp(row["official_release_at"]).isoformat() == "2026-06-10T08:30:00-04:00"
    assert row["audit_status"] == "REVIEW"
    assert "prior observation" in str(row["audit_message"])


def test_next_release_prefers_cpi_over_same_time_real_earnings() -> None:
    calendar = economic._parse_bls_calendar(BLS_ICS)
    release = economic.next_scheduled_macro_release(
        calendar,
        pd.Timestamp("2026-07-13T14:00:00", tz="America/New_York"),
    )
    assert release["release_name"] == "Consumer Price Index"


def test_release_window_accelerates_without_claiming_continuous_realtime(monkeypatch) -> None:
    calendar = economic._parse_bls_calendar(BLS_ICS)
    monkeypatch.setattr(economic, "secret_or_env", lambda *args, **kwargs: "")
    cadence = economic.macro_poll_interval_seconds(
        calendar,
        pd.Timestamp("2026-07-14T08:29:30", tz="America/New_York"),
    )
    assert cadence == 60

    wakeup = economic.macro_poll_interval_seconds(
        calendar,
        pd.Timestamp("2026-07-14T08:20:00", tz="America/New_York"),
    )
    assert wakeup == 300


def test_failed_primary_cache_uses_short_retry_bucket(monkeypatch) -> None:
    empty = economic._empty_macro()
    verified = pd.DataFrame(
        [
            {"series_id": series_id, "audit_status": "VERIFIED"}
            for series_id in economic.BLS_SERIES
        ]
    )
    calls: list[int] = []

    def cached(bucket: int) -> pd.DataFrame:
        calls.append(bucket)
        return empty if len(calls) == 1 else verified

    monkeypatch.setattr(economic, "macro_poll_interval_seconds", lambda: 21_600)
    monkeypatch.setattr(economic, "_fetch_macro_dashboard_cached", cached)
    result = economic.fetch_macro_dashboard()

    assert len(calls) == 2
    assert calls[1] < 0
    assert len(result) == len(economic.BLS_SERIES)


def test_macro_alert_requires_a_new_period_or_revision() -> None:
    prior = {"observation_period": "May 2026", "value": 333.979}
    assert not _release_changed(prior, {"observation_period": "May 2026", "value": 333.979})
    assert _release_changed(prior, {"observation_period": "June 2026", "value": 335.1})
    assert _release_changed(prior, {"observation_period": "May 2026", "value": 333.981})


def test_new_monitor_instance_alerts_on_just_released_data() -> None:
    row = {"official_release_at": "2026-07-14T08:30:00-04:00"}
    assert _recent_official_release(row, "2026-07-14T08:35:00-04:00")
    assert not _recent_official_release(row, "2026-07-14T09:00:00-04:00")
