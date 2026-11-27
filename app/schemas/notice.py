from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NoticeCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)


class NoticeUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1, max_length=10000)

    @model_validator(mode="after")
    def validate_changes(self) -> "NoticeUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("제목 또는 본문을 입력하세요.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("수정할 값은 null일 수 없습니다.")
        return self


class NoticeOut(BaseModel):
    notice_id: int
    author_user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class NoticeListItem(BaseModel):
    notice_id: int
    author_user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class NoticeListOut(BaseModel):
    items: list[NoticeListItem]
    total: int = Field(..., description="삭제되지 않은 전체 공지 수")
    page: int
    page_size: int
