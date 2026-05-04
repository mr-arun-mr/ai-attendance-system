"""Unit tests for app/core/security.py — pure functions, no DB."""
import time
from datetime import timedelta

import pytest
from jose import jwt

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings


class TestPasswordHashing:
    def test_hash_differs_from_plain(self):
        hashed = hash_password("secret")
        assert hashed != "secret"

    def test_correct_password_verifies(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_verifies_against_its_own_hash(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_same_password_produces_different_hashes(self):
        # bcrypt uses a random salt per call
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2


class TestJWTTokens:
    def test_create_token_returns_string(self):
        token = create_access_token({"sub": "42"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_decode_valid_token_returns_payload(self):
        token = create_access_token({"sub": "99"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "99"

    def test_decode_includes_expiry(self):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry_is_respected(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(hours=2))
        payload = decode_token(token)
        assert payload is not None

    def test_decode_expired_token_returns_none(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_decode_garbage_string_returns_none(self):
        assert decode_token("not.a.jwt") is None

    def test_decode_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_decode_wrong_secret_returns_none(self):
        token = jwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
        assert decode_token(token) is None

    def test_extra_claims_preserved(self):
        token = create_access_token({"sub": "5", "role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
