"""
Unit tests for cluster_service.py and the camera_ws dedup helper.

These tests cover only pure-logic helpers that have no DB dependency,
consistent with the existing unit test conventions (no real DB fixtures here).
DB-dependent service paths (run_clustering, auto_link_clusters, etc.) are
covered via the API integration tests in tests/integration/test_clusters.py.
"""
import json
import numpy as np
import pytest


def _emb(seed: float, size: int = 128) -> list[float]:
    v = np.full(size, seed, dtype=float)
    return (v / np.linalg.norm(v)).tolist()


# ── save_unknown_thumbnail ────────────────────────────────────────────────────

class TestSaveUnknownThumbnail:
    def test_writes_file_and_returns_web_path(self, tmp_path, monkeypatch):
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "FACE_DATA_DIR", str(tmp_path))

        from app.services.cluster_service import save_unknown_thumbnail
        path = save_unknown_thumbnail(b"\xff\xd8\xff\xe0fake_jpeg_data")

        assert path.startswith("/face_data/unknown_thumbs/")
        assert path.endswith(".jpg")
        on_disk = tmp_path / "unknown_thumbs" / path.split("/")[-1]
        assert on_disk.exists()
        assert on_disk.read_bytes() == b"\xff\xd8\xff\xe0fake_jpeg_data"

    def test_creates_directory_if_missing(self, tmp_path, monkeypatch):
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "FACE_DATA_DIR", str(tmp_path / "new_dir"))

        from app.services.cluster_service import save_unknown_thumbnail
        path = save_unknown_thumbnail(b"data")
        assert path.startswith("/face_data/unknown_thumbs/")

    def test_each_call_produces_unique_filename(self, tmp_path, monkeypatch):
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "FACE_DATA_DIR", str(tmp_path))

        from app.services.cluster_service import save_unknown_thumbnail
        p1 = save_unknown_thumbnail(b"a")
        p2 = save_unknown_thumbnail(b"b")
        assert p1 != p2


# ── _should_save_unknown (camera_ws dedup helper) ────────────────────────────

class TestShouldSaveUnknown:
    def _get_fn(self):
        # Import after conftest stubs are in place
        from app.api.camera_ws import _should_save_unknown
        return _should_save_unknown

    def test_always_saves_when_recent_is_empty(self):
        fn = self._get_fn()
        assert fn(_emb(1.0), []) is True

    def test_skips_when_near_duplicate_in_window(self):
        fn = self._get_fn()
        base = _emb(1.0)
        import time
        recent = [(base, time.time())]
        assert fn(base, recent) is False

    def test_saves_when_far_from_recent(self):
        fn = self._get_fn()
        import time
        recent = [(_emb(-1.0), time.time())]  # opposite direction — large L2
        assert fn(_emb(1.0), recent) is True

    def test_threshold_boundary(self):
        from app.api.camera_ws import UNKNOWN_DEDUP_DIST
        fn = self._get_fn()
        import time

        base = np.array(_emb(1.0))
        # Construct a vector exactly at UNKNOWN_DEDUP_DIST from base
        perp = np.zeros(128)
        perp[0] = 1.0
        perp = perp - base * np.dot(base, perp)
        perp /= np.linalg.norm(perp)
        at_boundary = (base + UNKNOWN_DEDUP_DIST * perp).tolist()

        # At exactly the threshold, distance == UNKNOWN_DEDUP_DIST → NOT saved (< is strict)
        recent = [(base.tolist(), time.time())]
        result = fn(at_boundary, recent)
        # distance at boundary equals UNKNOWN_DEDUP_DIST; condition is dist < threshold
        # so this face SHOULD be saved (not a duplicate)
        assert result is True


# ── Threshold constants sanity check ─────────────────────────────────────────

class TestThresholdConstants:
    def test_auto_link_below_review(self):
        from app.services.cluster_service import AUTO_LINK_THRESHOLD, REVIEW_THRESHOLD
        assert AUTO_LINK_THRESHOLD < REVIEW_THRESHOLD

    def test_cluster_eps_sensible(self):
        from app.services.cluster_service import CLUSTER_EPS, CLUSTER_MIN_SAMPLES
        assert 0.0 < CLUSTER_EPS < 1.0
        assert CLUSTER_MIN_SAMPLES >= 2
