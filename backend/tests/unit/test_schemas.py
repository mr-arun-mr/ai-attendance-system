"""Unit tests for Pydantic schema computed fields."""
import datetime

import pytest

from app.schemas.attendance import AttendanceOut


def _make_log(check_in, check_out=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    return AttendanceOut(
        id=1,
        user_id=1,
        full_name="Alice",
        employee_id="EMP001",
        department="Engineering",
        check_in=check_in,
        check_out=check_out,
        date=datetime.date.today(),
        confidence=0.95,
        source="camera",
        is_late=False,
    )


class TestAttendanceOutDuration:
    def test_duration_is_none_when_no_checkout(self):
        log = _make_log(datetime.datetime.now(datetime.timezone.utc))
        assert log.duration_minutes is None

    def test_duration_calculated_correctly(self):
        base = datetime.datetime(2024, 1, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        checkout = base + datetime.timedelta(hours=8, minutes=30)
        log = _make_log(base, checkout)
        assert log.duration_minutes == 8 * 60 + 30

    def test_duration_minimum_is_zero(self):
        # check_out before check_in (data anomaly) should clamp to 0
        base = datetime.datetime(2024, 1, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        log = _make_log(base, base - datetime.timedelta(minutes=5))
        assert log.duration_minutes == 0

    def test_duration_zero_for_same_time(self):
        t = datetime.datetime.now(datetime.timezone.utc)
        log = _make_log(t, t)
        assert log.duration_minutes == 0

    def test_duration_one_minute(self):
        base = datetime.datetime(2024, 1, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        log = _make_log(base, base + datetime.timedelta(minutes=1))
        assert log.duration_minutes == 1

    def test_duration_truncates_to_minutes(self):
        base = datetime.datetime(2024, 1, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        # 90 seconds = 1 minute (truncated, not rounded)
        log = _make_log(base, base + datetime.timedelta(seconds=90))
        assert log.duration_minutes == 1
