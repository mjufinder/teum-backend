from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_meeting_member, get_meeting_memo_repository
from app.domain.meeting_member import MeetingMember
from app.domain.meeting_memo import MeetingMemo
from app.repositories.meeting_memo_repository import MeetingMemoRepository
from app.schemas.meeting import MemoCreateRequest, MemoOut, MemoUpdateRequest

router = APIRouter(prefix="/meetings", tags=["meeting-memos"])


def _row_to_memo_out(row: dict) -> MemoOut:
    return MemoOut(
        memo_id=row["id"],
        meeting_id=row["meeting_id"],
        author_user_id=row["author_user_id"],
        content=row["content"],
        created_at=row.get("created_at"),
    )


def _load_editable_memo(
    meeting_id: int,
    memo_id: int,
    member: MeetingMember,
    memo_repo: MeetingMemoRepository,
) -> dict:
    """메모를 조회하고 수정·삭제 권한(작성자 본인 또는 관리자)을 검증한다."""
    row = memo_repo.find_by_id(memo_id)
    if row is None or row["meeting_id"] != meeting_id or row.get("deleted_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="메모를 찾을 수 없습니다."
        )
    if row["author_user_id"] != member.user_id and not member.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="작성자 본인 또는 모임 관리자만 수정·삭제할 수 있습니다.",
        )
    return row


@router.post(
    "/{meeting_id}/memos",
    response_model=MemoOut,
    status_code=status.HTTP_201_CREATED,
    summary="모임 메모 작성",
    responses={403: {"description": "구성원 아님"}, 404: {"description": "모임 없음"}},
)
def create_memo(
    meeting_id: int,
    payload: MemoCreateRequest,
    member: MeetingMember = Depends(get_meeting_member),
    memo_repo: MeetingMemoRepository = Depends(get_meeting_memo_repository),
) -> MemoOut:
    """모임 메모를 작성한다 (MEET-06). 구성원이면 작성 가능."""
    memo = MeetingMemo.write(
        meeting_id=meeting_id,
        author_user_id=member.user_id,
        content=payload.content,
        repo=memo_repo,
    )
    return MemoOut(
        memo_id=memo.memo_id,
        meeting_id=memo.meeting_id,
        author_user_id=memo.author_user_id,
        content=memo.content,
        created_at=None,
    )


@router.get(
    "/{meeting_id}/memos",
    response_model=list[MemoOut],
    summary="모임 메모 목록",
    responses={403: {"description": "구성원 아님"}, 404: {"description": "모임 없음"}},
)
def list_memos(
    meeting_id: int,
    _member: MeetingMember = Depends(get_meeting_member),
    memo_repo: MeetingMemoRepository = Depends(get_meeting_memo_repository),
) -> list[MemoOut]:
    """모임 메모 목록 (삭제되지 않은 것). 구성원만 조회 가능."""
    return [_row_to_memo_out(r) for r in memo_repo.find_by_meeting(meeting_id)]


@router.put(
    "/{meeting_id}/memos/{memo_id}",
    response_model=MemoOut,
    summary="모임 메모 수정",
    responses={403: {"description": "권한 없음"}, 404: {"description": "메모 없음"}},
)
def update_memo(
    meeting_id: int,
    memo_id: int,
    payload: MemoUpdateRequest,
    member: MeetingMember = Depends(get_meeting_member),
    memo_repo: MeetingMemoRepository = Depends(get_meeting_memo_repository),
) -> MemoOut:
    """모임 메모를 수정한다 (MEET-06). 작성자 본인 또는 관리자만."""
    row = _load_editable_memo(meeting_id, memo_id, member, memo_repo)
    memo = MeetingMemo._from_row(row, memo_repo)
    memo.update(content=payload.content)
    return _row_to_memo_out(memo_repo.find_by_id(memo_id))


@router.delete(
    "/{meeting_id}/memos/{memo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="모임 메모 삭제",
    responses={403: {"description": "권한 없음"}, 404: {"description": "메모 없음"}},
)
def delete_memo(
    meeting_id: int,
    memo_id: int,
    member: MeetingMember = Depends(get_meeting_member),
    memo_repo: MeetingMemoRepository = Depends(get_meeting_memo_repository),
) -> None:
    """모임 메모를 삭제한다 (MEET-06, Soft Delete). 작성자 본인 또는 관리자만."""
    row = _load_editable_memo(meeting_id, memo_id, member, memo_repo)
    MeetingMemo._from_row(row, memo_repo).delete()
