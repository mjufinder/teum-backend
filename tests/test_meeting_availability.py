from fastapi.testclient import TestClient

from app.domain.timetable import Timetable
from app.main import app
from app.services.meeting_matching_service import get_meeting_availability

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
