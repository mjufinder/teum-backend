from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_notice_repository, require_service_admin
from app.domain.notice import Notice
from app.domain.user import User
from app.repositories.notice_repository import NoticeRepository
from app.schemas.notice import NoticeCreateRequest, NoticeListItem, NoticeListOut, NoticeOut

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
