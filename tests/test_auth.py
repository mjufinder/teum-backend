from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_protected_endpoint_requires_token():
    """토큰 없이 보호된 엔드포인트 접근 시 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_protected_endpoint_rejects_bad_token():
    """유효하지 않은 토큰으로 접근 시 401. (Supabase 검증 실패)"""
    res = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert res.status_code == 401
