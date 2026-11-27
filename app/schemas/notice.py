from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)


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
