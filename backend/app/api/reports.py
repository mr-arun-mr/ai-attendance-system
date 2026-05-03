import csv
import io
import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.department import Department
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly")
async def weekly_report(
    start_date: Optional[datetime.date] = None,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    end = datetime.date.today()
    start = start_date or (end - datetime.timedelta(days=6))

    rows = []
    current = start
    while current <= end:
        q = select(func.count()).where(AttendanceLog.date == current)
        present_r = await db.execute(q)
        present = present_r.scalar()
        late_r = await db.execute(
            select(func.count()).where(
                and_(AttendanceLog.date == current, AttendanceLog.is_late == True)
            )
        )
        late = late_r.scalar()
        rows.append({"date": str(current), "present": present, "late": late})
        current += datetime.timedelta(days=1)

    return rows


@router.get("/export/csv")
async def export_csv(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    end = end_date or datetime.date.today()
    start = start_date or (end - datetime.timedelta(days=29))

    q = (
        select(AttendanceLog, User)
        .join(User, AttendanceLog.user_id == User.id)
        .where(and_(AttendanceLog.date >= start, AttendanceLog.date <= end))
    )
    if department_id:
        q = q.where(User.department_id == department_id)
    q = q.order_by(AttendanceLog.date, User.full_name)

    result = await db.execute(q)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Employee ID", "Full Name", "Department", "Check In", "Check Out", "Late", "Source", "Confidence"])

    for log, user in rows:
        dept_name = ""
        if user.department_id:
            dept_r = await db.execute(select(Department).where(Department.id == user.department_id))
            dept = dept_r.scalar_one_or_none()
            dept_name = dept.name if dept else ""
        writer.writerow([
            log.date,
            user.employee_id,
            user.full_name,
            dept_name,
            log.check_in.strftime("%H:%M:%S") if log.check_in else "",
            log.check_out.strftime("%H:%M:%S") if log.check_out else "",
            "Yes" if log.is_late else "No",
            log.source,
            f"{log.confidence:.2f}" if log.confidence else "",
        ])

    output.seek(0)
    filename = f"attendance_{start}_{end}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
