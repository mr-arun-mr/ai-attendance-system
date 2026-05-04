from pydantic import BaseModel, computed_field
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

    @computed_field
    @property
    def duration_minutes(self) -> Optional[int]:
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return max(0, int(delta.total_seconds() // 60))
        return None

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
    avg_duration_minutes: Optional[int] = None


class UserTimeSummary(BaseModel):
    user_id: int
    full_name: str
    employee_id: str
    department: Optional[str]
    check_in: Optional[datetime.datetime]
    check_out: Optional[datetime.datetime]
    duration_minutes: Optional[int]
    is_late: bool

    model_config = {"from_attributes": True}
