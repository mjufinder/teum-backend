from supabase import Client

from app.domain.timetable import Timetable


class TimetableRepository:
    def __init__(self, db: Client):
        self.db = db

    def save(self, user_id: int, timetable: Timetable) -> dict:
        """시간표와 사용자 등록 정보를 동일 트랜잭션에서 저장한다."""
        result = self.db.rpc("save_timetable", {
            "p_user_id": user_id,
            "p_class_bits": timetable.class_bits,
            "p_manual_bits": timetable.manual_bits,
        }).execute()
        return result.data[0]
