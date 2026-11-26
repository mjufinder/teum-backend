from datetime import date, time

from pydantic import BaseModel, Field


class MeetingCreateRequest(BaseModel):
    """모임 생성 요청. 기본 정보 + 공강 탐색 조건을 담는다."""

    name: str = Field(..., description="모임 이름", examples=["캡스톤 2조 정기회의"])
    description: str | None = Field(
        None, description="모임 설명", examples=["주간 진행상황 공유"]
    )
    period_start: date = Field(..., description="모임 기간 시작 (주간 공강 추천에는 사용하지 않음)", examples=["2026-11-01"])
    period_end: date = Field(..., description="모임 기간 종료 (주간 공강 추천에는 사용하지 않음)", examples=["2026-11-30"])
    search_start_time: time = Field(
        ..., description="하루 탐색 범위 시작", examples=["09:00"]
    )
    search_end_time: time = Field(
        ..., description="하루 탐색 범위 종료", examples=["18:00"]
    )
    min_duration_min: int = Field(
        ..., gt=0, description="최소 회의 시간(분)", examples=[60]
    )
    travel_buffer_min: int = Field(
        0, ge=0, description="이동 여유 시간(분)", examples=[10]
    )


class ConfirmedSlotOut(BaseModel):
    """모임에 확정된 일정 요약."""

    candidate_id: int
    day_of_week: int
    start_time: time
    end_time: time
    confirmed_at: str


class MeetingOut(BaseModel):
    """생성/조회된 모임 정보."""

    meeting_id: int = Field(..., description="모임 고유 번호", examples=[1])
    name: str
    description: str | None = None
    period_start: date
    period_end: date
    search_start_time: time
    search_end_time: time
    travel_buffer_min: int
    min_duration_min: int
    needs_recalc: bool = Field(..., description="재계산 필요 상태", examples=[False])
    share_token: str | None = Field(None, description="발급된 외부 공유 토큰")
    invite_code: str | None = Field(None, description="발급된 모임 초대 코드")
    confirmed_schedule: ConfirmedSlotOut | None = None


class MeetingUpdateRequest(BaseModel):
    """모임 정보·조건 수정 요청. 전달된 필드만 수정한다. (MEET-02)"""

    name: str | None = Field(None, description="모임 이름", examples=["이름 변경"])
    description: str | None = Field(None, description="모임 설명")
    min_duration_min: int | None = Field(
        None, gt=0, description="최소 회의 시간(분)", examples=[90]
    )
    search_start_time: time | None = Field(None, description="하루 탐색 범위 시작")
    search_end_time: time | None = Field(None, description="하루 탐색 범위 종료")
    travel_buffer_min: int | None = Field(
        None, ge=0, description="이동 여유 시간(분)"
    )


class MemberOut(BaseModel):
    """모임 구성원 정보."""

    member_id: int = Field(..., description="구성원 고유 번호", examples=[1])
    user_id: int = Field(..., description="사용자 번호", examples=[1])
    role: str = Field(..., description="ADMIN / MEMBER", examples=["ADMIN"])
    status: str = Field(..., description="ACTIVE / LEFT", examples=["ACTIVE"])
    has_timetable: bool = Field(False, description="시간표 등록 여부")


class AddMemberRequest(BaseModel):
    """팀원 추가 요청. 추가할 사용자의 이메일로 검색해 즉시 등록한다. (MEET-03)"""

    email: str = Field(
        ..., description="추가할 팀원의 이메일", examples=["teammate@example.com"]
    )


class TransferAdminRequest(BaseModel):
    """관리자 권한 위임 요청. 대상 구성원의 user_id 를 지정한다. (MEET-05)"""

    target_user_id: int = Field(
        ..., description="권한을 넘길 구성원의 사용자 번호", examples=[2]
    )


class MemoCreateRequest(BaseModel):
    """모임 메모 작성 요청. (MEET-06)"""

    content: str = Field(..., description="메모 내용", examples=["이번 주 금요일 발표 리허설"])


class MemoUpdateRequest(BaseModel):
    """모임 메모 수정 요청. (MEET-06)"""

    content: str = Field(..., description="수정할 메모 내용", examples=["리허설 → 토요일로 변경"])


class InviteCodeOut(BaseModel):
    """초대 코드 발급 응답."""

    invite_code: str = Field(..., description="모임 초대 코드", examples=["aB3xK9"])
    invite_url: str = Field(..., description="초대 링크 URL")


class InvitePreviewOut(BaseModel):
    """초대 링크 미리보기 (비인증)."""

    meeting_id: int
    name: str
    description: str | None = None
    member_count: int


class MemoOut(BaseModel):
    """모임 메모 정보."""

    memo_id: int = Field(..., description="메모 고유 번호", examples=[1])
    meeting_id: int = Field(..., description="모임 번호", examples=[1])
    author_user_id: int = Field(..., description="작성자 사용자 번호", examples=[1])
    content: str = Field(..., description="메모 내용")
    created_at: str | None = Field(None, description="작성 시각")
