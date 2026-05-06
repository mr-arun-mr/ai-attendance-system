"""
Admin API for face cluster management.

Endpoints:
  GET  /clusters/           — list all clusters (filterable by status)
  POST /clusters/run        — trigger clustering + auto-link
  POST /clusters/{id}/link  — manually link a cluster to a user
  POST /clusters/{id}/reject — reject a cluster
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.face_cluster import FaceCluster
from app.models.unknown_face_capture import UnknownFaceCapture
from app.api.deps import require_admin
from app.services.cluster_service import (
    run_clustering,
    auto_link_clusters,
    link_cluster_to_user,
    reject_cluster,
)

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _cluster_out(c: FaceCluster) -> dict:
    return {
        "id": c.id,
        "status": c.status,
        "sample_count": c.sample_count,
        "thumbnail_path": c.thumbnail_path,
        "nearest_user_id": c.nearest_user_id,
        "nearest_user_distance": c.nearest_user_distance,
        "linked_user_id": c.linked_user_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/")
async def list_clusters(
    status: Optional[str] = Query(None, description="Filter by status: pending, linked, rejected"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List face clusters, optionally filtered by status."""
    q = select(FaceCluster).order_by(FaceCluster.created_at.desc())
    if status:
        q = q.where(FaceCluster.status == status)
    result = await db.execute(q)
    clusters = result.scalars().all()
    return [_cluster_out(c) for c in clusters]


@router.post("/run")
async def run_cluster_pipeline(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Run DBSCAN clustering on buffered unknown faces, then auto-link confident matches."""
    cluster_summary = await run_clustering(db)
    link_summary = await auto_link_clusters(db)
    return {
        "clustering": cluster_summary,
        "auto_link": link_summary,
    }


@router.get("/{cluster_id}/samples")
async def list_cluster_samples(
    cluster_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return thumbnail paths for all UnknownFaceCapture rows in this cluster."""
    result = await db.execute(
        select(FaceCluster).where(FaceCluster.id == cluster_id)
    )
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cap_result = await db.execute(
        select(UnknownFaceCapture).where(UnknownFaceCapture.cluster_id == cluster_id)
    )
    captures = cap_result.scalars().all()
    return [
        {"id": c.id, "thumbnail_path": c.thumbnail_path, "captured_at": c.captured_at.isoformat() if c.captured_at else None}
        for c in captures
    ]


@router.post("/{cluster_id}/link")
async def link_cluster(
    cluster_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Manually assign a cluster to a user. Appends the centroid as a new FaceEmbedding."""
    try:
        cluster = await link_cluster_to_user(db, cluster_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _cluster_out(cluster)


@router.post("/{cluster_id}/reject")
async def reject_cluster_endpoint(
    cluster_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Mark a cluster as rejected so it is ignored in future auto-link runs."""
    try:
        cluster = await reject_cluster(db, cluster_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _cluster_out(cluster)
