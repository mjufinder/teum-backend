from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.domain.user import User
from app.schemas.auth import ProfileUpdateRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# 로그인/회원가입(이메일·구글)은 프론트 ↔ Supabase Auth 가 직접 처리한다.
# 백엔드는 Supabase 토큰 검증(get_current_user) + 사용자 프로비저닝/온보딩/탈퇴만 담당.


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        user_id=user.user_id,
        name=user.name,
        major=user.major,
        profile_completed=user.profile_completed,
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="내 정보 조회 / 최초 프로비저닝",
    responses={401: {"description": "인증 필요"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """현재 로그인한 사용자 정보 조회 (Supabase 토큰 필요).

    최초 호출 시 Supabase 인증 유저를 우리 users 테이블로 프로비저닝한다.
    (`is_new` 판정은 `profile_completed` 로 프론트에서 온보딩 분기)
    """
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
