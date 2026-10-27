from supabase import Client


class VoteSelectionRepository:
    """`vote_selections` 테이블 영속성 담당. (VoteSelection 도메인 전용)

    복합 기본키 (ballot_id, candidate_id) 를 사용하므로 단일 id 가 없다.
    """

    TABLE = "vote_selections"

    def __init__(self, db: Client):
        self.db = db

    def find_by_ballot(self, ballot_id: int) -> list[dict]:
        """한 투표지에서 선택한 후보들."""
        return (
            self.db.table(self.TABLE)
            .select("*")
            .eq("ballot_id", ballot_id)
            .execute()
            .data
        )

    def insert(self, data: dict) -> dict:
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def delete(self, ballot_id: int, candidate_id: int) -> None:
        """선택 취소: 복합키로 한 행 삭제."""
        (
            self.db.table(self.TABLE)
            .delete()
            .eq("ballot_id", ballot_id)
            .eq("candidate_id", candidate_id)
            .execute()
        )
