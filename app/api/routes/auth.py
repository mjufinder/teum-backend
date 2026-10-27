from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_user_repository
from app.domain.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _exchange_oauth_code(provider: str, code: str) -> tuple[str, str]:
    """OAuth 인가 코드 → (provider_user_id, name).

    > ⚠️ 실제 provider 별 토큰 교환/프로필 조회는 아직 미구현(개발용 스텁).
    > 지금은 code 를 그대로 식별자로 사용해 로그인 흐름만 연결한다.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 code"
        )
    # TODO: provider 별 OAuth 2.0 토큰 교환 → 사용자 프로필 조회
    return f"{provider}:{code}", "사용자"


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="소셜 로그인",
    responses={
        400: {"description": "잘못된 요청 (지원하지 않는 provider 등)"},
        401: {"description": "인증 실패 (유효하지 않은 code)"},
    },
)
def login(
    payload: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository),
) -> LoginResponse:
    """OAuth 2.0 기반 소셜 로그인 / 회원가입 (AUTH-01).

    - 기존 계정이면 `is_new=false` → 메인으로 이동
    - 신규/온보딩 미완료 계정이면 `is_new=true` → 온보딩 단계로 이동

    컨트롤러 → `User.social_login()`(domain) → `UserRepository`(DB) 흐름으로 처리.
    """
    provider_user_id, name = _exchange_oauth_code(payload.provider, payload.code)

    user = User.social_login(
        provider=payload.provider,
        provider_user_id=provider_user_id,
        name=name,
        repo=user_repo,
    )

    # TODO: 실제 JWT 액세스 토큰 발급
    return LoginResponse(
        access_token="sample.jwt.token",
        token_type="bearer",
        is_new=user.is_new(),
        user=UserOut(
            user_id=user.user_id,
            name=user.name,
            major=user.major,
            profile_completed=user.profile_completed,
        ),
    )
