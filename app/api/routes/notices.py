from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import get_notice_repository, require_service_admin
from app.domain.notice import Notice
from app.domain.user import User
from app.repositories.notice_repository import NoticeRepository
from app.schemas.notice import (
    NoticeCreateRequest, NoticeListItem, NoticeListOut, NoticeOut, NoticeUpdateRequest,
)

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=NoticeListOut, summary="공지 목록 조회")
def list_notices(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 공지 수"),
    repo: NoticeRepository = Depends(get_notice_repository),
) -> NoticeListOut:
    """로그인 없이 공지를 조회한다. 삭제된 공지를 제외하고 최신순으로 반환한다."""
    rows, total = repo.find_page(page=page, page_size=page_size)
    return NoticeListOut(
        items=[NoticeListItem(
            notice_id=row["id"], author_user_id=row["author_user_id"],
            title=row["title"], created_at=row["created_at"], updated_at=row["updated_at"],
        ) for row in rows],
        total=total, page=page, page_size=page_size,
    )


@router.get(
    "/{notice_id}", response_model=NoticeOut, summary="공지 상세 조회",
    responses={404: {"description": "공지가 없거나 삭제됨"}},
)
def read_notice(
    notice_id: int = Path(..., ge=1, le=9223372036854775807, description="공지 ID"),
    repo: NoticeRepository = Depends(get_notice_repository),
) -> NoticeOut:
    """로그인 없이 공지 본문을 조회한다. 삭제된 공지는 조회할 수 없다."""
    row = repo.find_by_id(notice_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    return NoticeOut(
        notice_id=row["id"], author_user_id=row["author_user_id"],
        title=row["title"], content=row["content"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


@router.post(
    "", response_model=NoticeOut, status_code=status.HTTP_201_CREATED,
    summary="공지 작성",
    responses={401: {"description": "인증 필요"}, 403: {"description": "관리자 권한 필요"}},
)
def create_notice(
    payload: NoticeCreateRequest,
    admin: User = Depends(require_service_admin),
    repo: NoticeRepository = Depends(get_notice_repository),
) -> NoticeOut:
    """서비스 관리자만 공지를 작성한다. 시간표·프로필 등록은 필요하지 않다."""
    notice = Notice.write(
        author_user_id=admin.user_id, title=payload.title, content=payload.content, repo=repo,
    )
    return NoticeOut.model_validate(notice, from_attributes=True)


@router.delete(
    "/{notice_id}", status_code=status.HTTP_204_NO_CONTENT, summary="공지 삭제",
    responses={
        401: {"description": "인증 필요"},
        403: {"description": "관리자 권한 필요"},
        404: {"description": "공지가 없거나 이미 삭제됨"},
    },
)
def delete_notice(
    notice_id: int = Path(..., ge=1, le=9223372036854775807, description="공지 ID"),
    _admin: User = Depends(require_service_admin),
    repo: NoticeRepository = Depends(get_notice_repository),
) -> None:
    """관리자는 다른 관리자의 공지도 논리 삭제할 수 있다. 시간표 등록은 불필요하다."""
    if not Notice.delete(notice_id=notice_id, repo=repo):
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")


@router.patch(
    "/{notice_id}", response_model=NoticeOut, summary="공지 수정",
    responses={
        401: {"description": "인증 필요"},
        403: {"description": "관리자 권한 필요"},
        404: {"description": "공지가 없거나 삭제됨"},
    },
)
def update_notice(
    payload: NoticeUpdateRequest,
    notice_id: int = Path(..., ge=1, le=9223372036854775807, description="공지 ID"),
    _admin: User = Depends(require_service_admin),
    repo: NoticeRepository = Depends(get_notice_repository),
) -> NoticeOut:
    """관리자는 다른 관리자의 공지도 수정할 수 있다. 생략된 필드는 유지한다."""
    notice = Notice.update(
        notice_id=notice_id, changes=payload.model_dump(exclude_unset=True), repo=repo,
    )
    if notice is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    return NoticeOut.model_validate(notice, from_attributes=True)
