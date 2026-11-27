from dataclasses import dataclass
from datetime import datetime, timezone

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
        return cls._from_row(row)

    @classmethod
    def update(
        cls, *, notice_id: int, changes: dict, repo: NoticeRepository,
    ) -> "Notice | None":
        row = repo.update(notice_id, changes)
        return cls._from_row(row) if row is not None else None

    @classmethod
    def delete(cls, *, notice_id: int, repo: NoticeRepository) -> bool:
        """행을 보존하고 삭제 시각만 기록한다. 이미 삭제된 행은 변경하지 않는다."""
        row = repo.update(notice_id, {"deleted_at": datetime.now(timezone.utc).isoformat()})
        return row is not None

    @classmethod
    def _from_row(cls, row: dict) -> "Notice":
        return cls(
            notice_id=row["id"], author_user_id=row["author_user_id"],
            title=row["title"], content=row["content"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
