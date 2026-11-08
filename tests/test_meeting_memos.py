from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_memo_requires_auth():
    res = client.post("/api/v1/meetings/1/memos", json={"content": "x"})
    assert res.status_code == 401


def test_list_memos_requires_auth():
    res = client.get("/api/v1/meetings/1/memos")
    assert res.status_code == 401


def test_update_memo_requires_auth():
    res = client.put("/api/v1/meetings/1/memos/1", json={"content": "x"})
    assert res.status_code == 401


def test_delete_memo_requires_auth():
    res = client.delete("/api/v1/meetings/1/memos/1")
    assert res.status_code == 401
