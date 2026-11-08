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


def test_tally_requires_auth():
    """투표 집계는 토큰 없이 접근 시 401."""
    res = client.get("/api/v1/meetings/1/candidate-sets/1/tally")
    assert res.status_code == 401


def test_close_vote_requires_auth():
    """투표 마감은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/candidate-sets/1/close")
    assert res.status_code == 401
