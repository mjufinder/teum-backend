from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_user_repository
from app.core.security import create_access_token
from app.domain.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _exchange_oauth_code(provider: str, code: str) -> tuple[str, str]:
    """OAuth 인가 코드 → (provider_user_id, name).

    > ⚠️ 실제 provider 별 토큰 교환/프로필 조회는 아직 미구현(개발용 스텁).
    > provider 자격증명(client id/secret) 확보 후 httpx 로 토큰 교환 예정.
    > 지금은 code 를 그대로 식별자로 사용해 로그인 흐름만 연결한다.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 code"
        )
    # TODO: provider 별 OAuth 2.0 토큰 교환 → 사용자 프로필 조회
    return f"{provider}:{code}", "사용자"


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        user_id=user.user_id,
        name=user.name,
        major=user.major,
        profile_completed=user.profile_completed,
    )


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

    컨트롤러 → `User.social_login()`(domain) → `UserRepository`(DB) 흐름으로 처리하고,
    로그인 성공 시 자체 JWT 액세스 토큰을 발급한다.
    """
    provider_user_id, name = _exchange_oauth_code(payload.provider, payload.code)

    user = User.social_login(
        provider=payload.provider,
        provider_user_id=provider_user_id,
        name=name,
        repo=user_repo,
    )

    return LoginResponse(
        access_token=create_access_token(user.user_id),
        token_type="bearer",
        is_new=user.is_new(),
        user=_to_user_out(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="내 정보 조회",
    responses={401: {"description": "인증 필요"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """현재 로그인한 사용자 정보 조회 (토큰 필요)."""
    return _to_user_out(current_user)


@router.put(
    "/profile",
    response_model=UserOut,
    summary="프로필 등록/수정 (온보딩)",
    responses={401: {"description": "인증 필요"}},
)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """이름/전공 등록·수정 (AUTH-02 온보딩).

    이름과 전공이 모두 채워지면 `profile_completed=true` 로 전환된다.
    (시간표 등록은 TIME 영역에서 별도 처리)
    """
    current_user.update_profile(name=payload.name, major=payload.major)
    return _to_user_out(current_user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
    responses={401: {"description": "인증 필요"}},
)
def withdraw(current_user: User = Depends(get_current_user)) -> None:
    """회원 탈퇴 (AUTH-03). Soft Delete 로 처리한다."""
    current_user.withdraw()
