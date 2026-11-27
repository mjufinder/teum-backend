from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeCommentCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content: str = Field(..., min_length=1, max_length=1000)


class NoticeCommentOut(BaseModel):
    comment_id: int
    notice_id: int
    author_user_id: int
    content: str
    created_at: datetime
    updated_at: datetime
