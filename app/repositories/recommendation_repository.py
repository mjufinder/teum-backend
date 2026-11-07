from supabase import Client


class RecommendationRepository:
    """후보 묶음/후보를 원자적으로 저장하고 한 스냅샷으로 조회한다."""

    def __init__(self, db: Client):
        self.db = db

    def save(self, run_id: int, candidates: list[dict]) -> dict:
        return self.db.rpc("save_recommended_candidates", {
            "p_run_id": run_id, "p_candidates": candidates,
        }).execute().data

    def find_latest(self, meeting_id: int) -> dict | None:
        return self.db.rpc("get_latest_recommended_candidates", {
            "p_meeting_id": meeting_id,
        }).execute().data

    def join_and_prepare(self, meeting_id: int, user_id: int) -> dict:
        return self.db.rpc("join_member_and_prepare_matching", {
            "p_meeting_id": meeting_id, "p_user_id": user_id,
        }).execute().data

    def complete_join(self, run_id: int, candidates: list[dict]) -> dict:
        return self.db.rpc("complete_join_matching", {
            "p_run_id": run_id, "p_candidates": candidates,
        }).execute().data
