from fastapi import APIRouter, Depends

from app.api.deps import (
    get_meeting_member,
    get_meeting_member_repository,
    get_recommendation_repository,
    get_timetable_repository,
)
from app.domain.meeting_member import MeetingMember
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.timetable_repository import TimetableRepository
from app.schemas.candidate import CandidateSetOut, MeetingAvailabilityOut
from app.services.meeting_matching_service import get_meeting_availability
from app.services.recommendation_service import read_latest_candidates

router = APIRouter(prefix="/meetings", tags=["candidates"])


@router.get(
    "/{meeting_id}/candidates", response_model=CandidateSetOut,
    summary="최신 추천 후보 조회",
    responses={401: {"description": "인증 필요"}, 403: {"description": "활성 구성원 아님"},
               404: {"description": "모임 또는 최신 후보 묶음 없음"},
               503: {"description": "후보 조회 실패"}},
)
def get_candidates(
    meeting_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    repository: RecommendationRepository = Depends(get_recommendation_repository),
) -> CandidateSetOut:
    """후보가 없는 계산 결과는 200과 빈 목록. 폐기 여부는 vote_status로 확인한다."""
    return read_latest_candidates(meeting_id, repository)


@router.get(
    "/{meeting_id}/availability", response_model=MeetingAvailabilityOut,
    summary="모임 주간 시간대별 참석 가능 인원(히트맵) 조회",
    responses={401: {"description": "인증 필요"}, 403: {"description": "활성 구성원 아님"},
               503: {"description": "시간표 현황 조회 실패"}},
)
def get_availability(
    meeting_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
    timetable_repo: TimetableRepository = Depends(get_timetable_repository),
) -> MeetingAvailabilityOut:
    """182칸(7일×26슬롯)별 참석 가능 member_id 목록을 반환한다."""
    return get_meeting_availability(meeting_id, member_repo, timetable_repo)
