from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_meeting_member,
    get_meeting_member_repository,
    get_meeting_repository,
)
from app.domain.meeting import Meeting
from app.domain.meeting_member import MeetingMember
from app.domain.user import User
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import MeetingCreateRequest, MeetingOut, MemberOut

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _row_to_meeting_out(row: dict) -> MeetingOut:
    return MeetingOut(
        meeting_id=row["id"],
        name=row["name"],
        description=row.get("description"),
        period_start=row["period_start"],
        period_end=row["period_end"],
        search_start_time=row["search_start_time"],
        search_end_time=row["search_end_time"],
        travel_buffer_min=row["travel_buffer_min"],
        min_duration_min=row["min_duration_min"],
        needs_recalc=row["needs_recalc"],
    )


@router.post(
    "",
    response_model=MeetingOut,
    status_code=status.HTTP_201_CREATED,
    summary="모임 생성",
    responses={401: {"description": "인증 필요"}},
)
def create_meeting(
    payload: MeetingCreateRequest,
    current_user: User = Depends(get_current_user),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> MeetingOut:
    """모임을 생성한다 (MEET-01).

    컨트롤러 → `Meeting.create()` → DB. 생성자는 관리자(ADMIN) 구성원으로
    자동 등록되어 이후 조회/관리 권한을 가진다.
    """
    meeting = Meeting.create(
        name=payload.name,
        description=payload.description,
        period_start=payload.period_start,
        period_end=payload.period_end,
        search_start_time=payload.search_start_time,
        search_end_time=payload.search_end_time,
        min_duration_min=payload.min_duration_min,
        travel_buffer_min=payload.travel_buffer_min,
        repo=meeting_repo,
    )
    MeetingMember.register(
        meeting_id=meeting.meeting_id,
        user_id=current_user.user_id,
        role="ADMIN",
        repo=member_repo,
    )
    return MeetingOut(
        meeting_id=meeting.meeting_id,
        name=meeting.name,
        description=meeting.description,
        period_start=meeting.period_start,
        period_end=meeting.period_end,
        search_start_time=meeting.search_start_time,
        search_end_time=meeting.search_end_time,
        travel_buffer_min=meeting.travel_buffer_min,
        min_duration_min=meeting.min_duration_min,
        needs_recalc=meeting.needs_recalc,
    )


@router.get(
    "",
    response_model=list[MeetingOut],
    summary="내 모임 목록",
    responses={401: {"description": "인증 필요"}},
)
def list_my_meetings(
    current_user: User = Depends(get_current_user),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> list[MeetingOut]:
    """현재 로그인 사용자가 활성 상태로 속한 모임 목록."""
    memberships = member_repo.find_active_by_user(current_user.user_id)
    meeting_ids = [m["meeting_id"] for m in memberships]
    rows = meeting_repo.find_by_ids(meeting_ids)
    return [_row_to_meeting_out(r) for r in rows]


@router.get(
    "/{meeting_id}",
    response_model=MeetingOut,
    summary="모임 상세",
    responses={403: {"description": "구성원 아님"}, 404: {"description": "모임 없음"}},
)
def get_meeting(
    meeting_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> MeetingOut:
    """모임 상세 조회. 해당 모임의 구성원만 조회할 수 있다."""
    row = meeting_repo.find_by_id(meeting_id)
    return _row_to_meeting_out(row)


@router.get(
    "/{meeting_id}/members",
    response_model=list[MemberOut],
    summary="모임 구성원 목록",
    responses={403: {"description": "구성원 아님"}, 404: {"description": "모임 없음"}},
)
def list_members(
    meeting_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> list[MemberOut]:
    """모임의 활성 구성원 목록 (역할/상태 포함). 구성원만 조회 가능."""
    rows = member_repo.find_active_by_meeting(meeting_id)
    return [
        MemberOut(
            member_id=r["id"],
            user_id=r["user_id"],
            role=r["role"],
            status=r["status"],
        )
        for r in rows
    ]
