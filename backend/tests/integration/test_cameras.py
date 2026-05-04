"""Integration tests for /cameras/ endpoints."""
import pytest


class TestListCameras:
    async def test_empty_list(self, client, admin_headers):
        resp = await client.get("/cameras/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_auth(self, client):
        resp = await client.get("/cameras/")
        assert resp.status_code == 403


class TestCreateCamera:
    async def test_admin_creates_camera(self, client, admin_headers):
        resp = await client.post(
            "/cameras/",
            json={"name": "Entrance", "stream_url": "rtsp://192.168.1.1/stream"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Entrance"
        assert data["is_active"] is True
        assert data["location"] is None

    async def test_create_with_location(self, client, admin_headers):
        resp = await client.post(
            "/cameras/",
            json={
                "name": "Lobby",
                "stream_url": "rtsp://10.0.0.1/live",
                "location": "Ground floor",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["location"] == "Ground floor"

    async def test_non_admin_cannot_create(self, client, user_headers):
        resp = await client.post(
            "/cameras/",
            json={"name": "Hack", "stream_url": "rtsp://x"},
            headers=user_headers,
        )
        assert resp.status_code == 403


class TestUpdateCamera:
    async def test_update_name_and_status(self, client, admin_headers):
        create = await client.post(
            "/cameras/",
            json={"name": "Old Name", "stream_url": "rtsp://cam1"},
            headers=admin_headers,
        )
        cam_id = create.json()["id"]

        resp = await client.patch(
            f"/cameras/{cam_id}",
            json={"name": "New Name", "is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["is_active"] is False

    async def test_update_nonexistent_returns_404(self, client, admin_headers):
        resp = await client.patch(
            "/cameras/99999", json={"name": "x"}, headers=admin_headers
        )
        assert resp.status_code == 404


class TestDeleteCamera:
    async def test_delete_camera(self, client, admin_headers):
        create = await client.post(
            "/cameras/",
            json={"name": "TempCam", "stream_url": "rtsp://tmp"},
            headers=admin_headers,
        )
        cam_id = create.json()["id"]
        resp = await client.delete(f"/cameras/{cam_id}", headers=admin_headers)
        assert resp.status_code == 204

        # Confirm it's gone
        list_resp = await client.get("/cameras/", headers=admin_headers)
        assert all(c["id"] != cam_id for c in list_resp.json())

    async def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = await client.delete("/cameras/99999", headers=admin_headers)
        assert resp.status_code == 404
