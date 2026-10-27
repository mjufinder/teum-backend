from supabase import Client


class TimetableSlotRepository:
    """`timetable_slots` 테이블 영속성 담당. (TimetableSlot 도메인 전용)"""

    TABLE = "timetable_slots"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, slot_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", slot_id).execute()
        return res.data[0] if res.data else None

    def find_by_user(self, user_id: int) -> list[dict]:
        """한 사용자의 모든 시간표 항목 (공강 계산 입력 자료)."""
        return (
            self.db.table(self.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
        )

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, slot_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE).update(data).eq("id", slot_id).execute().data[0]
        )

    def delete(self, slot_id: int) -> None:
        self.db.table(self.TABLE).delete().eq("id", slot_id).execute()
