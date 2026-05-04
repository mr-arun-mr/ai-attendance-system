import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.attendance import AttendanceLog

# Default work start time — late if check-in is after this
WORK_START_HOUR = 9
WORK_START_MINUTE = 0

# Minimum time that must pass after check-in before the next face recognition
# triggers a check-out instead of being ignored. This prevents a person
# walking past the camera twice in quick succession from being checked out.
MIN_CHECKOUT_GAP_MINUTES = 60


async def mark_attendance(
    db: AsyncSession,
    user_id: int,
    confidence: float | None = None,
    camera_id: int | None = None,
    source: str = "camera",
) -> tuple[AttendanceLog | None, str]:
    """
    Smart check-in / check-out logic.

    Returns (log, status) where status is one of:
      "checked_in"   – new check-in created
      "checked_out"  – existing log updated with check-out time
      "already_done" – log fully complete (both times recorded), nothing changed
      "too_soon"     – check-in exists but not enough time has passed to check out

    Rules:
      1. No log today          → create check-in
      2. Log exists, no c/out, AND time_since_checkin >= MIN_CHECKOUT_GAP_MINUTES → check-out
      3. Log exists, no c/out, time too short → return "too_soon" (person still in building)
      4. Log exists with c/out → return "already_done"
    """
    today = datetime.date.today()
    result = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.user_id == user_id, AttendanceLog.date == today)
        )
    )
    existing = result.scalar_one_or_none()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Rule 1 — first recognition today → check-in
    if existing is None:
        local_now = now.astimezone()
        is_late = (local_now.hour, local_now.minute) > (WORK_START_HOUR, WORK_START_MINUTE)
        log = AttendanceLog(
            user_id=user_id,
            check_in=now,
            date=today,
            confidence=confidence,
            source=source,
            camera_id=camera_id,
            is_late=is_late,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log, "checked_in"

    # Rule 4 — already fully logged
    if existing.check_out is not None:
        return existing, "already_done"

    # Rules 2 & 3 — check-in exists, no check-out yet
    elapsed = (now - existing.check_in).total_seconds() / 60  # minutes
    if elapsed >= MIN_CHECKOUT_GAP_MINUTES:
        existing.check_out = now
        await db.commit()
        await db.refresh(existing)
        return existing, "checked_out"

    return existing, "too_soon"


async def manual_checkout(
    db: AsyncSession, user_id: int
) -> AttendanceLog | None:
    today = datetime.date.today()
    result = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.user_id == user_id, AttendanceLog.date == today)
        )
    )
    log = result.scalar_one_or_none()
    if log and not log.check_out:
        log.check_out = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(log)
    return log
