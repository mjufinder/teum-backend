from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_issue_share_requires_auth():
    """공유 링크 발급은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/share")
    assert res.status_code == 401
