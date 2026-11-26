from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_user_repository
from app.domain.user import User
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search")
def search_users(
    q: str = Query(..., min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> list[dict]:
    """이메일 prefix로 사용자를 검색한다 (팀원 초대 자동완성).

    - 본인은 결과에서 제외한다.
    - 최대 7명까지 반환한다.
    """
    results = user_repo.search_by_email_prefix(q)
    return [r for r in results if r["id"] != current_user.user_id]
