from pydantic import BaseModel
from typing import Optional
import datetime


class AttendanceOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    employee_id: str
    department: Optional[str]
    check_in: datetime.datetime
    check_out: Optional[datetime.datetime]
    date: datetime.date
    confidence: Optional[float]
    source: str
    is_late: bool

    model_config = {"from_attributes": True}


class AttendanceManualCreate(BaseModel):
    user_id: int
    check_in: datetime.datetime
    check_out: Optional[datetime.datetime] = None
    date: Optional[datetime.date] = None


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime.datetime] = None
    check_out: Optional[datetime.datetime] = None
    is_late: Optional[bool] = None


class DailySummary(BaseModel):
    date: datetime.date
    total_registered: int
    present: int
    absent: int
    late: int
