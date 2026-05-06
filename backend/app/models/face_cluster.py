from sqlalchemy import String, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import datetime


class FaceCluster(Base):
    __tablename__ = "face_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    # JSON array of 128 floats — mean of all member embeddings
    centroid: Mapped[str] = mapped_column(String(8192), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Nearest known user from auto-link scan (hint for admin review)
    nearest_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    nearest_user_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Set when admin or auto-link assigns the cluster to a user
    linked_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # "pending" | "linked" | "rejected"
    status: Mapped[str] = mapped_column(String(20), default="pending")

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    nearest_user: Mapped["User"] = relationship("User", foreign_keys=[nearest_user_id])
    linked_user: Mapped["User"] = relationship("User", foreign_keys=[linked_user_id])
    captures: Mapped[list["UnknownFaceCapture"]] = relationship(
        "UnknownFaceCapture", back_populates="cluster"
    )
