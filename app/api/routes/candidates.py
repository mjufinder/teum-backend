from fastapi import APIRouter, Depends

from app.api.deps import get_meeting_member, get_recommendation_repository
from app.domain.meeting_member import MeetingMember
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.candidate import CandidateSetOut
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
