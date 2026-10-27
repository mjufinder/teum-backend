from supabase import Client


class ConfirmedScheduleRepository:
    """`confirmed_schedules` 테이블 영속성 담당. (ConfirmedSchedule 도메인 전용)"""

    TABLE = "confirmed_schedules"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, confirmed_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", confirmed_id).execute()
        return res.data[0] if res.data else None

    def find_by_meeting(self, meeting_id: int) -> dict | None:
        """모임의 확정 일정 (모임당 최대 1개)."""
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("meeting_id", meeting_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]
