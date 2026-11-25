from fastapi.testclient import TestClient

from app.api.deps import (
    get_candidate_repository,
    get_confirmed_schedule_repository,
    get_meeting_member_repository,
    get_meeting_repository,
)
from app.main import app

client = TestClient(app)


def test_issue_share_requires_auth():
    """공유 링크 발급은 토큰 없이 접근 시 401."""
    res = client.post("/api/v1/meetings/1/share")
    assert res.status_code == 401


def test_read_shared_schedule_returns_metadata():
    """공개 공유 조회 시 모임 설명과 참여 인원 수를 함께 반환한다."""

    class FakeMeetingRepo:
        def find_by_share_token(self, token: str):
            if token == "valid-token":
                return {"id": 1, "name": "캡스톤 정기회의", "description": "주간 스프린트"}
            return None

    class FakeConfirmedRepo:
        def find_by_meeting(self, meeting_id: int):
            return {"id": 10, "candidate_id": 20, "confirmed_at": "2026-11-24T01:00:00+09:00"}

    class FakeCandidateRepo:
        def find_by_id(self, candidate_id: int):
            return {"id": 20, "day_of_week": 3, "start_time": "14:00:00", "end_time": "16:00:00"}

    class FakeMemberRepo:
        def find_active_by_meeting(self, meeting_id: int):
            return [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]

    app.dependency_overrides[get_meeting_repository] = lambda: FakeMeetingRepo()
    app.dependency_overrides[get_confirmed_schedule_repository] = lambda: FakeConfirmedRepo()
    app.dependency_overrides[get_candidate_repository] = lambda: FakeCandidateRepo()
    app.dependency_overrides[get_meeting_member_repository] = lambda: FakeMemberRepo()
    try:
        res = client.get("/api/v1/share/valid-token")
        assert res.status_code == 200
        body = res.json()
        assert body["meeting_name"] == "캡스톤 정기회의"
        assert body["description"] == "주간 스프린트"
        assert body["member_count"] == 4
        assert body["day_of_week"] == 3

        not_found = client.get("/api/v1/share/missing-token")
        assert not_found.status_code == 404
    finally:
        app.dependency_overrides.clear()
