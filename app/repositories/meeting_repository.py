from supabase import Client


class MeetingRepository:
    """`meetings` 테이블 영속성 담당. (Meeting 도메인 전용)"""

    TABLE = "meetings"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, meeting_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", meeting_id).execute()
        return res.data[0] if res.data else None

    def find_by_invite_code(self, invite_code: str) -> dict | None:
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("invite_code", invite_code)
            .is_("deleted_at", "null")
            .execute()
        )
        return res.data[0] if res.data else None

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, meeting_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE)
            .update(data)
            .eq("id", meeting_id)
            .execute()
            .data[0]
        )
