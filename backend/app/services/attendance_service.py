import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.attendance import AttendanceLog
from app.core.config import settings

# Default work start time — late if check-in is after this
WORK_START_HOUR = 9
WORK_START_MINUTE = 0


async def mark_attendance(
    db: AsyncSession,
    user_id: int,
    confidence: float | None = None,
    camera_id: int | None = None,
    source: str = "camera",
) -> AttendanceLog | None:
    """
    Mark attendance for a user. Idempotent — one check-in per user per day.
    Returns the created log or None if already marked today.
    """
    today = datetime.date.today()
    existing = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.user_id == user_id, AttendanceLog.date == today)
        )
    )
    if existing.scalar_one_or_none():
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
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
    return log


async def mark_checkout(
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
