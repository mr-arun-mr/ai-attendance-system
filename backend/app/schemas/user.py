from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime


class DepartmentBase(BaseModel):
    name: str


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentOut(DepartmentBase):
    id: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    employee_id: str
    password: str
    department_id: Optional[int] = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    employee_id: str
    is_active: bool
    is_admin: bool
    department_id: Optional[int]
    photo_path: Optional[str]
    created_at: datetime.datetime
    has_face: bool = False

    model_config = {"from_attributes": True}
