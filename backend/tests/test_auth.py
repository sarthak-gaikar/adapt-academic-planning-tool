"""
ADAPT — Unit Tests for Security & JWT Auth
"""

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    raw = "StrongSecret123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "user-uuid-12345", "role": "FACULTY"}
    token = create_access_token(payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-12345"
    assert decoded["role"] == "FACULTY"


def test_jwt_invalid_token():
    assert decode_access_token("invalid.token.string") is None
