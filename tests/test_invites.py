"""초대 링크(MEET-08) 엔드포인트 테스트.

Supabase 없이 돌도록 저장소와 현재 사용자를 메모리 가짜로 바꾼다.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import invites
from app.main import app
from app.schemas.meeting import MemberOut

client = TestClient(app)

ADMIN_ID, MEMBER_ID, NEWCOMER_ID = 1, 2, 3


class FakeMeetingRepo:
    def __init__(self):
        self.rows = {
            10: {
                "id": 10, "name": "캡스톤 2조", "description": "주간 회의",
                "period_start": "2026-11-01", "period_end": "2026-11-30",
                "search_start_time": "09:00:00", "search_end_time": "18:00:00",
                "travel_buffer_min": 0, "min_duration_min": 60,
                "needs_recalc": False, "invite_code": None, "invite_expires_at": None,
                "share_token": None, "deleted_at": None,
            }
        }

    def find_by_id(self, meeting_id):
        return self.rows.get(meeting_id)

    def find_by_invite_code(self, code):
        return next(
            (r for r in self.rows.values()
             if r["invite_code"] == code and r["deleted_at"] is None),
            None,
        )

    def update(self, meeting_id, data):
        self.rows[meeting_id].update(data)
        return self.rows[meeting_id]


class FakeMemberRepo:
    def __init__(self):
        self.rows = [
            {"id": 100, "meeting_id": 10, "user_id": ADMIN_ID, "role": "ADMIN", "status": "ACTIVE"},
            {"id": 101, "meeting_id": 10, "user_id": MEMBER_ID, "role": "MEMBER", "status": "ACTIVE"},
        ]

    def find_by_meeting_and_user(self, meeting_id, user_id):
        return next(
            (r for r in self.rows if r["meeting_id"] == meeting_id and r["user_id"] == user_id),
            None,
        )

    def find_active_by_meeting(self, meeting_id):
        return [r for r in self.rows if r["meeting_id"] == meeting_id and r["status"] == "ACTIVE"]


@pytest.fixture
def env(monkeypatch):
    meetings, members = FakeMeetingRepo(), FakeMemberRepo()
    state = SimpleNamespace(meetings=meetings, members=members, user_id=ADMIN_ID, joined=[])

    def fake_add_member_and_match(meeting_id, user_id, _repo):
        state.joined.append((meeting_id, user_id))
        row = {"id": 200 + len(state.joined), "meeting_id": meeting_id,
               "user_id": user_id, "role": "MEMBER", "status": "ACTIVE"}
        members.rows.append(row)
        return MemberOut(member_id=row["id"], user_id=user_id, role="MEMBER", status="ACTIVE")

    monkeypatch.setattr(invites, "add_member_and_match", fake_add_member_and_match)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[deps.get_meeting_repository] = lambda: meetings
    app.dependency_overrides[deps.get_meeting_member_repository] = lambda: members
    app.dependency_overrides[deps.get_recommendation_repository] = lambda: object()
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(user_id=state.user_id)
    yield state
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _issue(env) -> str:
    env.user_id = ADMIN_ID
    res = client.post("/api/v1/meetings/10/invite")
    assert res.status_code == 200
    return res.json()["invite_code"]


def test_issue_invite_requires_auth():
    """초대 링크 발급은 토큰 없이 접근 시 401."""
    assert client.post("/api/v1/meetings/1/invite").status_code == 401


def test_join_requires_auth():
    """초대 참가는 토큰 없이 접근 시 401."""
    assert client.post("/api/v1/invites/abc/join").status_code == 401


def test_admin_issues_invite_valid_for_7_days(env):
    res = client.post("/api/v1/meetings/10/invite")
    assert res.status_code == 200
    body = res.json()
    assert body["invite_path"] == f"/invite/{body['invite_code']}"
    expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    remaining = expires - datetime.now(timezone.utc)
    assert timedelta(days=6, hours=23) < remaining <= timedelta(days=7)
    assert env.meetings.rows[10]["invite_code"] == body["invite_code"]


def test_reissue_invalidates_previous_code(env):
    old = _issue(env)
    new = _issue(env)
    assert old != new
    assert client.get(f"/api/v1/invites/{old}").status_code == 404


def test_member_cannot_issue_invite(env):
    env.user_id = MEMBER_ID
    assert client.post("/api/v1/meetings/10/invite").status_code == 403


def test_read_invite_without_code_returns_404(env):
    assert client.get("/api/v1/meetings/10/invite").status_code == 404


def test_read_invite_returns_current_code(env):
    code = _issue(env)
    res = client.get("/api/v1/meetings/10/invite")
    assert res.status_code == 200
    assert res.json()["invite_code"] == code


def test_preview_shows_meeting_summary(env):
    code = _issue(env)
    res = client.get(f"/api/v1/invites/{code}")
    assert res.status_code == 200
    body = res.json()
    assert body["meeting_name"] == "캡스톤 2조"
    assert body["member_count"] == 2


def test_preview_unknown_code_returns_404(env):
    assert client.get("/api/v1/invites/nope").status_code == 404


def test_expired_invite_returns_410(env):
    code = _issue(env)
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    env.meetings.rows[10]["invite_expires_at"] = past.isoformat()
    assert client.get(f"/api/v1/invites/{code}").status_code == 410
    env.user_id = NEWCOMER_ID
    assert client.post(f"/api/v1/invites/{code}/join").status_code == 410
    assert env.joined == []


def test_newcomer_joins_by_invite(env):
    code = _issue(env)
    env.user_id = NEWCOMER_ID
    res = client.post(f"/api/v1/invites/{code}/join")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "meeting_id": 10,
        "already_member": False,
        "member": {"member_id": 201, "user_id": NEWCOMER_ID, "role": "MEMBER", "status": "ACTIVE"},
    }
    assert env.joined == [(10, NEWCOMER_ID)]


def test_existing_member_is_not_registered_again(env):
    code = _issue(env)
    env.user_id = MEMBER_ID
    res = client.post(f"/api/v1/invites/{code}/join")
    assert res.status_code == 200
    assert res.json()["already_member"] is True
    assert env.joined == []


def test_existing_member_retries_matching_when_recalc_needed(env):
    """직전 참가의 추천 계산이 실패해 재계산이 필요하면 같은 요청으로 다시 계산한다."""
    code = _issue(env)
    env.meetings.rows[10]["needs_recalc"] = True
    env.user_id = MEMBER_ID
    res = client.post(f"/api/v1/invites/{code}/join")
    assert res.status_code == 200
    assert env.joined == [(10, MEMBER_ID)]


def test_revoked_invite_cannot_be_used(env):
    code = _issue(env)
    assert client.delete("/api/v1/meetings/10/invite").status_code == 204
    assert env.meetings.rows[10]["invite_code"] is None
    env.user_id = NEWCOMER_ID
    assert client.post(f"/api/v1/invites/{code}/join").status_code == 404
