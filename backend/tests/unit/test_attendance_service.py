"""
Unit tests for attendance_service business logic using mocked DB sessions.

We use AsyncMock to simulate SQLAlchemy execute() results so we can test
all four state-machine branches of mark_attendance without a real database.
"""
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.attendance_service import (
    MIN_CHECKOUT_GAP_MINUTES,
    WORK_START_HOUR,
    WORK_START_MINUTE,
    mark_attendance,
    manual_checkout,
)
from app.models.attendance import AttendanceLog


def _make_log(check_in, check_out=None, user_id=1):
    log = MagicMock(spec=AttendanceLog)
    log.user_id = user_id
    log.check_in = check_in
    log.check_out = check_out
    log.date = check_in.date()
    log.is_late = False
    return log


def _mock_db(existing_log=None):
    """Build an AsyncMock DB session that returns *existing_log* on execute."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_log
    db.execute.return_value = result
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


class TestMarkAttendanceCheckin:
    async def test_creates_new_log_when_none_exists(self):
        db = _mock_db(existing_log=None)
        log, status = await mark_attendance(db, user_id=1, confidence=0.9)
        assert status == "checked_in"
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_sets_is_late_false_for_early_arrival(self):
        db = _mock_db(existing_log=None)
        # Patch datetime.date.today and datetime.datetime.now to an on-time moment
        early = datetime.datetime(2024, 5, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
        with patch("app.services.attendance_service.datetime") as mock_dt:
            mock_dt.date.today.return_value = early.date()
            mock_dt.datetime.now.return_value = early
            mock_dt.timezone.utc = datetime.timezone.utc
            # early.astimezone() needs a real datetime for is_late check
            early_local = MagicMock()
            early_local.hour = WORK_START_HOUR - 1
            early_local.minute = 0
            mock_dt.datetime.now.return_value.astimezone.return_value = early_local

            log, status = await mark_attendance(db, user_id=1)
        assert status == "checked_in"

    async def test_sets_source_and_camera_id(self):
        db = _mock_db(existing_log=None)
        captured_log = {}

        def capture_add(obj):
            captured_log["obj"] = obj

        db.add = capture_add
        await mark_attendance(db, user_id=5, confidence=0.8, camera_id=3, source="camera")
        assert captured_log["obj"].user_id == 5
        assert captured_log["obj"].camera_id == 3
        assert captured_log["obj"].source == "camera"
        assert captured_log["obj"].confidence == 0.8


class TestMarkAttendanceCheckout:
    async def test_already_done_when_both_times_set(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        existing = _make_log(check_in=now - datetime.timedelta(hours=9), check_out=now)
        db = _mock_db(existing_log=existing)
        log, status = await mark_attendance(db, user_id=1)
        assert status == "already_done"
        db.add.assert_not_called()

    async def test_too_soon_when_gap_is_under_threshold(self):
        recent_checkin = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            minutes=MIN_CHECKOUT_GAP_MINUTES - 1
        )
        existing = _make_log(check_in=recent_checkin)
        db = _mock_db(existing_log=existing)
        log, status = await mark_attendance(db, user_id=1)
        assert status == "too_soon"
        db.commit.assert_not_awaited()

    async def test_checked_out_when_gap_exceeds_threshold(self):
        old_checkin = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            minutes=MIN_CHECKOUT_GAP_MINUTES + 1
        )
        existing = _make_log(check_in=old_checkin)
        db = _mock_db(existing_log=existing)
        log, status = await mark_attendance(db, user_id=1)
        assert status == "checked_out"
        assert existing.check_out is not None
        db.commit.assert_awaited_once()


class TestManualCheckout:
    async def test_sets_checkout_when_open_login_exists(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        existing = _make_log(check_in=now - datetime.timedelta(hours=4))
        db = _mock_db(existing_log=existing)
        result = await manual_checkout(db, user_id=1)
        assert existing.check_out is not None
        db.commit.assert_awaited_once()

    async def test_returns_none_when_no_log_today(self):
        db = _mock_db(existing_log=None)
        result = await manual_checkout(db, user_id=1)
        assert result is None
        db.commit.assert_not_awaited()

    async def test_does_not_overwrite_existing_checkout(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        checkout_time = now - datetime.timedelta(hours=1)
        existing = _make_log(
            check_in=now - datetime.timedelta(hours=8),
            check_out=checkout_time,
        )
        db = _mock_db(existing_log=existing)
        await manual_checkout(db, user_id=1)
        # check_out should remain unchanged
        assert existing.check_out == checkout_time
        db.commit.assert_not_awaited()
