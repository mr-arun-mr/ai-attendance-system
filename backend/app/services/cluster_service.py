"""
Face clustering and auto-link service.

Workflow:
  1. run_clustering(db)   — groups UnknownFaceCapture rows into FaceCluster rows
                            using DBSCAN on 128-dim L2 space.
  2. auto_link_clusters(db) — for each pending cluster, compares centroid against
                            all registered FaceEmbeddings and either auto-links
                            (distance < AUTO_LINK_THRESHOLD) or stores a hint for
                            admin review (distance < REVIEW_THRESHOLD).
"""

import json
import uuid
import os
import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.face_cluster import FaceCluster
from app.models.face_embedding import FaceEmbedding
from app.models.unknown_face_capture import UnknownFaceCapture
from app.models.user import User
from app.core.config import settings

# DBSCAN: faces within this L2 distance belong to the same cluster.
# Slightly relaxed vs RECOGNITION_THRESHOLD so intra-person angle variation
# doesn't split one person into many clusters.
CLUSTER_EPS = 0.50
CLUSTER_MIN_SAMPLES = 3  # at least 3 detections to form a cluster

# Centroid vs known-user distance bands:
#   < AUTO_LINK_THRESHOLD  → confident enough to auto-extend the user's embeddings
#   < REVIEW_THRESHOLD     → show to admin with a user hint
#   >= REVIEW_THRESHOLD    → no hint, genuinely unknown person
AUTO_LINK_THRESHOLD = 0.45
REVIEW_THRESHOLD = 0.60


async def run_clustering(db: AsyncSession) -> dict:
    """
    Cluster all un-clustered UnknownFaceCapture rows.

    Returns a summary dict: {new_clusters, updated_clusters, noise_points}.
    """
    result = await db.execute(
        select(UnknownFaceCapture).where(UnknownFaceCapture.cluster_id.is_(None))
    )
    captures = result.scalars().all()

    if len(captures) < CLUSTER_MIN_SAMPLES:
        return {"new_clusters": 0, "updated_clusters": 0, "noise_points": len(captures)}

    embeddings = np.array([json.loads(c.embedding) for c in captures], dtype=float)
    labels = DBSCAN(eps=CLUSTER_EPS, min_samples=CLUSTER_MIN_SAMPLES, metric="euclidean").fit_predict(embeddings)

    # Group captures by label; label == -1 means noise
    groups: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        groups.setdefault(label, []).append(idx)

    new_count = 0
    updated_count = 0

    for label, indices in groups.items():
        member_embeddings = embeddings[indices]
        centroid = member_embeddings.mean(axis=0).tolist()

        # Pick the capture closest to centroid as the thumbnail representative
        dists = np.linalg.norm(member_embeddings - centroid, axis=1)
        rep_capture = captures[indices[int(np.argmin(dists))]]

        cluster = FaceCluster(
            centroid=json.dumps(centroid),
            sample_count=len(indices),
            thumbnail_path=rep_capture.thumbnail_path,
            status="pending",
        )
        db.add(cluster)
        await db.flush()  # get cluster.id

        for idx in indices:
            captures[idx].cluster_id = cluster.id

        new_count += 1

    await db.commit()
    noise_count = int(np.sum(labels == -1))
    return {"new_clusters": new_count, "updated_clusters": updated_count, "noise_points": noise_count}


async def auto_link_clusters(db: AsyncSession) -> dict:
    """
    For each pending FaceCluster, compare its centroid against all registered
    FaceEmbeddings.

    - distance < AUTO_LINK_THRESHOLD: auto-link — append centroid as new
      FaceEmbedding for that user and mark cluster "linked".
    - AUTO_LINK_THRESHOLD <= distance < REVIEW_THRESHOLD: store hint for admin.
    - distance >= REVIEW_THRESHOLD: leave as pending with no hint.

    Returns {auto_linked, hinted, unchanged}.
    """
    cluster_result = await db.execute(
        select(FaceCluster).where(FaceCluster.status == "pending")
    )
    clusters = cluster_result.scalars().all()

    emb_result = await db.execute(
        select(FaceEmbedding.user_id, FaceEmbedding.embedding)
    )
    emb_rows = emb_result.all()

    auto_linked = hinted = unchanged = 0

    for cluster in clusters:
        centroid = np.array(json.loads(cluster.centroid))

        best_user_id = None
        best_dist = float("inf")
        for row in emb_rows:
            dist = float(np.linalg.norm(centroid - np.array(json.loads(row.embedding))))
            if dist < best_dist:
                best_dist = dist
                best_user_id = row.user_id

        if best_user_id is None or best_dist >= REVIEW_THRESHOLD:
            unchanged += 1
            continue

        cluster.nearest_user_id = best_user_id
        cluster.nearest_user_distance = round(best_dist, 4)

        if best_dist < AUTO_LINK_THRESHOLD:
            # Auto-extend the matched user's embedding pool with this centroid
            db.add(FaceEmbedding(
                user_id=best_user_id,
                embedding=cluster.centroid,
            ))
            cluster.linked_user_id = best_user_id
            cluster.status = "linked"
            auto_linked += 1
        else:
            # In review zone — keep pending, hint stored above
            hinted += 1

    await db.commit()
    return {"auto_linked": auto_linked, "hinted": hinted, "unchanged": unchanged}


async def link_cluster_to_user(db: AsyncSession, cluster_id: int, user_id: int) -> FaceCluster:
    """Admin manually links a cluster to a user. Appends centroid as FaceEmbedding."""
    result = await db.execute(select(FaceCluster).where(FaceCluster.id == cluster_id))
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise ValueError(f"Cluster {cluster_id} not found")

    user_result = await db.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise ValueError(f"User {user_id} not found")

    db.add(FaceEmbedding(user_id=user_id, embedding=cluster.centroid))
    cluster.linked_user_id = user_id
    cluster.status = "linked"
    await db.commit()
    await db.refresh(cluster)
    return cluster


async def reject_cluster(db: AsyncSession, cluster_id: int) -> FaceCluster:
    """Admin rejects a cluster — marks it so it's excluded from future auto-link."""
    result = await db.execute(select(FaceCluster).where(FaceCluster.id == cluster_id))
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise ValueError(f"Cluster {cluster_id} not found")
    cluster.status = "rejected"
    await db.commit()
    await db.refresh(cluster)
    return cluster


def save_unknown_thumbnail(jpeg_bytes: bytes) -> str:
    """Write JPEG bytes to the unknown_thumbs directory and return the relative path."""
    thumbs_dir = os.path.join(settings.FACE_DATA_DIR, "unknown_thumbs")
    os.makedirs(thumbs_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    full_path = os.path.join(thumbs_dir, filename)
    with open(full_path, "wb") as fh:
        fh.write(jpeg_bytes)
    return f"/face_data/unknown_thumbs/{filename}"
