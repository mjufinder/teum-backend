from supabase import Client


class MeetingMemberRepository:
    """`meeting_members` 테이블 영속성 담당. (MeetingMember 도메인 전용)"""

    TABLE = "meeting_members"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, member_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", member_id).execute()
        return res.data[0] if res.data else None

    def find_active_by_meeting(self, meeting_id: int) -> list[dict]:
        """모임의 활성(ACTIVE) 구성원 목록."""
        return (
            self.db.table(self.TABLE)
            .select("*")
            .eq("meeting_id", meeting_id)
            .eq("status", "ACTIVE")
            .execute()
            .data
        )

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, member_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE)
            .update(data)
            .eq("id", member_id)
            .execute()
            .data[0]
        )
