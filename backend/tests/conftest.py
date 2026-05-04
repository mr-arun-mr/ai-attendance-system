"""
Top-level conftest — runs before anything else.

1. Sets DATABASE_URL to the test database before any app module is imported
   (pydantic-settings reads env vars at import time).
2. Stubs out cv2 and face_recognition so dlib/OpenCV never need to be
   compiled.  All CV-dependent code paths are covered via mock-patching in
   individual tests instead.
"""
import os
import sys
from unittest.mock import MagicMock

# ── 1. Point the app at the test database ────────────────────────────────────
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://attendance:attendance_secret@localhost:5432/attendance_test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")
os.environ.setdefault("FACE_DATA_DIR", "/tmp/test_face_data")

# ── 2. Stub heavy CV libraries ────────────────────────────────────────────────
_cv2_mock = MagicMock()
_cv2_mock.IMREAD_COLOR = 1
_cv2_mock.COLOR_BGR2RGB = 4
_cv2_mock.IMWRITE_JPEG_QUALITY = 1
_cv2_mock.FILLED = -1
_cv2_mock.FONT_HERSHEY_SIMPLEX = 0

sys.modules.setdefault("cv2", _cv2_mock)
sys.modules.setdefault("face_recognition", MagicMock())
