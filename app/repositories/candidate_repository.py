from supabase import Client


class CandidateRepository:
    """`candidates` 테이블 영속성 담당. (Candidate 도메인 전용)"""

    TABLE = "candidates"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, candidate_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", candidate_id).execute()
        return res.data[0] if res.data else None

    def find_by_set(self, set_id: int) -> list[dict]:
        """후보 묶음에 속한 후보들 (추천 순위 오름차순)."""
        return (
            self.db.table(self.TABLE)
            .select("*")
            .eq("set_id", set_id)
            .order("rank_no")
            .execute()
            .data
        )

    def count_votes(self, candidate_id: int) -> int:
        """이 후보를 선택한 투표 수."""
        res = (
            self.db.table("vote_selections")
            .select("ballot_id", count="exact")
            .eq("candidate_id", candidate_id)
            .execute()
        )
        return res.count or 0

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, candidate_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE)
            .update(data)
            .eq("id", candidate_id)
            .execute()
            .data[0]
        )

    def delete(self, candidate_id: int) -> None:
        self.db.table(self.TABLE).delete().eq("id", candidate_id).execute()
