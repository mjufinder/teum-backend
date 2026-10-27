from __future__ import annotations

from app.repositories.candidate_repository import CandidateRepository
from app.repositories.candidate_set_repository import CandidateSetRepository


class CandidateSet:
    """후보 묶음 도메인 객체 (클래스 다이어그램의 CANDIDATE_SET).

    투표 라운드 단위. 추천(RECOMMEND)/차선(ALTERNATIVE) 후보 묶음이며
    투표 진행·집계를 담당한다. DB 입출력은 `CandidateSetRepository` 에 위임.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        set_id: int | None,
        run_id: int,
        set_type: str,
        reason: str | None,
        result_status: str,
        vote_status: str = "OPEN",
        repo: CandidateSetRepository,
        candidate_repo: CandidateRepository,
    ):
        self.set_id = set_id                # Long
        self.run_id = run_id                # Long
        self.set_type = set_type            # String (RECOMMEND / ALTERNATIVE)
        self.reason = reason                # String (차선책 진입 사유)
        self.result_status = result_status  # String (HAS_CANDIDATE / NO_CANDIDATE)
        self.vote_status = vote_status      # String (OPEN / CLOSED / DISCARDED)
        self._repo = repo
        self._candidate_repo = candidate_repo

    @classmethod
    def _from_row(
        cls,
        row: dict,
        repo: CandidateSetRepository,
        candidate_repo: CandidateRepository,
    ) -> CandidateSet:
        return cls(
            set_id=row["id"],
            run_id=row["run_id"],
            set_type=row["set_type"],
            reason=row.get("reason"),
            result_status=row["result_status"],
            vote_status=row["vote_status"],
            repo=repo,
            candidate_repo=candidate_repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    def open_vote(self) -> None:
        """투표 시작 → openVote():void."""
        self.vote_status = "OPEN"
        self._repo.update(self.set_id, {"vote_status": "OPEN"})

    def count_votes(self) -> list[int]:
        """후보별 득표수 집계 → countVotes():Integer[].

        묶음 내 각 후보의 득표수를 순위(rank_no) 순으로 반환한다.
        """
        candidates = self._candidate_repo.find_by_set(self.set_id)
        return [self._candidate_repo.count_votes(c["id"]) for c in candidates]

    def close_vote(self) -> None:
        """투표 마감 → closeVote():void."""
        self.vote_status = "CLOSED"
        self._repo.update(self.set_id, {"vote_status": "CLOSED"})

    def get_winner(self) -> dict | None:
        """최다 득표 후보 → getWinner():CANDIDATE.

        득표수가 가장 많은 후보 행을 반환(동점이면 rank_no 가 앞선 후보).
        """
        candidates = self._candidate_repo.find_by_set(self.set_id)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda c: (self._candidate_repo.count_votes(c["id"]), -c["rank_no"]),
        )
