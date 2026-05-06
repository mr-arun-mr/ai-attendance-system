from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import datetime


class UnknownFaceCapture(Base):
    __tablename__ = "unknown_face_captures"

    id: Mapped[int] = mapped_column(primary_key=True)
    # JSON array of 128 floats
    embedding: Mapped[str] = mapped_column(String(8192), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True
    )
    captured_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Null until run_clustering assigns it
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("face_clusters.id", ondelete="SET NULL"), nullable=True
    )

    cluster: Mapped["FaceCluster"] = relationship("FaceCluster", back_populates="captures")
