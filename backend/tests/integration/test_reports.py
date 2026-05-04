"""Integration tests for /reports/ endpoints."""
import datetime
import pytest


class TestWeeklyReport:
    async def test_returns_seven_days(self, client, admin_headers):
        resp = await client.get("/reports/weekly", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        for row in data:
            assert "date" in row
            assert "present" in row
            assert "late" in row

    async def test_counts_reflect_attendance(self, client, admin_headers, admin_user):
        today = datetime.date.today()
        await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "date": today.isoformat(),
            },
            headers=admin_headers,
        )
        resp = await client.get("/reports/weekly", headers=admin_headers)
        today_row = next(r for r in resp.json() if r["date"] == today.isoformat())
        assert today_row["present"] == 1

    async def test_requires_auth(self, client):
        resp = await client.get("/reports/weekly")
        assert resp.status_code == 403


class TestExportCSV:
    async def test_returns_csv_content_type(self, client, admin_headers):
        resp = await client.get("/reports/export/csv", headers=admin_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    async def test_csv_has_correct_header_columns(self, client, admin_headers):
        resp = await client.get("/reports/export/csv", headers=admin_headers)
        lines = resp.text.splitlines()
        assert len(lines) >= 1
        header = lines[0]
        for col in ("Date", "Employee ID", "Full Name", "Check In", "Check Out", "Duration"):
            assert col in header

    async def test_csv_includes_data_rows(self, client, admin_headers, admin_user):
        check_in = datetime.datetime(2024, 3, 5, 8, 0, 0, tzinfo=datetime.timezone.utc)
        check_out = check_in + datetime.timedelta(hours=8)
        await client.post(
            "/attendance/manual",
            json={
                "user_id": admin_user.id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "date": "2024-03-05",
            },
            headers=admin_headers,
        )
        resp = await client.get(
            "/reports/export/csv",
            params={"start_date": "2024-03-01", "end_date": "2024-03-10"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.splitlines()
        assert len(lines) == 2  # header + 1 data row
        assert "ADMIN001" in lines[1]
        assert "480" in lines[1]  # 8 h = 480 min

    async def test_csv_filename_in_content_disposition(self, client, admin_headers):
        resp = await client.get("/reports/export/csv", headers=admin_headers)
        cd = resp.headers.get("content-disposition", "")
        assert "attendance_" in cd
        assert ".csv" in cd

    async def test_requires_auth(self, client):
        resp = await client.get("/reports/export/csv")
        assert resp.status_code == 403
