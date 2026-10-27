from supabase import Client


class MeetingMemoRepository:
    """`meeting_memos` 테이블 영속성 담당. (MeetingMemo 도메인 전용)"""

    TABLE = "meeting_memos"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, memo_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", memo_id).execute()
        return res.data[0] if res.data else None

    def find_by_meeting(self, meeting_id: int) -> list[dict]:
        """삭제되지 않은 모임 메모 목록."""
        return (
            self.db.table(self.TABLE)
            .select("*")
            .eq("meeting_id", meeting_id)
            .is_("deleted_at", "null")
            .execute()
            .data
        )

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, memo_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE).update(data).eq("id", memo_id).execute().data[0]
        )
