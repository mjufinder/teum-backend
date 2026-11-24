from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_candidate_set_repository,
    get_current_user,
    get_matching_run_repository,
    get_meeting_member,
    get_meeting_member_repository,
    get_meeting_repository,
    get_timetable_repository,
    get_user_repository,
    get_recommendation_repository,
    require_meeting_admin,
)
from app.domain.meeting import Meeting
from app.domain.meeting_member import MeetingMember
from app.domain.user import User
from app.repositories.candidate_set_repository import CandidateSetRepository
from app.repositories.matching_run_repository import MatchingRunRepository
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.timetable_repository import TimetableRepository
from app.repositories.user_repository import UserRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.meeting_matching_service import add_member_and_match
from app.schemas.meeting import (
    AddMemberRequest,
    MeetingCreateRequest,
    MeetingOut,
    MeetingUpdateRequest,
    MemberOut,
    TransferAdminRequest,
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


@router.put(
    "/{meeting_id}",
    response_model=MeetingOut,
    summary="모임 정보·조건 수정",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임 없음"},
    },
)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdateRequest,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    run_repo: MatchingRunRepository = Depends(get_matching_run_repository),
    set_repo: CandidateSetRepository = Depends(get_candidate_set_repository),
) -> MeetingOut:
    """모임 이름/설명·공강 탐색 조건을 수정한다 (MEET-02, 관리자만).

    - 이름/설명 변경은 재계산과 무관
    - 조건(최소 회의시간·탐색 시간대·이동 여유) 변경 시 `needs_recalc` 를 켜고,
      진행 중인 후보 묶음(투표)을 폐기한다.
    """
    meeting = Meeting._from_row(meeting_repo.find_by_id(meeting_id), meeting_repo)

    if payload.name is not None or payload.description is not None:
        meeting.update_info(name=payload.name, description=payload.description)

    condition_changed = any(
        v is not None
        for v in (
            payload.min_duration_min,
            payload.search_start_time,
            payload.search_end_time,
            payload.travel_buffer_min,
        )
    )
    if condition_changed:
        meeting.update_conditions(
            min_duration_min=payload.min_duration_min,
            search_start_time=payload.search_start_time,
            search_end_time=payload.search_end_time,
            travel_buffer_min=payload.travel_buffer_min,
        )
        # 조건이 바뀌면 진행 중인 투표(후보 묶음)를 폐기
        run_ids = run_repo.find_ids_by_meeting(meeting_id)
        set_repo.discard_open_by_runs(run_ids)

    return _row_to_meeting_out(meeting_repo.find_by_id(meeting_id))


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
    timetable_repo: TimetableRepository = Depends(get_timetable_repository),
) -> list[MemberOut]:
    """모임의 활성 구성원 목록 (역할/상태/시간표 등록 여부 포함). 구성원만 조회 가능."""
    rows = member_repo.find_active_by_meeting(meeting_id)
    timetables = timetable_repo.find_by_users([r["user_id"] for r in rows])
    registered_users = {
        t["user_id"]
        for t in timetables
        if t.get("class_bits") is not None and t.get("manual_bits") is not None
    }
    return [
        MemberOut(
            member_id=r["id"],
            user_id=r["user_id"],
            role=r["role"],
            status=r["status"],
            has_timetable=r["user_id"] in registered_users,
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
        503: {"description": "추가 또는 추천 갱신 실패. 같은 요청으로 재시도 가능"},
    },
)
def add_member(
    meeting_id: int,
    payload: AddMemberRequest,
    _admin: MeetingMember = Depends(require_meeting_admin),
    user_repo: UserRepository = Depends(get_user_repository),
    recommendation_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> MemberOut:
    """관리자가 이메일로 팀원을 검색해 수락 절차 없이 즉시 등록한다 (MEET-03).

    - 존재하지 않는 사용자 → 404
    - 이미 활성 구성원 → 409 (재계산이 미완료인 경우 재시도)
    - 과거 탈퇴(LEFT) 구성원 → 다시 활성화
    """
    target = user_repo.find_by_email(payload.email)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이메일의 사용자를 찾을 수 없습니다. (상대방이 먼저 로그인해야 합니다)",
        )

    return add_member_and_match(meeting_id, target["id"], recommendation_repo)


@router.post(
    "/{meeting_id}/transfer-admin",
    response_model=list[MemberOut],
    summary="관리자 권한 위임",
    responses={
        400: {"description": "잘못된 대상 (본인 등)"},
        403: {"description": "관리자 아님"},
        404: {"description": "대상 구성원 없음"},
    },
)
def transfer_admin(
    meeting_id: int,
    payload: TransferAdminRequest,
    admin: MeetingMember = Depends(require_meeting_admin),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> list[MemberOut]:
    """관리자 권한을 다른 활성 구성원에게 위임한다 (MEET-05, 관리자만).

    위임 후 기존 관리자는 일반 구성원(MEMBER)이 된다. (관리자 1명 유지)
    """
    if payload.target_user_id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="본인에게는 위임할 수 없습니다."
        )
    target_row = member_repo.find_by_meeting_and_user(meeting_id, payload.target_user_id)
    if target_row is None or target_row["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="대상 구성원을 찾을 수 없습니다."
        )
    target = MeetingMember._from_row(target_row, member_repo)
    admin.transfer_admin(target)

    rows = member_repo.find_active_by_meeting(meeting_id)
    return [
        MemberOut(member_id=r["id"], user_id=r["user_id"], role=r["role"], status=r["status"])
        for r in rows
    ]


@router.delete(
    "/{meeting_id}/members/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="모임 탈퇴",
    responses={
        403: {"description": "구성원 아님"},
        404: {"description": "모임 없음"},
        409: {"description": "관리자는 위임/삭제 후 탈퇴 가능"},
    },
)
def leave_meeting(
    meeting_id: int,
    member: MeetingMember = Depends(get_meeting_member),
) -> None:
    """모임에서 탈퇴한다 (MEET-05).

    관리자는 권한 위임 또는 모임 삭제 전까지 탈퇴할 수 없다.
    """
    if member.is_admin():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="관리자는 권한 위임 또는 모임 삭제 후 탈퇴할 수 있습니다.",
        )
    member.leave()


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="모임 삭제",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임 없음"},
    },
)
def delete_meeting(
    meeting_id: int,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> None:
    """모임을 삭제한다 (MEET-05, 관리자만). Soft Delete 로 처리한다."""
    meeting = Meeting._from_row(meeting_repo.find_by_id(meeting_id), meeting_repo)
    meeting.delete()
