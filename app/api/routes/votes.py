from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_candidate_repository,
    get_candidate_set_repository,
    get_matching_run_repository,
    get_meeting_member,
    get_vote_ballot_repository,
    get_vote_selection_repository,
)
from app.domain.meeting_member import MeetingMember
from app.domain.vote_ballot import VoteBallot
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.candidate_set_repository import CandidateSetRepository
from app.repositories.matching_run_repository import MatchingRunRepository
from app.repositories.vote_ballot_repository import VoteBallotRepository
from app.repositories.vote_selection_repository import VoteSelectionRepository
from app.schemas.vote import BallotOut, VoteRequest

router = APIRouter(prefix="/meetings", tags=["votes"])


def _get_open_set_for_meeting(
    meeting_id: int,
    set_id: int,
    set_repo: CandidateSetRepository,
    run_repo: MatchingRunRepository,
) -> dict:
    """후보 묶음이 해당 모임에 속하고 투표 진행중(OPEN)인지 검증 후 반환."""
    cset = set_repo.find_by_id(set_id)
    if cset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="후보 묶음을 찾을 수 없습니다."
        )
    run = run_repo.find_by_id(cset["run_id"])
    if run is None or run["meeting_id"] != meeting_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="후보 묶음을 찾을 수 없습니다."
        )
    if cset["vote_status"] != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="투표가 종료된 후보 묶음입니다."
        )
    return cset


@router.post(
    "/{meeting_id}/candidate-sets/{set_id}/vote",
    response_model=BallotOut,
    summary="후보 선호 투표",
    responses={
        400: {"description": "잘못된 요청 (후보 선택/없음 동시/누락, 묶음 외 후보)"},
        403: {"description": "구성원 아님"},
        404: {"description": "모임/후보 묶음 없음"},
        409: {"description": "투표 종료된 묶음"},
    },
)
def submit_vote(
    meeting_id: int,
    set_id: int,
    payload: VoteRequest,
    member: MeetingMember = Depends(get_meeting_member),
    set_repo: CandidateSetRepository = Depends(get_candidate_set_repository),
    run_repo: MatchingRunRepository = Depends(get_matching_run_repository),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    ballot_repo: VoteBallotRepository = Depends(get_vote_ballot_repository),
    selection_repo: VoteSelectionRepository = Depends(get_vote_selection_repository),
) -> BallotOut:
    """후보 묶음에 투표한다 (VOTE-01, 구성원만).

    - 선호 후보 선택, 또는 '참석 가능 후보 없음'(no_available) 제출
    - 한 묶음당 1인 1표. 재투표 시 기존 투표를 갱신한다.
    - 다른 묶음의 후보는 선택할 수 없다 (같은 set_id 후보만 허용).
    """
    _get_open_set_for_meeting(meeting_id, set_id, set_repo, run_repo)

    # 입력 검증: '없음'과 후보 선택은 동시 불가, 둘 다 비어도 안 됨
    if payload.no_available and payload.candidate_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'참석 가능 후보 없음'과 후보 선택은 동시에 제출할 수 없습니다.",
        )
    if not payload.no_available and not payload.candidate_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="후보를 선택하거나 '참석 가능 후보 없음'을 제출하세요.",
        )

    # 후보가 이 묶음에 속하는지 검증
    if payload.candidate_ids:
        valid_ids = {c["id"] for c in candidate_repo.find_by_set(set_id)}
        invalid = [cid for cid in payload.candidate_ids if cid not in valid_ids]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이 후보 묶음에 속하지 않은 후보입니다: {invalid}",
            )

    # 1인 1표: 기존 투표지가 있으면 갱신, 없으면 생성
    existing = ballot_repo.find_by_set_and_member(set_id, member.member_id)
    if existing is not None:
        ballot = VoteBallot._from_row(existing, ballot_repo, selection_repo)
        if payload.no_available:
            ballot.mark_no_available()
        else:
            ballot.update(candidate_ids=payload.candidate_ids)
    else:
        ballot = VoteBallot.submit(
            set_id=set_id,
            member_id=member.member_id,
            candidate_ids=[] if payload.no_available else payload.candidate_ids,
            repo=ballot_repo,
            selection_repo=selection_repo,
        )
        if payload.no_available:
            ballot.mark_no_available()

    selected = [s["candidate_id"] for s in selection_repo.find_by_ballot(ballot.ballot_id)]
    return BallotOut(
        ballot_id=ballot.ballot_id,
        set_id=set_id,
        member_id=member.member_id,
        no_available=ballot.no_available,
        candidate_ids=selected,
    )
