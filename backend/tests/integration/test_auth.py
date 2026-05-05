"""Integration tests for POST /auth/login."""
import pytest


class TestLogin:
    async def test_login_success(self, client, admin_user):
        resp = await client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "testpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["is_admin"] is True
        assert data["full_name"] == "Test Admin"

    async def test_login_wrong_password(self, client, admin_user):
        resp = await client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "pass"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_user(self, client, test_engine):
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            user = User(
                email="inactive@example.com",
                full_name="Inactive",
                employee_id="INA001",
                hashed_password=hash_password("pass"),
                is_active=False,
            )
            session.add(user)
            await session.commit()

        resp = await client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "pass"},
        )
        assert resp.status_code == 403

    async def test_token_allows_authenticated_request(self, client, admin_user):
        resp = await client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "testpass123"},
        )
        token = resp.json()["access_token"]
        resp2 = await client.get(
            "/users/", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp2.status_code == 200

    async def test_no_token_returns_403(self, client):
        resp = await client.get("/users/")
        assert resp.status_code == 403
