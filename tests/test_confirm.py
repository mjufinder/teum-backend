from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_confirm_requires_auth():
    """일정 확정은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/confirm", json={"candidate_id": 1})
    assert res.status_code == 401
