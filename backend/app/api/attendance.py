import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.face_embedding import FaceEmbedding
from app.models.department import Department
from app.schemas.attendance import (
    AttendanceOut, AttendanceManualCreate, AttendanceUpdate,
    DailySummary, UserTimeSummary,
)
from app.api.deps import get_current_user, require_admin
from app.services.face_service import extract_embedding, match_embedding
from app.services.attendance_service import mark_attendance, manual_checkout

router = APIRouter(prefix="/attendance", tags=["attendance"])


async def _load_user_with_dept(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    if user.department_id:
        dept_r = await db.execute(select(Department).where(Department.id == user.department_id))
        user.department = dept_r.scalar_one_or_none()
    else:
        user.department = None
    return user


def _build_out(log: AttendanceLog, user: User) -> AttendanceOut:
    return AttendanceOut(
        id=log.id,
        user_id=log.user_id,
        full_name=user.full_name,
        employee_id=user.employee_id,
        department=user.department.name if user.department else None,
        check_in=log.check_in,
        check_out=log.check_out,
        date=log.date,
        confidence=log.confidence,
        source=log.source,
        is_late=log.is_late,
    )


@router.get("/", response_model=List[AttendanceOut])
async def list_attendance(
    date: Optional[datetime.date] = None,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(AttendanceLog).join(User, AttendanceLog.user_id == User.id)
    if date:
        q = q.where(AttendanceLog.date == date)
    if user_id:
        q = q.where(AttendanceLog.user_id == user_id)
    if department_id:
        q = q.where(User.department_id == department_id)
    q = q.order_by(AttendanceLog.check_in.desc()).limit(limit).offset(offset)

    result = await db.execute(q)
    logs = result.scalars().all()
    out = []
    for log in logs:
        user = await _load_user_with_dept(db, log.user_id)
        out.append(_build_out(log, user))
    return out


@router.post("/mark-photo", summary="Mark attendance from an uploaded photo")
async def mark_from_photo(
    file: UploadFile = File(...),
    camera_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await file.read()
    query_emb = extract_embedding(content)
    if query_emb is None:
        raise HTTPException(status_code=422, detail="No face detected")

    all_emb = await db.execute(select(FaceEmbedding.user_id, FaceEmbedding.embedding))
    pairs = [(r.user_id, json.loads(r.embedding)) for r in all_emb.all()]
    match = match_embedding(query_emb, pairs)
    if not match:
        return {"marked": False, "reason": "No matching face found"}

    user_id, confidence = match
    log, event = await mark_attendance(db, user_id, confidence=confidence, camera_id=camera_id)

    user = await _load_user_with_dept(db, user_id)
    return {
        "marked": event in ("checked_in", "checked_out"),
        "event": event,
        "user_id": user_id,
        "full_name": user.full_name,
        "confidence": confidence,
        "check_in": log.check_in.isoformat() if log else None,
        "check_out": log.check_out.isoformat() if log and log.check_out else None,
        "duration_minutes": _build_out(log, user).duration_minutes if log else None,
        "reason": None if event in ("checked_in", "checked_out") else event,
    }


@router.post("/manual", response_model=AttendanceOut)
async def create_manual(
    body: AttendanceManualCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    today = body.date or datetime.date.today()
    existing = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.user_id == body.user_id, AttendanceLog.date == today)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Attendance already exists for this date")

    log = AttendanceLog(
        user_id=body.user_id,
        check_in=body.check_in,
        check_out=body.check_out,
        date=today,
        source="manual",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    user = await _load_user_with_dept(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _build_out(log, user)


@router.patch("/{log_id}", response_model=AttendanceOut)
async def update_attendance(
    log_id: int,
    body: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(AttendanceLog).where(AttendanceLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(log, field, val)
    await db.commit()
    await db.refresh(log)
    user = await _load_user_with_dept(db, log.user_id)
    return _build_out(log, user)


@router.delete("/{log_id}", status_code=204)
async def delete_attendance(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(AttendanceLog).where(AttendanceLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.delete(log)
    await db.commit()


@router.post("/{user_id}/checkout", response_model=AttendanceOut)
async def manual_checkout_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Manually trigger check-out for a user for today."""
    log = await manual_checkout(db, user_id)
    if not log:
        raise HTTPException(status_code=404, detail="No open check-in found for today")
    user = await _load_user_with_dept(db, user_id)
    return _build_out(log, user)


@router.get("/summary/daily", response_model=DailySummary)
async def daily_summary(
    date: Optional[datetime.date] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    target = date or datetime.date.today()

    total_r = await db.execute(select(func.count()).where(User.is_active == True))
    total = total_r.scalar()

    present_r = await db.execute(
        select(func.count()).where(AttendanceLog.date == target)
    )
    present = present_r.scalar()

    late_r = await db.execute(
        select(func.count()).where(
            and_(AttendanceLog.date == target, AttendanceLog.is_late == True)
        )
    )
    late = late_r.scalar()

    # Average duration only for records that have both check-in and check-out
    logs_r = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.date == target, AttendanceLog.check_out.isnot(None))
        )
    )
    completed_logs = logs_r.scalars().all()
    avg_duration = None
    if completed_logs:
        total_mins = sum(
            int((l.check_out - l.check_in).total_seconds() // 60) for l in completed_logs
        )
        avg_duration = total_mins // len(completed_logs)

    return DailySummary(
        date=target,
        total_registered=total,
        present=present,
        absent=max(0, total - present),
        late=late,
        avg_duration_minutes=avg_duration,
    )


@router.get("/summary/users", response_model=List[UserTimeSummary])
async def user_time_summary(
    date: Optional[datetime.date] = None,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Per-user check-in, check-out, and total duration for a given date."""
    target = date or datetime.date.today()

    q = (
        select(AttendanceLog, User)
        .join(User, AttendanceLog.user_id == User.id)
        .where(AttendanceLog.date == target)
    )
    if department_id:
        q = q.where(User.department_id == department_id)
    q = q.order_by(User.full_name)

    result = await db.execute(q)
    rows = result.all()

    out = []
    for log, user in rows:
        dept_name = None
        if user.department_id:
            dept_r = await db.execute(select(Department).where(Department.id == user.department_id))
            dept = dept_r.scalar_one_or_none()
            dept_name = dept.name if dept else None

        duration = None
        if log.check_in and log.check_out:
            duration = max(0, int((log.check_out - log.check_in).total_seconds() // 60))

        out.append(UserTimeSummary(
            user_id=user.id,
            full_name=user.full_name,
            employee_id=user.employee_id,
            department=dept_name,
            check_in=log.check_in,
            check_out=log.check_out,
            duration_minutes=duration,
            is_late=log.is_late,
        ))
    return out
