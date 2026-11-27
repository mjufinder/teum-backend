from typing import Literal

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    """클라이언트에 노출하는 사용자 정보."""

    user_id: int = Field(..., description="사용자 고유 번호", examples=[1])
    name: str = Field(..., description="사용자 이름", examples=["한규진"])
    role: Literal["USER", "ADMIN"] = Field("USER", description="서비스 권한")
    major: str | None = Field(
        None, description="전공 (온보딩 전이면 null)", examples=["컴퓨터공학전공"]
    )
    profile_completed: bool = Field(
        ..., description="프로필+시간표 등록 완료 여부. false면 온보딩 필요", examples=[False]
    )


class ProfileUpdateRequest(BaseModel):
    """온보딩/마이페이지 프로필 수정 요청. (AUTH-02)"""

    name: str | None = Field(
        None, description="사용자 이름", examples=["한규진"]
    )
    major: str | None = Field(
        None, description="전공", examples=["컴퓨터공학전공"]
    )
