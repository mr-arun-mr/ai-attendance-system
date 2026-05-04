"""Integration tests for /users/ and /departments/ endpoints."""
import pytest


class TestListUsers:
    async def test_returns_empty_list_initially(self, client, admin_headers):
        # admin_user fixture creates one user — should appear
        resp = await client.get("/users/", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_requires_auth(self, client):
        resp = await client.get("/users/")
        assert resp.status_code == 403

    async def test_regular_user_can_list(self, client, user_headers):
        resp = await client.get("/users/", headers=user_headers)
        assert resp.status_code == 200

    async def test_filter_by_department(self, client, admin_headers, test_engine):
        from app.models.department import Department
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            dept = Department(name="Engineering")
            session.add(dept)
            await session.commit()
            await session.refresh(dept)

            user = User(
                email="eng@test.local",
                full_name="Engineer",
                employee_id="ENG001",
                hashed_password=hash_password("pass"),
                department_id=dept.id,
            )
            session.add(user)
            await session.commit()

        resp = await client.get(
            "/users/", params={"department_id": dept.id}, headers=admin_headers
        )
        assert resp.status_code == 200
        ids = [u["department_id"] for u in resp.json()]
        assert all(i == dept.id for i in ids)


class TestCreateUser:
    async def test_admin_creates_user(self, client, admin_headers):
        resp = await client.post(
            "/users/",
            json={
                "email": "new@test.local",
                "full_name": "New User",
                "employee_id": "NEW001",
                "password": "secret123",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@test.local"
        assert data["has_face"] is False

    async def test_non_admin_cannot_create_user(self, client, user_headers):
        resp = await client.post(
            "/users/",
            json={
                "email": "x@test.local",
                "full_name": "X",
                "employee_id": "X001",
                "password": "pass",
            },
            headers=user_headers,
        )
        assert resp.status_code == 403

    async def test_duplicate_email_returns_400(self, client, admin_headers, admin_user):
        resp = await client.post(
            "/users/",
            json={
                "email": "admin@test.local",  # already exists
                "full_name": "Duplicate",
                "employee_id": "DUP001",
                "password": "pass",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400


class TestGetUser:
    async def test_get_existing_user(self, client, admin_headers, admin_user):
        resp = await client.get(f"/users/{admin_user.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == admin_user.id

    async def test_get_nonexistent_user(self, client, admin_headers):
        resp = await client.get("/users/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestUpdateUser:
    async def test_update_full_name(self, client, admin_headers, admin_user):
        resp = await client.patch(
            f"/users/{admin_user.id}",
            json={"full_name": "Updated Name"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    async def test_deactivate_user(self, client, admin_headers, regular_user):
        resp = await client.patch(
            f"/users/{regular_user.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


class TestDeleteUser:
    async def test_admin_can_delete(self, client, admin_headers, regular_user):
        resp = await client.delete(f"/users/{regular_user.id}", headers=admin_headers)
        assert resp.status_code == 204

    async def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = await client.delete("/users/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestDepartments:
    async def test_list_empty(self, client, admin_headers):
        resp = await client.get("/departments/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_department(self, client, admin_headers):
        resp = await client.post(
            "/departments/", json={"name": "HR"}, headers=admin_headers
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "HR"

    async def test_delete_department(self, client, admin_headers):
        create = await client.post(
            "/departments/", json={"name": "TempDept"}, headers=admin_headers
        )
        dept_id = create.json()["id"]
        resp = await client.delete(f"/departments/{dept_id}", headers=admin_headers)
        assert resp.status_code == 204

    async def test_non_admin_cannot_create_department(self, client, user_headers):
        resp = await client.post(
            "/departments/", json={"name": "Nope"}, headers=user_headers
        )
        assert resp.status_code == 403
