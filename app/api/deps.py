"""FastAPI 의존성 프로바이더.

라우터(컨트롤러)가 repository 를 직접 생성하지 않고 `Depends` 로 주입받도록
한다. Spring 의 `@Autowired` 에 해당하는 역할. DB 클라이언트(`get_supabase`)를
받아 각 Repository 인스턴스를 만들어 넘긴다.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

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
    db: Client = Depends(get_supabase),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """현재 로그인 사용자 주입 (보호된 엔드포인트용).

    프론트가 보낸 Supabase 액세스 토큰(이메일·구글 로그인 공통)을 GoTrue 로
    검증하고, 인증된 유저의 auth_uid 기준으로 우리 users 행을 프로비저닝한다.
    토큰이 없거나 유효하지 않거나 탈퇴 사용자면 401 을 반환한다.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 인증 정보",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    # Supabase JWT 검증 (GoTrue 에 위임) → 인증 유저 정보 획득
    try:
        auth_user = db.auth.get_user(credentials.credentials).user
    except Exception:
        raise unauthorized
    if auth_user is None:
        raise unauthorized

    metadata = auth_user.user_metadata or {}
    display_name = (
        metadata.get("full_name") or metadata.get("name") or auth_user.email or "사용자"
    )

    user = User.from_auth_user(
        auth_uid=auth_user.id,
        email=auth_user.email,
        name=display_name,
        provider=(auth_user.app_metadata or {}).get("provider"),
        repo=user_repo,
    )
    if user.deleted_at is not None:
        raise unauthorized
    return user
