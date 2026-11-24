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

    def find_by_user(self, user_id: int) -> dict | None:
        """단일 조회로 시간표와 같은 시점의 사용자 등록 정보를 가져온다."""
        result = (
            self.db.table("timetables")
            .select("class_bits,manual_bits,available_bits,updated_at,"
                    "users!inner(timetable_version,timetable_registered_at)")
            .eq("user_id", user_id)
            .is_("users.deleted_at", "null")
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = dict(result.data[0])
        user = row.pop("users")
        return {**row, **user}

    def find_by_users(self, user_ids: list[int]) -> list[dict]:
        """여러 사용자의 시간표 비트맵을 일괄 조회한다."""
        if not user_ids:
            return []
        return (
            self.db.table("timetables")
            .select("user_id,class_bits,manual_bits")
            .in_("user_id", user_ids)
            .execute()
            .data
        )
