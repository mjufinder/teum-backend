"""초대 링크(QR) 기반 모임 참가 (MEET-08).

기존 이메일 팀원 추가(MEET-03)는 그대로 두고, 초대 코드로 스스로 참가하는 경로를 더한다.
실제 등록과 추천 재계산은 팀원 추가와 같은 `add_member_and_match` 를 쓴다.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import (
    get_current_user,
    get_meeting_member_repository,
    get_meeting_repository,
    get_recommendation_repository,
    require_meeting_admin,
)
from app.domain.meeting import Meeting
from app.domain.meeting_member import MeetingMember
from app.domain.user import User
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.invite import InviteJoinOut, InviteOut, InvitePreviewOut
from app.schemas.meeting import MemberOut
from app.services.meeting_matching_service import add_member_and_match

# 발급/조회/해제(관리자, 인증)와 미리보기(비회원)·참가(인증)를 한 라우터에 둔다.
router = APIRouter(tags=["invites"])


def _to_invite_out(meeting: Meeting) -> InviteOut:
    return InviteOut(
        invite_code=meeting.invite_code,
        invite_path=f"/invite/{meeting.invite_code}",
        expires_at=meeting.invite_expiry(),
    )


def _load_meeting(meeting_id: int, meeting_repo: MeetingRepository) -> Meeting:
    row = meeting_repo.find_by_id(meeting_id)
    if row is None or row.get("deleted_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다."
        )
    return Meeting._from_row(row, meeting_repo)


def _load_by_valid_code(invite_code: str, meeting_repo: MeetingRepository) -> Meeting:
    """초대 코드로 모임을 찾는다. 없으면 404, 만료됐으면 410."""
    row = meeting_repo.find_by_invite_code(invite_code)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유효하지 않은 초대 링크입니다."
        )
    meeting = Meeting._from_row(row, meeting_repo)
    if not meeting.is_invite_valid():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="만료된 초대 링크입니다. 모임 관리자에게 새 링크를 요청하세요.",
        )
    return meeting


@router.post(
    "/meetings/{meeting_id}/invite",
    response_model=InviteOut,
    summary="초대 링크 발급/재발급",
    responses={403: {"description": "관리자 아님"}, 404: {"description": "모임 없음"}},
)
def issue_invite(
    meeting_id: int,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> InviteOut:
    """새 초대 코드를 발급한다. 이미 있으면 바꾸고 이전 링크는 무효가 된다 (관리자만, 7일 유효)."""
    meeting = _load_meeting(meeting_id, meeting_repo)
    meeting.create_invite()
    return _to_invite_out(meeting)


@router.get(
    "/meetings/{meeting_id}/invite",
    response_model=InviteOut,
    summary="현재 초대 링크 조회",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임 없음 / 유효한 초대 링크 없음"},
    },
)
def read_invite(
    meeting_id: int,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> InviteOut:
    """발급해 둔 초대 링크를 조회한다. 없거나 만료됐으면 404 (관리자만)."""
    meeting = _load_meeting(meeting_id, meeting_repo)
    if not meeting.is_invite_valid():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유효한 초대 링크가 없습니다."
        )
    return _to_invite_out(meeting)


@router.delete(
    "/meetings/{meeting_id}/invite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="초대 링크 끊기",
    responses={403: {"description": "관리자 아님"}, 404: {"description": "모임 없음"}},
)
def revoke_invite(
    meeting_id: int,
    _admin: MeetingMember = Depends(require_meeting_admin),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> Response:
    """초대 코드를 지워 기존 링크·QR 로 더 이상 참가할 수 없게 한다 (관리자만)."""
    _load_meeting(meeting_id, meeting_repo).revoke_invite()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/invites/{invite_code}",
    response_model=InvitePreviewOut,
    summary="초대 링크 미리보기 (비회원)",
    responses={404: {"description": "유효하지 않은 링크"}, 410: {"description": "만료된 링크"}},
)
def preview_invite(
    invite_code: str,
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
) -> InvitePreviewOut:
    """초대받은 사람이 로그인 전에 어떤 모임인지 확인할 수 있게 요약만 돌려준다."""
    meeting = _load_by_valid_code(invite_code, meeting_repo)
    return InvitePreviewOut(
        meeting_id=meeting.meeting_id,
        meeting_name=meeting.name,
        description=meeting.description,
        member_count=len(member_repo.find_active_by_meeting(meeting.meeting_id)),
        expires_at=meeting.invite_expiry(),
    )


@router.post(
    "/invites/{invite_code}/join",
    response_model=InviteJoinOut,
    summary="초대 링크로 모임 참가",
    responses={
        401: {"description": "인증 필요"},
        404: {"description": "유효하지 않은 링크"},
        410: {"description": "만료된 링크"},
        503: {"description": "참가 또는 추천 갱신 실패. 같은 요청으로 재시도 가능"},
    },
)
def join_by_invite(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
    recommendation_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> InviteJoinOut:
    """로그인한 사용자가 초대 코드로 직접 참가한다.

    - 이미 활성 구성원이면 등록 없이 already_member=True 로 돌려준다.
    - 과거 탈퇴(LEFT) 구성원은 다시 활성화된다 (팀원 추가와 같은 규칙).
    - 등록은 됐지만 추천 계산만 실패하면 503. 같은 요청을 다시 보내면 계산만 재시도한다.
    """
    meeting = _load_by_valid_code(invite_code, meeting_repo)
    row = member_repo.find_by_meeting_and_user(meeting.meeting_id, current_user.user_id)
    # needs_recalc 이면 직전 참가의 계산이 실패했을 수 있으므로 다시 계산하도록 넘긴다.
    if row is not None and row["status"] == "ACTIVE" and not meeting.needs_recalc:
        return InviteJoinOut(
            meeting_id=meeting.meeting_id,
            already_member=True,
            member=MemberOut(
                member_id=row["id"], user_id=row["user_id"],
                role=row["role"], status=row["status"],
            ),
        )

    member = add_member_and_match(
        meeting.meeting_id, current_user.user_id, recommendation_repo
    )
    return InviteJoinOut(meeting_id=meeting.meeting_id, already_member=False, member=member)
