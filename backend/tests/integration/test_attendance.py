"""Integration tests for /attendance/ endpoints."""
import datetime
from unittest.mock import patch

import pytest


def _today() -> str:
    return datetime.date.today().isoformat()


class TestListAttendance:
    async def test_returns_empty_list(self, client, admin_headers):
        resp = await client.get("/attendance/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_auth(self, client):
        resp = await client.get("/attendance/")
        assert resp.status_code == 403

    async def test_filter_by_date(self, client, admin_headers, admin_user):
        # Create a manual log then filter by today
        await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            headers=admin_headers,
        )
        resp = await client.get(
            "/attendance/", params={"date": _today()}, headers=admin_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestManualAttendance:
    async def test_create_manual_entry(self, client, admin_headers, admin_user):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        resp = await client.post(
            "/attendance/manual",
            json={"user_id": admin_user.id, "check_in": now},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == admin_user.id
        assert data["source"] == "manual"
        assert data["duration_minutes"] is None  # no check_out yet

    async def test_duplicate_date_returns_409(self, client, admin_headers, admin_user):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        await client.post(
            "/attendance/manual",
            json={"user_id": admin_user.id, "check_in": now},
            headers=admin_headers,
        )
        resp = await client.post(
            "/attendance/manual",
            json={"user_id": admin_user.id, "check_in": now},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    async def test_create_with_checkout_calculates_duration(
        self, client, admin_headers, admin_user
    ):
        check_in = datetime.datetime(2024, 1, 10, 9, 0, 0, tzinfo=datetime.timezone.utc)
        check_out = check_in + datetime.timedelta(hours=8)
        resp = await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "date": "2024-01-10",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["duration_minutes"] == 480

    async def test_non_admin_cannot_create(self, client, user_headers, regular_user):
        resp = await client.post(
            "/attendance/manual",
            json={
                "user_id": regular_user.id,
                "check_in": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            headers=user_headers,
        )
        assert resp.status_code == 403


class TestUpdateAttendance:
    async def test_admin_can_patch(self, client, admin_headers, admin_user):
        now = datetime.datetime.now(datetime.timezone.utc)
        create_resp = await client.post(
            "/attendance/manual",
            json={"user_id": admin_user.id, "check_in": now.isoformat()},
            headers=admin_headers,
        )
        log_id = create_resp.json()["id"]
        check_out = (now + datetime.timedelta(hours=4)).isoformat()
        resp = await client.patch(
            f"/attendance/{log_id}",
            json={"check_out": check_out},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["duration_minutes"] == 240

    async def test_patch_nonexistent_returns_404(self, client, admin_headers):
        resp = await client.patch(
            "/attendance/99999", json={"is_late": True}, headers=admin_headers
        )
        assert resp.status_code == 404


class TestDeleteAttendance:
    async def test_admin_can_delete(self, client, admin_headers, admin_user):
        create = await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            headers=admin_headers,
        )
        log_id = create.json()["id"]
        resp = await client.delete(f"/attendance/{log_id}", headers=admin_headers)
        assert resp.status_code == 204

    async def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = await client.delete("/attendance/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestManualCheckout:
    async def test_checkout_marks_checkout_time(self, client, admin_headers, admin_user):
        # Check in manually
        check_in = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
        await client.post(
            "/attendance/manual",
            json={"user_id": admin_user.id, "check_in": check_in.isoformat()},
            headers=admin_headers,
        )
        resp = await client.post(
            f"/attendance/{admin_user.id}/checkout", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["check_out"] is not None
        assert data["duration_minutes"] is not None
        assert data["duration_minutes"] > 0

    async def test_checkout_without_checkin_returns_404(
        self, client, admin_headers, admin_user
    ):
        resp = await client.post(
            f"/attendance/{admin_user.id}/checkout", headers=admin_headers
        )
        assert resp.status_code == 404


class TestMarkFromPhoto:
    async def test_no_face_detected_returns_422(self, client, user_headers):
        import io
        from unittest.mock import patch

        with patch("app.api.attendance.extract_embedding", return_value=None):
            resp = await client.post(
                "/attendance/mark-photo",
                files={"file": ("photo.jpg", io.BytesIO(b"fake"), "image/jpeg")},
                headers=user_headers,
            )
        assert resp.status_code == 422

    async def test_no_matching_face_returns_unmatched(self, client, user_headers):
        import io

        with patch("app.api.attendance.extract_embedding", return_value=[0.1] * 128), \
             patch("app.api.attendance.match_embedding", return_value=None):
            resp = await client.post(
                "/attendance/mark-photo",
                files={"file": ("photo.jpg", io.BytesIO(b"fake"), "image/jpeg")},
                headers=user_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["marked"] is False

    async def test_matching_face_creates_checkin(
        self, client, user_headers, admin_user
    ):
        import io

        fake_emb = [0.1] * 128
        with patch("app.api.attendance.extract_embedding", return_value=fake_emb), \
             patch(
                 "app.api.attendance.match_embedding",
                 return_value=(admin_user.id, 0.92),
             ):
            resp = await client.post(
                "/attendance/mark-photo",
                files={"file": ("photo.jpg", io.BytesIO(b"fake"), "image/jpeg")},
                headers=user_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event"] == "checked_in"
        assert data["user_id"] == admin_user.id
        assert data["marked"] is True


class TestDailySummary:
    async def test_empty_day(self, client, admin_headers):
        resp = await client.get(
            "/attendance/summary/daily",
            params={"date": "2024-01-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["present"] == 0
        assert data["absent"] == data["total_registered"]
        assert data["avg_duration_minutes"] is None

    async def test_with_checkins(self, client, admin_headers, admin_user):
        check_in = datetime.datetime(2024, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)
        check_out = check_in + datetime.timedelta(hours=7, minutes=30)
        await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "date": "2024-06-01",
            },
            headers=admin_headers,
        )
        resp = await client.get(
            "/attendance/summary/daily",
            params={"date": "2024-06-01"},
            headers=admin_headers,
        )
        data = resp.json()
        assert data["present"] == 1
        assert data["avg_duration_minutes"] == 450


class TestUserTimeSummary:
    async def test_returns_per_user_data(self, client, admin_headers, admin_user):
        check_in = datetime.datetime(2024, 7, 1, 8, 30, 0, tzinfo=datetime.timezone.utc)
        check_out = check_in + datetime.timedelta(hours=9)
        await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "date": "2024-07-01",
            },
            headers=admin_headers,
        )
        resp = await client.get(
            "/attendance/summary/users",
            params={"date": "2024-07-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["user_id"] == admin_user.id
        assert rows[0]["duration_minutes"] == 540

    async def test_empty_returns_empty_list(self, client, admin_headers):
        resp = await client.get(
            "/attendance/summary/users",
            params={"date": "2000-01-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
