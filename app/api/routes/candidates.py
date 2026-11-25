from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_candidate_repository,
    get_candidate_set_repository,
    get_matching_run_repository,
    get_meeting_member,
    get_meeting_member_repository,
    get_meeting_repository,
    get_recommendation_repository,
    get_timetable_repository,
)
from app.domain.meeting_member import MeetingMember
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.candidate_set_repository import CandidateSetRepository
from app.repositories.matching_run_repository import MatchingRunRepository
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.timetable_repository import TimetableRepository
from app.schemas.candidate import (
    CandidateSetOut,
    CustomCandidateCreateRequest,
    MeetingAvailabilityOut,
)
from app.services.meeting_matching_service import (
    add_custom_candidate,
    delete_custom_candidate,
    get_meeting_availability,
)
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


@router.post(
    "/{meeting_id}/candidates",
    response_model=CandidateSetOut,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 직접 후보 시간 추가",
    responses={
        401: {"description": "인증 필요"},
        403: {"description": "활성 구성원 아님"},
        409: {"description": "중복 후보 또는 마감된 투표"},
        503: {"description": "후보 추가 실패"},
    },
)
def create_custom_candidate(
    meeting_id: int,
    body: CustomCandidateCreateRequest,
    _member: MeetingMember = Depends(get_meeting_member),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
    timetable_repo: TimetableRepository = Depends(get_timetable_repository),
    run_repo: MatchingRunRepository = Depends(get_matching_run_repository),
    set_repo: CandidateSetRepository = Depends(get_candidate_set_repository),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> CandidateSetOut:
    """히트맵에서 직접 선택한 시간대를 후보 목록에 추가한다."""
    return add_custom_candidate(
        meeting_id,
        body,
        meeting_repo,
        member_repo,
        timetable_repo,
        run_repo,
        set_repo,
        candidate_repo,
        rec_repo,
    )


@router.delete(
    "/{meeting_id}/candidates/{candidate_id}",
    response_model=CandidateSetOut,
    summary="사용자 직접 추가 후보 시간 삭제",
    responses={
        400: {"description": "추천 시간은 삭제 불가"},
        401: {"description": "인증 필요"},
        403: {"description": "활성 구성원 아님"},
        404: {"description": "후보 없음"},
        409: {"description": "종료된 투표 또는 확정된 일정"},
    },
)
def remove_custom_candidate(
    meeting_id: int,
    candidate_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    run_repo: MatchingRunRepository = Depends(get_matching_run_repository),
    set_repo: CandidateSetRepository = Depends(get_candidate_set_repository),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> CandidateSetOut:
    """직접 추가한 후보 시간(rank_no > 3)을 삭제한다."""
    return delete_custom_candidate(
        meeting_id,
        candidate_id,
        run_repo,
        set_repo,
        candidate_repo,
        rec_repo,
    )
