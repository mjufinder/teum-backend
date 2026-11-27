from fastapi import APIRouter, Depends, status

from app.api.deps import get_notice_repository, require_service_admin
from app.domain.notice import Notice
from app.domain.user import User
from app.repositories.notice_repository import NoticeRepository
from app.schemas.notice import NoticeCreateRequest, NoticeOut

router = APIRouter(prefix="/notices", tags=["notices"])


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
