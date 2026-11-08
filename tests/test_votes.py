from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_submit_vote_requires_auth():
    """후보 투표는 토큰 없이 접근 시 401."""
    res = client.post(
        "/api/v1/meetings/1/candidate-sets/1/vote",
        json={"candidate_ids": [1]},
    )
    assert res.status_code == 401
