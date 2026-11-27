from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeCommentCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content: str = Field(..., min_length=1, max_length=1000)


class NoticeCommentUpdateRequest(NoticeCommentCreateRequest):
    """수정할 본문은 필수이며 작성자·공지 ID 변경은 허용하지 않는다."""


class NoticeCommentOut(BaseModel):
    comment_id: int
    notice_id: int
    author_user_id: int
    content: str
    created_at: datetime
    updated_at: datetime


class NoticeCommentListOut(BaseModel):
    items: list[NoticeCommentOut]
    total: int = Field(..., description="해당 공지의 삭제되지 않은 전체 댓글 수")
    page: int
    page_size: int
