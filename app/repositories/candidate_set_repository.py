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

    def discard_open_by_runs(self, run_ids: list[int]) -> int:
        """주어진 계산 이력들의 진행 중(OPEN) 후보 묶음을 폐기(DISCARDED)한다.

        모임 조건 변경 시 기존 투표를 무효화하는 용도. 폐기된 묶음 수를 반환.
        """
        if not run_ids:
            return 0
        rows = (
            self.db.table(self.TABLE)
            .update({"vote_status": "DISCARDED"})
            .in_("run_id", run_ids)
            .eq("vote_status", "OPEN")
            .execute()
            .data
        )
        return len(rows)
