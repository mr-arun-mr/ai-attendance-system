from sqlalchemy import String, DateTime, ForeignKey, func, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import datetime


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    check_in: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="camera")  # camera | manual
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id"), nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="attendance_logs")
    camera: Mapped["Camera"] = relationship("Camera")
