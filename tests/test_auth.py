import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token
from app.main import app

client = TestClient(app)


def test_jwt_roundtrip():
    """토큰 발급 → 검증 시 동일한 사용자 ID 를 복원한다."""
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_jwt_invalid_token_raises():
    """위조/형식 오류 토큰은 InvalidTokenError 를 던진다."""
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("not.a.valid.token")


def test_protected_endpoint_requires_token():
    """토큰 없이 보호된 엔드포인트 접근 시 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_protected_endpoint_rejects_bad_token():
    """잘못된 토큰으로 접근 시 401."""
    res = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert res.status_code == 401
