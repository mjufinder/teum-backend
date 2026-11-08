from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_meetings_requires_auth():
    """내 모임 목록은 토큰 없이 접근 시 401."""
    res = client.get("/api/v1/meetings")
    assert res.status_code == 401


def test_create_meeting_requires_auth():
    """모임 생성은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings", json={})
    assert res.status_code == 401


def test_meeting_detail_requires_auth():
    """모임 상세는 토큰 없이 접근 시 401."""
    res = client.get("/api/v1/meetings/1")
    assert res.status_code == 401


def test_meeting_members_requires_auth():
    """모임 구성원 목록은 토큰 없이 접근 시 401."""
    res = client.get("/api/v1/meetings/1/members")
    assert res.status_code == 401


def test_add_member_requires_auth():
    """팀원 추가는 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/members", json={"email": "x@example.com"})
    assert res.status_code == 401


def test_update_meeting_requires_auth():
    """모임 수정은 토큰 없이 접근 시 401."""
    res = client.put("/api/v1/meetings/1", json={"name": "x"})
    assert res.status_code == 401


def test_transfer_admin_requires_auth():
    """관리자 위임은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/transfer-admin", json={"target_user_id": 2})
    assert res.status_code == 401


def test_leave_meeting_requires_auth():
    """모임 탈퇴는 토큰 없이 접근 시 401."""
    res = client.delete("/api/v1/meetings/1/members/me")
    assert res.status_code == 401


def test_delete_meeting_requires_auth():
    """모임 삭제는 토큰 없이 접근 시 401."""
    res = client.delete("/api/v1/meetings/1")
    assert res.status_code == 401
