"""Integration tests for /clusters/ endpoints."""
import json
import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


def _emb(seed: float) -> list[float]:
    v = np.full(128, seed, dtype=float)
    return (v / np.linalg.norm(v)).tolist()


def _close_emb(base: list[float], noise: float = 0.01) -> list[float]:
    arr = np.array(base) + np.random.default_rng(0).normal(0, noise, len(base))
    return (arr / np.linalg.norm(arr)).tolist()


class TestListClusters:
    async def test_empty_list_initially(self, client, admin_headers):
        resp = await client.get("/clusters/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_admin(self, client, user_headers):
        resp = await client.get("/clusters/", headers=user_headers)
        assert resp.status_code == 403

    async def test_filter_by_status(self, client, admin_headers, test_engine):
        from app.models.face_cluster import FaceCluster

        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            session.add(FaceCluster(centroid=json.dumps(_emb(1.0)), sample_count=3, status="pending"))
            session.add(FaceCluster(centroid=json.dumps(_emb(2.0)), sample_count=5, status="linked"))
            await session.commit()

        resp = await client.get("/clusters/?status=pending", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

        resp2 = await client.get("/clusters/?status=linked", headers=admin_headers)
        assert len(resp2.json()) == 1


class TestRunClusterPipeline:
    async def test_run_returns_summary(self, client, admin_headers):
        resp = await client.post("/clusters/run", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "clustering" in body
        assert "auto_link" in body

    async def test_run_clusters_unknown_captures(self, client, admin_headers, test_engine):
        from app.models.unknown_face_capture import UnknownFaceCapture
        from app.models.face_cluster import FaceCluster
        from sqlalchemy import select

        base = _emb(5.0)
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            for _ in range(4):
                session.add(UnknownFaceCapture(embedding=json.dumps(_close_emb(base))))
            await session.commit()

        resp = await client.post("/clusters/run", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["clustering"]["new_clusters"] == 1

    async def test_requires_admin(self, client, user_headers):
        resp = await client.post("/clusters/run", headers=user_headers)
        assert resp.status_code == 403


class TestLinkCluster:
    async def test_link_assigns_user_and_adds_embedding(self, client, admin_headers, test_engine):
        from app.models.face_cluster import FaceCluster
        from app.models.face_embedding import FaceEmbedding
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy import select

        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            user = User(
                email="link@test.com", full_name="Link User", employee_id="LNK001",
                hashed_password=hash_password("pw"), is_active=True,
            )
            session.add(user)
            cluster = FaceCluster(
                centroid=json.dumps(_emb(7.0)), sample_count=4, status="pending"
            )
            session.add(cluster)
            await session.commit()
            await session.refresh(user)
            await session.refresh(cluster)
            user_id, cluster_id = user.id, cluster.id

        resp = await client.post(
            f"/clusters/{cluster_id}/link?user_id={user_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "linked"
        assert body["linked_user_id"] == user_id

        # Verify FaceEmbedding was created
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            result = await session.execute(
                select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
            )
            embs = result.scalars().all()
        assert len(embs) == 1

    async def test_link_returns_404_for_missing_cluster(self, client, admin_headers):
        resp = await client.post("/clusters/9999/link?user_id=1", headers=admin_headers)
        assert resp.status_code == 404

    async def test_requires_admin(self, client, user_headers):
        resp = await client.post("/clusters/1/link?user_id=1", headers=user_headers)
        assert resp.status_code == 403


class TestRejectCluster:
    async def test_reject_sets_status(self, client, admin_headers, test_engine):
        from app.models.face_cluster import FaceCluster

        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            cluster = FaceCluster(
                centroid=json.dumps(_emb(9.0)), sample_count=3, status="pending"
            )
            session.add(cluster)
            await session.commit()
            await session.refresh(cluster)
            cluster_id = cluster.id

        resp = await client.post(f"/clusters/{cluster_id}/reject", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    async def test_reject_returns_404_for_missing_cluster(self, client, admin_headers):
        resp = await client.post("/clusters/9999/reject", headers=admin_headers)
        assert resp.status_code == 404

    async def test_requires_admin(self, client, user_headers):
        resp = await client.post("/clusters/1/reject", headers=user_headers)
        assert resp.status_code == 403
