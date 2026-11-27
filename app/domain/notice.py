from dataclasses import dataclass
from datetime import datetime

from app.repositories.notice_repository import NoticeRepository


@dataclass
class Notice:
    notice_id: int
    author_user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def write(
        cls, *, author_user_id: int, title: str, content: str, repo: NoticeRepository
    ) -> "Notice":
        row = repo.insert({
            "author_user_id": author_user_id,
            "title": title,
            "content": content,
        })
        return cls(
            notice_id=row["id"], author_user_id=row["author_user_id"],
            title=row["title"], content=row["content"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
