from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.meeting import MemberOut


class InviteOut(BaseModel):
    """초대 링크 발급/조회 결과. (MEET-08)

    백엔드는 프론트 주소를 모르므로 경로만 돌려주고, 전체 URL 과 QR 은 프론트가 만든다.
    """

    invite_code: str = Field(..., description="초대 코드", examples=["Xk2p9QaB7mE"])
    invite_path: str = Field(
        ..., description="프론트 참가 페이지 경로", examples=["/invite/Xk2p9QaB7mE"]
    )
    expires_at: datetime = Field(..., description="만료 시각 (UTC)")


class InvitePreviewOut(BaseModel):
    """초대 링크로 들어온 사람에게 보여 줄 모임 요약. 로그인 없이 조회한다."""

    meeting_id: int = Field(..., description="모임 고유 번호", examples=[1])
    meeting_name: str = Field(..., description="모임 이름", examples=["캡스톤 2조 정기회의"])
    description: str | None = Field(None, description="모임 설명")
    member_count: int = Field(..., description="현재 활성 구성원 수", examples=[3])
    expires_at: datetime = Field(..., description="초대 만료 시각 (UTC)")


class InviteJoinOut(BaseModel):
    """초대 링크로 참가한 결과."""

    meeting_id: int = Field(..., description="참가한 모임 번호", examples=[1])
    already_member: bool = Field(
        ..., description="이미 구성원이어서 새로 등록하지 않았는지 여부", examples=[False]
    )
    member: MemberOut
