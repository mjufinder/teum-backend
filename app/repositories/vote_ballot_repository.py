from supabase import Client


class VoteBallotRepository:
    """`vote_ballots` 테이블 영속성 담당. (VoteBallot 도메인 전용)"""

    TABLE = "vote_ballots"

    def __init__(self, db: Client):
        self.db = db

    def find_by_id(self, ballot_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", ballot_id).execute()
        return res.data[0] if res.data else None

    def find_by_set_and_member(self, set_id: int, member_id: int) -> dict | None:
        """한 묶음에서 구성원의 기존 투표지 (구성원당 1표)."""
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("set_id", set_id)
            .eq("member_id", member_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, ballot_id: int, data: dict) -> dict:
        return (
            self.db.table(self.TABLE)
            .update(data)
            .eq("id", ballot_id)
            .execute()
            .data[0]
        )
