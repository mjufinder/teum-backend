from __future__ import annotations

from datetime import datetime

from app.repositories.meeting_memo_repository import MeetingMemoRepository


class MeetingMemo:
    """모임 메모 도메인 객체 (클래스 다이어그램의 MEETING_MEMO).

    모임 안내·의견 기록. DB 입출력은 `MeetingMemoRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        memo_id: int | None,
        meeting_id: int,
        author_user_id: int,
        content: str,
        deleted_at: datetime | None = None,
        repo: MeetingMemoRepository,
    ):
        self.memo_id = memo_id              # Long
        self.meeting_id = meeting_id        # Long
        self.author_user_id = author_user_id  # Long
        self.content = content              # String
        self.deleted_at = deleted_at        # LocalDateTime
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: MeetingMemoRepository) -> MeetingMemo:
        return cls(
            memo_id=row["id"],
            meeting_id=row["meeting_id"],
            author_user_id=row["author_user_id"],
            content=row["content"],
            deleted_at=row.get("deleted_at"),
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def write(
        cls,
        *,
        meeting_id: int,
        author_user_id: int,
        content: str,
        repo: MeetingMemoRepository,
    ) -> MeetingMemo:
        """메모 작성 → write():void."""
        row = repo.insert(
            {
                "meeting_id": meeting_id,
                "author_user_id": author_user_id,
                "content": content,
            }
        )
        return cls._from_row(row, repo)

    def update(self, *, content: str) -> None:
        """메모 수정 → update():void."""
        self.content = content
        self._repo.update(self.memo_id, {"content": content})

    def delete(self) -> None:
        """메모 삭제(Soft Delete) → delete():void."""
        self.deleted_at = datetime.now()
        self._repo.update(self.memo_id, {"deleted_at": self.deleted_at.isoformat()})
