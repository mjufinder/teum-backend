from __future__ import annotations

from app.repositories.vote_selection_repository import VoteSelectionRepository


class VoteSelection:
    """투표 선택 항목 도메인 객체 (클래스 다이어그램의 VOTE_SELECTION).

    한 투표지에서 선택한 후보 하나. 복합키 (ballot_id, candidate_id) 를 쓰며,
    set_id 는 투표지와 후보가 같은 묶음인지 검증하는 용도다.
    DB 입출력은 `VoteSelectionRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        ballot_id: int,
        candidate_id: int,
        set_id: int,
        repo: VoteSelectionRepository,
    ):
        self.ballot_id = ballot_id          # Long
        self.candidate_id = candidate_id    # Long
        self.set_id = set_id                # Long (정합성 검증용)
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: VoteSelectionRepository) -> VoteSelection:
        return cls(
            ballot_id=row["ballot_id"],
            candidate_id=row["candidate_id"],
            set_id=row["set_id"],
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def select(
        cls,
        *,
        ballot_id: int,
        candidate_id: int,
        set_id: int,
        repo: VoteSelectionRepository,
    ) -> VoteSelection:
        """후보 선택 → select():void."""
        repo.insert(
            {"ballot_id": ballot_id, "candidate_id": candidate_id, "set_id": set_id}
        )
        return cls(
            ballot_id=ballot_id, candidate_id=candidate_id, set_id=set_id, repo=repo
        )

    def cancel(self) -> None:
        """선택 취소 → cancel():void."""
        self._repo.delete(self.ballot_id, self.candidate_id)
