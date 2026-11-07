"""주간 공강 계산. DB 조회·저장과 팀원 합류 이벤트 연결은 호출자가 담당한다."""

from collections.abc import Mapping
from typing import TypedDict

from app.domain.timetable import Timetable


class AvailabilityCandidate(TypedDict):
    rank_no: int
    day: str
    start_time: str
    end_time: str
    available_count: int
    available_member_ids: list[int]


def calculate_candidates(
    member_timetables: Mapping[int, Timetable], min_duration_min: int,
) -> list[AvailabilityCandidate]:
    """월~일 09~22시에서 참여 가능한 인원이 많은 주간 후보를 최대 3개 반환.

    입력 키는 팀원 ID이며 값은 저장된 class_bits/manual_bits로 복원한 Timetable.
    available_bits를 사용하므로 수업과 수동 불가 시간을 모두 반영한다.
    회의 길이는 모임의 min_duration_min을 사용하며 1~780분 정수로 받는다.
    시작 시각은 30분 간격이고, 길이가 30의 배수가 아니면 마지막에 걸치는
    슬롯도 공강이어야 한다. 반환 종료 시각은 요청한 길이를 정확히 반영한다.

    인원수 내림차순, 동점은 월~일/시작 시각 오름차순이다. 겹치는 후보는
    허용하며 0명인 구간은 제외한다. 빈 입력/가능한 구간 없음은 []를 반환한다.
    팀원 ID는 오름차순으로 반환한다. 입력을 변경하거나 DB/OCR을 호출하지 않는다.
    토요일과 일요일도 저장된 수업/수동 불가 시간을 반영한다.

    날짜 기간, 일일 탐색 범위, 이동 여유 시간과 영속성은 이 함수의 입력에
    포함되지 않는다. 모임 조건을 연결할 단계에서 전체 후보 탐색에 반영해야 한다.
    """
    max_duration = Timetable.SLOTS_PER_DAY * Timetable.SLOT_MINUTES
    if type(min_duration_min) is not int or not 1 <= min_duration_min <= max_duration:
        raise ValueError("회의 길이는 1~780분 사이의 정수여야 합니다.")
    if not isinstance(member_timetables, Mapping):
        raise ValueError("팀원 시간표는 {팀원 ID: Timetable} 형태여야 합니다.")
    for member_id, timetable in member_timetables.items():
        if type(member_id) is not int or member_id <= 0:
            raise ValueError("팀원 ID는 양의 정수여야 합니다.")
        if not isinstance(timetable, Timetable):
            raise ValueError(f"팀원 {member_id}의 시간표는 Timetable 객체여야 합니다.")

    members = [(member_id, member_timetables[member_id].available_bits)
               for member_id in sorted(member_timetables)]
    window_size = (min_duration_min + Timetable.SLOT_MINUTES - 1) // Timetable.SLOT_MINUTES
    candidates: list[AvailabilityCandidate] = []
    for day_index, day in enumerate(Timetable.DAYS):
        for start_row in range(Timetable.SLOTS_PER_DAY - window_size + 1):
            offset = day_index * Timetable.SLOTS_PER_DAY + start_row
            available_ids = [member_id for member_id, bits in members
                             if bits[offset:offset + window_size] == "1" * window_size]
            if not available_ids:
                continue
            start = Timetable.START_HOUR * 60 + start_row * Timetable.SLOT_MINUTES
            end = start + min_duration_min
            candidates.append({
                "rank_no": 0,
                "day": day,
                "start_time": f"{start // 60:02d}:{start % 60:02d}",
                "end_time": f"{end // 60:02d}:{end % 60:02d}",
                "available_count": len(available_ids),
                "available_member_ids": available_ids,
            })

    # 안정 정렬이므로 동점일 때 탐색 순서(월~일/이른 시각)가 유지된다.
    candidates.sort(key=lambda candidate: candidate["available_count"], reverse=True)
    result = candidates[:3]
    for rank_no, candidate in enumerate(result, start=1):
        candidate["rank_no"] = rank_no
    return result
