from pydantic import BaseModel
from typing import Optional
import datetime


class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    stream_url: str
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    is_active: Optional[bool] = None


class CameraOut(BaseModel):
    id: int
    name: str
    location: Optional[str]
    stream_url: str
    is_active: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
