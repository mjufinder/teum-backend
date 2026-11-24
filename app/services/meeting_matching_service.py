"""팀원 합류 후 주간 후보 계산과 저장을 연결한다."""

import logging
from datetime import time

from fastapi import HTTPException
from httpx import HTTPError
from postgrest.exceptions import APIError

from app.domain.timetable import Timetable
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.timetable_repository import TimetableRepository
from app.schemas.candidate import CandidateInput, MeetingAvailabilityOut
from app.schemas.meeting import MemberOut

logger = logging.getLogger(__name__)


def calculate_weekly_candidates(state: dict) -> list[CandidateInput]:
    """월~일 탐색 시간 조건을 적용한 뒤 상위 3개 선정. 시작은 30분 단위.

    이동 여유는 회의 전후 모두 적용하며 가용 범위 09~22시를 벗어나면 제외한다.
    수업/수동 불가 시간을 함께 반영하고 시간표 미등록자는 참석자로 세지 않는다.
    """
    meeting = state["meeting"]
    lower, upper = time.fromisoformat(meeting["search_start_time"]), time.fromisoformat(meeting["search_end_time"])
    duration, buffer = meeting["min_duration_min"], meeting["travel_buffer_min"]
    if lower >= upper or duration <= 0 or buffer < 0:
        raise ValueError("모임의 기간/탐색 시간/회의 길이 조건이 올바르지 않습니다.")
    members = []
    for member in state["members"]:
        if member["class_bits"] is not None and member["manual_bits"] is not None:
            timetable = Timetable(member["class_bits"], member["manual_bits"])
            members.append((member["member_id"], timetable.available_bits))
    members.sort()
    if not members or duration + 2 * buffer > 780:
        return []
    candidates = []
    for day in range(len(Timetable.DAYS)):
        for slot in range(Timetable.SLOTS_PER_DAY):
            start_min = 9 * 60 + slot * 30
            end_min = start_min + duration
            if start_min - buffer < 540 or end_min + buffer > 1320:
                continue
            start = time(start_min // 60, start_min % 60)
            end = time(end_min // 60, end_min % 60)
            if start < lower or end > upper:
                continue
            first_slot = (start_min - buffer - 540) // 30
            last_slot = (end_min + buffer - 540 + 29) // 30
            offset = day * Timetable.SLOTS_PER_DAY
            ids = [member_id for member_id, bits in members
                   if "0" not in bits[offset + first_slot:offset + last_slot]]
            if ids:
                candidates.append(CandidateInput(day_of_week=day, start_time=start, end_time=end,
                    available_count=len(ids), available_member_ids=ids))
        # 최대 3개만 유지해 전체 탐색의 메모리 사용을 제한한다.
        candidates.sort(key=lambda item: (-item.available_count, item.day_of_week, item.start_time))
        candidates = candidates[:3]
    return candidates


def add_member_and_match(
    meeting_id: int, user_id: int, repository: RecommendationRepository,
) -> MemberOut:
    """등록/재가입 → 일관된 입력 스냅샷 → 계산 → 후보 저장."""
    try:
        prepared = repository.join_and_prepare(meeting_id, user_id)
    except APIError as exc:
        if exc.code in {"PT404", "PT409"}:
            raise HTTPException(int(exc.code[2:]),
                                "모임/사용자가 없거나 이미 추가된 팀원입니다.") from None
        logger.exception("Member registration and matching preparation failed")
        raise HTTPException(503, "팀원 추가 처리에 실패했습니다. 다시 시도해 주세요.") from None
    except HTTPError:
        logger.exception("Member registration connection failed")
        raise HTTPException(503, "팀원 추가 처리에 실패했습니다. 다시 시도해 주세요.") from None

    try:
        candidates = calculate_weekly_candidates(prepared["input_state"])
        payload = [dict(item.model_dump(mode="json"), rank_no=rank)
                   for rank, item in enumerate(candidates, start=1)]
        repository.complete_join(prepared["run_id"], payload)
    except (APIError, HTTPError, ValueError):
        logger.exception("Member registered, but candidate calculation/save failed")
        raise HTTPException(503, {
            "message": "팀원은 등록됐지만 추천 후보 갱신에 실패했습니다. 같은 팀원 추가 요청을 다시 보내 주세요.",
            "member_added": True, "needs_recalc": True,
        }) from None
    row = prepared["member"]
    return MemberOut(member_id=row["id"], user_id=row["user_id"], role=row["role"], status=row["status"])


def get_meeting_availability(
    meeting_id: int,
    member_repo: MeetingMemberRepository,
    timetable_repo: TimetableRepository,
) -> MeetingAvailabilityOut:
    """모임 활성 구성원들의 주간 182칸별 참석 가능 member_id 목록을 집계한다."""
    try:
        members = member_repo.find_active_by_meeting(meeting_id)
        user_ids = [m["user_id"] for m in members]
        timetables = timetable_repo.find_by_users(user_ids)
    except (APIError, HTTPError):
        logger.exception("Meeting availability lookup failed")
        raise HTTPException(503, "시간표 현황 조회에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None

    bits_by_user: dict[int, str] = {}
    for row in timetables:
        if row.get("class_bits") is not None and row.get("manual_bits") is not None:
            bits_by_user[row["user_id"]] = Timetable(
                row["class_bits"], row["manual_bits"]
            ).available_bits

    registered = sorted(
        (m["id"], bits_by_user[m["user_id"]])
        for m in members
        if m["user_id"] in bits_by_user
    )
    total_slots = len(Timetable.DAYS) * Timetable.SLOTS_PER_DAY
    slots = [
        [member_id for member_id, bits in registered if bits[idx] == "1"]
        for idx in range(total_slots)
    ]

    return MeetingAvailabilityOut(
        meeting_id=meeting_id,
        total_member_count=len(members),
        registered_member_count=len(registered),
        slots=slots,
    )
