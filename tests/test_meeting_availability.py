from datetime import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.domain.timetable import Timetable
from app.main import app
from app.schemas.candidate import CustomCandidateCreateRequest
from app.services.meeting_matching_service import (
    add_custom_candidate,
    delete_custom_candidate,
    get_meeting_availability,
)

client = TestClient(app)


class FakeMemberRepo:
    def __init__(self, members):
        self._members = members

    def find_active_by_meeting(self, meeting_id: int):
        return self._members


class FakeTimetableRepo:
    def __init__(self, rows):
        self._rows = rows

    def find_by_users(self, user_ids: list[int]):
        return [r for r in self._rows if r["user_id"] in user_ids]


def test_meeting_availability_requires_auth():
    """모임 주간 가능 인원 조회는 토큰 없이 접근 시 401."""
    res = client.get("/api/v1/meetings/1/availability")
    assert res.status_code == 401


def test_get_meeting_availability_aggregates_182_slots():
    """등록된 구성원만 집계하고 182칸별 가능 member_id 목록을 반환한다."""
    total = len(Timetable.DAYS) * Timetable.SLOTS_PER_DAY
    ones = "1" * total
    # member 10 (user 1): 0번 칸만 수업(불가)
    class_1 = "0" + "1" * (total - 1)
    # member 20 (user 2): 1번 칸만 개인 일정(불가)
    manual_2 = "10" + "1" * (total - 2)

    member_repo = FakeMemberRepo([
        {"id": 20, "user_id": 2},
        {"id": 10, "user_id": 1},
        {"id": 30, "user_id": 3},  # 시간표 미등록
    ])
    timetable_repo = FakeTimetableRepo([
        {"user_id": 1, "class_bits": class_1, "manual_bits": ones},
        {"user_id": 2, "class_bits": ones, "manual_bits": manual_2},
    ])

    result = get_meeting_availability(1, member_repo, timetable_repo)

    assert result.meeting_id == 1
    assert result.total_member_count == 3
    assert result.registered_member_count == 2
    assert len(result.slots) == total
    assert result.slots[0] == [20]
    assert result.slots[1] == [10]
    assert result.slots[2] == [10, 20]


def test_custom_candidate_requires_auth():
    """후보 시간 직접 추가는 토큰 없이 접근 시 401."""
    res = client.post(
        "/api/v1/meetings/1/candidates",
        json={"day_of_week": 0, "start_time": "10:00", "end_time": "11:00"},
    )
    assert res.status_code == 401


def test_add_custom_candidate_appends_to_open_set():
    """기존 OPEN 후보 묶음에 rank_no >= 4로 직접 선택한 후보를 추가한다."""
    total = len(Timetable.DAYS) * Timetable.SLOTS_PER_DAY
    ones = "1" * total
    inserted = []

    class FakeCandidateRepo:
        def insert(self, data):
            inserted.append(data)
            return {"id": 99, **data}

    class FakeSetRepo:
        def update(self, set_id, data):
            return {"id": set_id, **data}

    class FakeRecRepo:
        def find_latest(self, meeting_id):
            if not inserted:
                return {
                    "meeting_id": meeting_id,
                    "run_id": 1,
                    "set_id": 5,
                    "result_status": "HAS_CANDIDATE",
                    "vote_status": "OPEN",
                    "created_at": "2026-11-24T00:00:00+09:00",
                    "candidates": [
                        {
                            "candidate_id": 1,
                            "rank_no": 1,
                            "day_of_week": 0,
                            "start_time": "09:00:00",
                            "end_time": "10:00:00",
                            "available_count": 1,
                            "available_member_ids": [10],
                        }
                    ],
                }
            return {
                "meeting_id": meeting_id,
                "run_id": 1,
                "set_id": 5,
                "result_status": "HAS_CANDIDATE",
                "vote_status": "OPEN",
                "created_at": "2026-11-24T00:00:00+09:00",
                "candidates": [
                    {
                        "candidate_id": 1,
                        "rank_no": 1,
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                        "available_count": 1,
                        "available_member_ids": [10],
                    },
                    {
                        "candidate_id": 99,
                        "rank_no": 4,
                        "day_of_week": 1,
                        "start_time": "14:00:00",
                        "end_time": "15:00:00",
                        "available_count": 1,
                        "available_member_ids": [10],
                    },
                ],
            }

    out = add_custom_candidate(
        1,
        CustomCandidateCreateRequest(
            day_of_week=1, start_time=time(14, 0), end_time=time(15, 0)
        ),
        None,
        FakeMemberRepo([{"id": 10, "user_id": 1}]),
        FakeTimetableRepo([{"user_id": 1, "class_bits": ones, "manual_bits": ones}]),
        None,
        FakeSetRepo(),
        FakeCandidateRepo(),
        FakeRecRepo(),
    )

    assert len(inserted) == 1
    assert inserted[0]["rank_no"] == 4
    assert inserted[0]["available_member_ids"] == [10]
    assert len(out.candidates) == 2
    assert out.candidates[1].rank_no == 4


def test_add_custom_candidate_rejects_duplicate():
    """이미 존재하는 후보 시간이면 409를 반환한다."""
    total = len(Timetable.DAYS) * Timetable.SLOTS_PER_DAY
    ones = "1" * total

    class FakeRecRepo:
        def find_latest(self, meeting_id):
            return {
                "meeting_id": meeting_id,
                "run_id": 1,
                "set_id": 5,
                "result_status": "HAS_CANDIDATE",
                "vote_status": "OPEN",
                "created_at": "2026-11-24T00:00:00+09:00",
                "candidates": [
                    {
                        "candidate_id": 1,
                        "rank_no": 1,
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                        "available_count": 1,
                        "available_member_ids": [10],
                    }
                ],
            }

    with pytest.raises(HTTPException) as exc:
        add_custom_candidate(
            1,
            CustomCandidateCreateRequest(
                day_of_week=0, start_time=time(9, 0), end_time=time(10, 0)
            ),
            None,
            FakeMemberRepo([{"id": 10, "user_id": 1}]),
            FakeTimetableRepo([{"user_id": 1, "class_bits": ones, "manual_bits": ones}]),
            None,
            None,
            None,
            FakeRecRepo(),
        )
    assert exc.value.status_code == 409


def test_delete_custom_candidate_removes_only_custom():
    """직접 추가한 후보(rank_no > 3)는 삭제되고, 추천 시간(rank_no <= 3)은 400을 반환한다."""
    deleted = []

    class FakeRunRepo:
        def find_by_id(self, run_id):
            return {"id": run_id, "meeting_id": 1}

    class FakeSetRepo:
        def find_by_id(self, set_id):
            return {
                "id": set_id,
                "run_id": 1,
                "vote_status": "OPEN",
                "result_status": "HAS_CANDIDATE",
            }

        def update(self, set_id, data):
            return {"id": set_id, **data}

    class FakeCandidateRepo:
        def find_by_id(self, cid):
            if cid == 1:
                return {"id": 1, "set_id": 5, "rank_no": 1}
            if cid == 99:
                return {"id": 99, "set_id": 5, "rank_no": 4}
            return None

        def delete(self, cid):
            deleted.append(cid)

        def find_by_set(self, set_id):
            return [{"id": 1, "rank_no": 1}]

    class FakeRecRepo:
        def find_latest(self, meeting_id):
            return {
                "meeting_id": meeting_id,
                "run_id": 1,
                "set_id": 5,
                "result_status": "HAS_CANDIDATE",
                "vote_status": "OPEN",
                "created_at": "2026-11-24T00:00:00+09:00",
                "candidates": [],
            }

    with pytest.raises(HTTPException) as exc:
        delete_custom_candidate(
            1, 1, FakeRunRepo(), FakeSetRepo(), FakeCandidateRepo(), FakeRecRepo()
        )
    assert exc.value.status_code == 400

    delete_custom_candidate(
        1, 99, FakeRunRepo(), FakeSetRepo(), FakeCandidateRepo(), FakeRecRepo()
    )
    assert deleted == [99]
