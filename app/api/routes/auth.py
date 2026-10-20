from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="소셜 로그인",
    responses={
        400: {"description": "잘못된 요청 (지원하지 않는 provider 등)"},
        401: {"description": "인증 실패 (유효하지 않은 code)"},
    },
)
def login(payload: LoginRequest) -> LoginResponse:
    """OAuth 2.0 기반 소셜 로그인 / 회원가입 (AUTH-01).

    - 기존 계정이면 `is_new=false` → 메인으로 이동
    - 신규 계정이면 `is_new=true` → 온보딩(프로필+시간표 등록) 단계로 이동

    > ⚠️ 샘플 스텁입니다. 실제 OAuth 토큰 교환/검증은 아직 구현되지 않았습니다.
    > Swagger 자동 명세가 어떻게 생성되는지 보여주기 위한 예시 라우터입니다.
    """
    # 샘플: code 가 비어 있으면 인증 실패로 간주
    if not payload.code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 code"
        )

    # TODO: provider 별 OAuth 토큰 교환 → 사용자 조회/생성 → JWT 발급
    return LoginResponse(
        access_token="sample.jwt.token",
        token_type="bearer",
        is_new=True,
        user=UserOut(
            user_id=1,
            name="한규진",
            major=None,
            profile_completed=False,
        ),
    )
