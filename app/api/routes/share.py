import secrets

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_candidate_repository,
    get_confirmed_schedule_repository,
    get_meeting_member_repository,
    get_meeting_repository,
    require_meeting_admin,
)
from app.domain.meeting_member import MeetingMember
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.confirmed_schedule_repository import ConfirmedScheduleRepository
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.vote import PublicScheduleOut, ShareOut

# 공유 발급(관리자, 인증)과 공유 조회(비회원, 인증 불필요)를 한 라우터에 둔다.
router = APIRouter(tags=["share"])


@router.post(
    "/meetings/{meeting_id}/share",
    response_model=ShareOut,
    summary="확정 일정 공유 링크 발급",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임 없음"},
        409: {"description": "확정된 일정 없음"},
    },
)
def issue_share_link(
    meeting_id: int,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    confirmed_repo: ConfirmedScheduleRepository = Depends(get_confirmed_schedule_repository),
) -> ShareOut:
    """확정된 일정의 외부 공유 토큰을 발급/회전한다 (VOTE-04, 관리자만)."""
    if confirmed_repo.find_by_meeting(meeting_id) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="확정된 일정이 없습니다. 먼저 일정을 확정하세요.",
        )
    token = secrets.token_urlsafe(12)
    meeting_repo.update(meeting_id, {"share_token": token})
    return ShareOut(share_token=token, share_url=f"/api/v1/share/{token}")


@router.get(
    "/share/{share_token}",
    response_model=PublicScheduleOut,
    summary="확정 일정 공유 조회 (비회원)",
    responses={404: {"description": "유효하지 않은 링크 또는 미확정"}},
)
def read_shared_schedule(
    share_token: str,
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    confirmed_repo: ConfirmedScheduleRepository = Depends(get_confirmed_schedule_repository),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> PublicScheduleOut:
    """공유 토큰으로 확정 일정을 읽기 전용 조회한다 (VOTE-04, 인증 불필요)."""
    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="유효하지 않은 공유 링크입니다."
    )
    meeting = meeting_repo.find_by_share_token(share_token)
    if meeting is None:
        raise not_found
    confirmed = confirmed_repo.find_by_meeting(meeting["id"])
    if confirmed is None:
        raise not_found
    candidate = candidate_repo.find_by_id(confirmed["candidate_id"])
    if candidate is None:
        raise not_found
    members = member_repo.find_active_by_meeting(meeting["id"])
    return PublicScheduleOut(
        meeting_name=meeting["name"],
        description=meeting.get("description"),
        member_count=len(members),
        day_of_week=candidate["day_of_week"],
        start_time=str(candidate["start_time"]),
        end_time=str(candidate["end_time"]),
        confirmed_at=str(confirmed["confirmed_at"]),
    )
