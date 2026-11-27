from dataclasses import dataclass
from datetime import datetime

from app.repositories.notice_comment_repository import NoticeCommentRepository


@dataclass
class NoticeComment:
    comment_id: int
    notice_id: int
    author_user_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def write(
        cls, *, notice_id: int, author_user_id: int, content: str,
        repo: NoticeCommentRepository,
    ) -> "NoticeComment | None":
        row = repo.insert(notice_id=notice_id, author_user_id=author_user_id, content=content)
        if row is None:
            return None
        return cls(
            comment_id=row["id"], notice_id=row["notice_id"],
            author_user_id=row["author_user_id"], content=row["content"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
