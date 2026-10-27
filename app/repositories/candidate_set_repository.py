from supabase import Client


class CandidateSetRepository:
    """`candidate_sets` 테이블 영속성 담당. (CandidateSet 도메인 전용)"""

    TABLE = "candidate_sets"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, set_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", set_id).execute()
        return res.data[0] if res.data else None

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, set_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE).update(data).eq("id", set_id).execute().data[0]
        )
