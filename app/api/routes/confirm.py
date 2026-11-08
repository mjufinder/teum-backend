import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_candidate_repository,
    get_candidate_set_repository,
    get_confirmed_schedule_repository,
    get_matching_run_repository,
    get_meeting_member_repository,
    get_timetable_repository,
    require_meeting_admin,
)
from app.domain.confirmed_schedule import ConfirmedSchedule
from app.domain.meeting_member import MeetingMember
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.candidate_set_repository import CandidateSetRepository
from app.repositories.confirmed_schedule_repository import ConfirmedScheduleRepository
from app.repositories.matching_run_repository import MatchingRunRepository
from app.repositories.meeting_member_repository import MeetingMemberRepository
from app.repositories.timetable_repository import TimetableRepository
from app.schemas.vote import ConfirmRequest, ConfirmResult

router = APIRouter(prefix="/meetings", tags=["confirm"])


def _parse_ts(value) -> datetime:
    """Supabase timestamptz 문자열을 datetime 으로 변환."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


@router.post(
    "/{meeting_id}/confirm",
    response_model=ConfirmResult,
    summary="일정 최종 확정 (+확정 직전 재검사)",
    responses={
        403: {"description": "관리자 아님"},
        404: {"description": "모임/후보 없음"},
        409: {"description": "이미 확정된 모임"},
    },
)
def confirm_schedule(
    meeting_id: int,
    payload: ConfirmRequest,
    _admin: MeetingMember = Depends(require_meeting_admin),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    set_repo: CandidateSetRepository = Depends(get_candidate_set_repository),
    run_repo: MatchingRunRepository = Depends(get_matching_run_repository),
    member_repo: MeetingMemberRepository = Depends(get_meeting_member_repository),
    timetable_repo: TimetableRepository = Depends(get_timetable_repository),
    confirmed_repo: ConfirmedScheduleRepository = Depends(get_confirmed_schedule_repository),
) -> ConfirmResult:
    """최종 후보로 모임 일정을 확정한다 (VOTE-03, 관리자만).

    확정 직전 재검사: 후보를 계산한 매칭 이후 팀원 시간표가 바뀌었는지 확인한다.
    변경이 감지되면 확정하지 않고 재계산을 안내한다. (모임당 확정 1개)
    """
    # 후보가 이 모임에 속하는지 검증 (candidate → set → run → meeting)
    candidate = candidate_repo.find_by_id(payload.candidate_id)
    cset = set_repo.find_by_id(candidate["set_id"]) if candidate else None
    run = run_repo.find_by_id(cset["run_id"]) if cset else None
    if run is None or run["meeting_id"] != meeting_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="후보를 찾을 수 없습니다. (이 모임의 후보가 아닙니다)",
        )

    # 모임당 확정 1개
    if confirmed_repo.find_by_meeting(meeting_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 확정된 모임입니다."
        )

    # 확정 직전 재검사: 매칭 계산 이후 시간표 변경 여부
    calculated_at = _parse_ts(run["calculated_at"])
    members = member_repo.find_active_by_meeting(meeting_id)
    changed: list[int] = []
    input_count = 0
    state_parts: list[str] = []
    for m in members:
        tt = timetable_repo.find_by_user(m["user_id"])
        if tt is None:
            continue
        input_count += 1
        state_parts.append(f"{m['user_id']}:{tt.get('updated_at')}")
        if _parse_ts(tt["updated_at"]) > calculated_at:
            changed.append(m["user_id"])

    if changed:
        return ConfirmResult(
            confirmed=False,
            recheck_passed=False,
            meeting_id=meeting_id,
            candidate_id=payload.candidate_id,
            confirmed_id=None,
            detail="팀원 시간표가 변경되어 재검사에 실패했습니다. 재계산 후 다시 확정하세요.",
        )

    # 재검사 통과 → 재검사 이력(PRE_CONFIRM_RECHECK) 기록 후 확정
    recheck_run = run_repo.insert(
        {
            "meeting_id": meeting_id,
            "trigger_type": "PRE_CONFIRM_RECHECK",
            "cond_snapshot": {},
            "total_member_count": len(members),
            "timetable_input_count": input_count,
            "input_hash": hashlib.sha256(",".join(state_parts).encode()).hexdigest(),
        }
    )
    confirmed = ConfirmedSchedule.confirm(
        meeting_id=meeting_id,
        candidate_id=payload.candidate_id,
        recheck_run_id=recheck_run["id"],
        repo=confirmed_repo,
        candidate_repo=candidate_repo,
    )
    return ConfirmResult(
        confirmed=True,
        recheck_passed=True,
        meeting_id=meeting_id,
        candidate_id=payload.candidate_id,
        confirmed_id=confirmed.confirmed_id,
        detail="일정이 확정되었습니다.",
    )
