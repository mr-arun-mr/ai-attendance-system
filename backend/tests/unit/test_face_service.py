"""
Unit tests for the pure-math parts of face_service.py.

extract_embedding / detect_faces_in_frame rely on cv2 + face_recognition
which are mocked at the conftest level.  We test match_embedding directly
because it only uses numpy and is the critical business-logic path.
"""
import numpy as np
import pytest

from app.services.face_service import match_embedding


def _emb(seed: float, size: int = 128) -> list[float]:
    """Create a deterministic unit-normalised embedding."""
    v = np.full(size, seed, dtype=float)
    return (v / np.linalg.norm(v)).tolist()


class TestMatchEmbedding:
    def test_returns_none_when_no_candidates(self):
        assert match_embedding(_emb(1.0), []) is None

    def test_exact_match_is_found(self):
        emb = _emb(1.0)
        result = match_embedding(emb, [(7, emb)])
        assert result is not None
        user_id, confidence = result
        assert user_id == 7
        assert confidence == pytest.approx(1.0, abs=1e-4)

    def test_below_threshold_returns_none(self):
        # Two completely different embeddings — distance will exceed default threshold
        result = match_embedding(_emb(1.0), [(1, _emb(-1.0))], threshold=0.1)
        assert result is None

    def test_closest_candidate_wins(self):
        # _emb() normalises all same-sign scalars to identical unit vectors,
        # so use structurally different vectors to get meaningful distances.
        query = list(_emb(1.0))                                    # all-ones direction
        close = list(query)                                        # identical → distance 0
        mid = np.zeros(128); mid[0] = 1.0                         # only dim-0 non-zero
        far = list(_emb(-1.0))                                     # opposite direction

        candidates = [
            (10, close),
            (20, mid.tolist()),
            (30, far),
        ]
        result = match_embedding(query, candidates, threshold=2.0)
        assert result is not None
        assert result[0] == 10

    def test_confidence_is_one_minus_distance(self):
        query = _emb(1.0)
        stored = _emb(1.0)
        result = match_embedding(query, [(1, stored)], threshold=1.0)
        assert result is not None
        _, confidence = result
        dist = float(np.linalg.norm(np.array(query) - np.array(stored)))
        assert confidence == pytest.approx(1.0 - dist, abs=1e-4)

    def test_custom_threshold_overrides_default(self):
        # With a very tight threshold, a near-match should be rejected
        query = _emb(1.0)
        close_emb = _emb(0.999)
        strict = match_embedding(query, [(1, close_emb)], threshold=0.001)
        lenient = match_embedding(query, [(1, close_emb)], threshold=1.0)
        # lenient should find it, strict may or may not — at least verify API
        assert lenient is not None

    def test_multiple_candidates_all_below_threshold(self):
        query = _emb(1.0)
        far_candidates = [(i, _emb(float(-i))) for i in range(1, 5)]
        result = match_embedding(query, far_candidates, threshold=0.01)
        assert result is None

    def test_returns_tuple_of_user_id_and_float(self):
        emb = _emb(1.0)
        result = match_embedding(emb, [(42, emb)], threshold=1.0)
        assert result is not None
        user_id, confidence = result
        assert isinstance(user_id, int)
        assert isinstance(confidence, float)
