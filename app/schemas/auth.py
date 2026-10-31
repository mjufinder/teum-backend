from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """소셜 로그인 요청. OAuth 2.0 인가 코드를 전달한다. (AUTH-01)"""

    provider: Literal["google", "kakao", "naver"] = Field(
        ..., description="소셜 로그인 제공자", examples=["google"]
    )
    code: str = Field(
        ...,
        description="OAuth 2.0 인가 코드 (프론트 리다이렉트로 수신한 값)",
        examples=["4/0AeanS0b..."],
    )


class UserOut(BaseModel):
    """클라이언트에 노출하는 사용자 정보."""

    user_id: int = Field(..., description="사용자 고유 번호", examples=[1])
    name: str = Field(..., description="사용자 이름", examples=["한규진"])
    major: str | None = Field(
        None, description="전공 (온보딩 전이면 null)", examples=["컴퓨터공학전공"]
    )
    profile_completed: bool = Field(
        ..., description="프로필+시간표 등록 완료 여부. false면 온보딩 필요", examples=[False]
    )


class LoginResponse(BaseModel):
    """로그인 결과. 신규 계정이면 is_new=true 로 온보딩으로 유도한다."""

    access_token: str = Field(..., description="JWT 액세스 토큰")
    token_type: str = Field("bearer", examples=["bearer"])
    is_new: bool = Field(
        ..., description="신규 가입 여부 (true면 온보딩 단계로 이동)", examples=[True]
    )
    user: UserOut


class ProfileUpdateRequest(BaseModel):
    """온보딩/마이페이지 프로필 수정 요청. (AUTH-02)"""

    name: str | None = Field(
        None, description="사용자 이름", examples=["한규진"]
    )
    major: str | None = Field(
        None, description="전공", examples=["컴퓨터공학전공"]
    )
