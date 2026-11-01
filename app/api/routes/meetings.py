from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_meeting_member,
    get_meeting_member_repository,
    get_meeting_repository,
    get_user_repository,
    require_meeting_admin,
)
from app.domain.meeting import Meeting
from app.domain.meeting_member import MeetingMember
from app.domain.user import User
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.meeting import (
    AddMemberRequest,
    MeetingCreateRequest,
    MeetingOut,
    MemberOut,
)

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


@router.post(
    "/{meeting_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="팀원 추가 (즉시 등록)",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임 없음 / 사용자 없음"},
        409: {"description": "이미 추가된 팀원"},
    },
)
def add_member(
    meeting_id: int,
    payload: AddMemberRequest,
    _admin: MeetingMember = Depends(require_meeting_admin),
    user_repo: UserRepository = Depends(get_user_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> MemberOut:
    """관리자가 이메일로 팀원을 검색해 수락 절차 없이 즉시 등록한다 (MEET-03).

    - 존재하지 않는 사용자 → 404
    - 이미 활성 구성원 → 409
    - 과거 탈퇴(LEFT) 구성원 → 다시 활성화
    """
    target = user_repo.find_by_email(payload.email)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이메일의 사용자를 찾을 수 없습니다. (상대방이 먼저 로그인해야 합니다)",
        )

    existing = member_repo.find_by_meeting_and_user(meeting_id, target["id"])
    if existing is not None:
        if existing["status"] == "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이미 추가된 팀원입니다."
            )
        # 과거 탈퇴한 구성원은 다시 활성화
        row = member_repo.update(existing["id"], {"status": "ACTIVE", "role": "MEMBER"})
        member = MeetingMember._from_row(row, member_repo)
    else:
        member = MeetingMember.register(
            meeting_id=meeting_id,
            user_id=target["id"],
            role="MEMBER",
            repo=member_repo,
        )

    # TODO(MEET-04): 팀원 추가 시 공강 자동 매칭 실행 연결
    return MemberOut(
        member_id=member.member_id,
        user_id=member.user_id,
        role=member.role,
        status=member.status,
    )
