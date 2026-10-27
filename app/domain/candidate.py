from __future__ import annotations

from datetime import datetime

from app.repositories.candidate_repository import CandidateRepository


class Candidate:
    """개별 시간대 후보 도메인 객체 (클래스 다이어그램의 CANDIDATE).

    후보 묶음에 속한 하나의 추천 시간대. DB 입출력은 `CandidateRepository` 에 위임.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        candidate_id: int | None,
        set_id: int,
        rank_no: int,
        start_at: datetime,
        end_at: datetime,
        available_count: int,
        repo: CandidateRepository,
    ):
        self.candidate_id = candidate_id        # Long
        self.set_id = set_id                    # Long
        self.rank_no = rank_no                  # Integer (묶음 내 추천 순위)
        self.start_at = start_at                # LocalDateTime
        self.end_at = end_at                    # LocalDateTime
        self.available_count = available_count  # Integer (참석 가능 인원)
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: CandidateRepository) -> Candidate:
        return cls(
            candidate_id=row["id"],
            set_id=row["set_id"],
            rank_no=row["rank_no"],
            start_at=row["start_at"],
            end_at=row["end_at"],
            available_count=row["available_count"],
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    def is_available(self, total_member_count: int) -> bool:
        """전원 참석 가능 여부 → isAvailable():Boolean.

        참석 가능 인원이 전체 인원과 같으면 '공통 공강'으로 성립.
        """
        return self.available_count >= total_member_count

    def get_vote_count(self) -> int:
        """이 후보의 득표수 → getVoteCount():Integer."""
        return self._repo.count_votes(self.candidate_id)
