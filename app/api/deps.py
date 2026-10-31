"""FastAPI 의존성 프로바이더.

라우터(컨트롤러)가 repository 를 직접 생성하지 않고 `Depends` 로 주입받도록
한다. Spring 의 `@Autowired` 에 해당하는 역할. DB 클라이언트(`get_supabase`)를
받아 각 Repository 인스턴스를 만들어 넘긴다.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.security import decode_access_token
from app.core.supabase import get_supabase
from app.domain.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.user_repository import UserRepository


def get_user_repository(db: Client = Depends(get_supabase)) -> UserRepository:
    return UserRepository(db)


def get_meeting_repository(db: Client = Depends(get_supabase)) -> MeetingRepository:
    return MeetingRepository(db)


# Authorization: Bearer <token> 헤더에서 토큰을 추출 (Swagger 에 자물쇠 UI 노출)
# auto_error=False: 헤더가 없을 때 403 대신 아래에서 직접 401 로 통일한다.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """현재 로그인 사용자 주입 (보호된 엔드포인트용).

    Bearer 토큰 검증 → 사용자 ID 추출 → DB 조회. 토큰이 없거나 유효하지
    않거나 사용자가 없으면 401 을 반환한다.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 인증 정보",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized

    row = user_repo.find_by_id(user_id)
    if row is None or row.get("deleted_at") is not None:
        raise unauthorized
    return User._from_row(row, user_repo)
