from supabase import Client


class MeetingRepository:
    """`meetings` 테이블 영속성 담당. (Meeting 도메인 전용)"""

    TABLE = "meetings"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, meeting_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", meeting_id).execute()
        return res.data[0] if res.data else None

    def find_by_share_token(self, share_token: str) -> dict | None:
        """공유 토큰으로 모임 조회 (삭제되지 않은 것). 없으면 None. (외부 공유용)"""
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("share_token", share_token)
            .is_("deleted_at", "null")
            .execute()
        )
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

    def find_by_ids(self, meeting_ids: list[int]) -> list[dict]:
        """여러 모임 ID로 조회 (삭제되지 않은 것만). (내 모임 목록용)"""
        if not meeting_ids:
            return []
        return (
            self.db.table(self.TABLE)
            .select("*")
            .in_("id", meeting_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
        )

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
