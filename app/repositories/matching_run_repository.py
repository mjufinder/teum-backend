from supabase import Client


class MatchingRunRepository:
    """`matching_runs` 테이블 영속성 담당. (MatchingRun 도메인 전용)"""

    TABLE = "matching_runs"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, run_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", run_id).execute()
        return res.data[0] if res.data else None

    def find_latest_by_meeting(self, meeting_id: int) -> dict | None:
        """모임의 가장 최근 계산 이력 1건."""
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("meeting_id", meeting_id)
            .order("calculated_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_ids_by_meeting(self, meeting_id: int) -> list[int]:
        """모임의 모든 계산 이력 ID 목록. (후보 묶음 폐기 등 연계용)"""
        rows = (
            self.db.table(self.TABLE)
            .select("id")
            .eq("meeting_id", meeting_id)
            .execute()
            .data
        )
        return [r["id"] for r in rows]

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]
