from __future__ import annotations

from app.repositories.vote_ballot_repository import VoteBallotRepository
from app.repositories.vote_selection_repository import VoteSelectionRepository


class VoteBallot:
    """투표지 도메인 객체 (클래스 다이어그램의 VOTE_BALLOT).

    구성원 1명이 후보 묶음 1개에 제출한 투표 1건. 선택 항목(VoteSelection)은
    복합 관계로 소유한다. DB 입출력은 `VoteBallotRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        ballot_id: int | None,
        set_id: int,
        member_id: int,
        no_available: bool = False,
        repo: VoteBallotRepository,
        selection_repo: VoteSelectionRepository,
    ):
        self.ballot_id = ballot_id          # Long
        self.set_id = set_id                # Long
        self.member_id = member_id          # Long
        self.no_available = no_available    # Boolean ('참석 가능 후보 없음')
        self._repo = repo
        self._selection_repo = selection_repo

    @classmethod
    def _from_row(
        cls,
        row: dict,
        repo: VoteBallotRepository,
        selection_repo: VoteSelectionRepository,
    ) -> VoteBallot:
        return cls(
            ballot_id=row["id"],
            set_id=row["set_id"],
            member_id=row["member_id"],
            no_available=row["no_available"],
            repo=repo,
            selection_repo=selection_repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def submit(
        cls,
        *,
        set_id: int,
        member_id: int,
        candidate_ids: list[int],
        repo: VoteBallotRepository,
        selection_repo: VoteSelectionRepository,
    ) -> VoteBallot:
        """투표 제출 → submit():void.

        투표지를 만들고 선택한 후보들을 VoteSelection 으로 저장한다.
        """
        row = repo.insert(
            {"set_id": set_id, "member_id": member_id, "no_available": False}
        )
        ballot = cls._from_row(row, repo, selection_repo)
        for candidate_id in candidate_ids:
            selection_repo.insert(
                {
                    "ballot_id": ballot.ballot_id,
                    "candidate_id": candidate_id,
                    "set_id": set_id,
                }
            )
        return ballot

    def update(self, *, candidate_ids: list[int]) -> None:
        """투표 수정 → update():void. 기존 선택을 지우고 다시 저장."""
        for sel in self._selection_repo.find_by_ballot(self.ballot_id):
            self._selection_repo.delete(self.ballot_id, sel["candidate_id"])
        for candidate_id in candidate_ids:
            self._selection_repo.insert(
                {
                    "ballot_id": self.ballot_id,
                    "candidate_id": candidate_id,
                    "set_id": self.set_id,
                }
            )
        self.no_available = False
        self._repo.update(self.ballot_id, {"no_available": False})

    def mark_no_available(self) -> None:
        """'참석 가능 후보 없음' 표시 → markNoAvailable():void.

        선택 항목을 모두 비우고 no_available 플래그를 켠다.
        """
        for sel in self._selection_repo.find_by_ballot(self.ballot_id):
            self._selection_repo.delete(self.ballot_id, sel["candidate_id"])
        self.no_available = True
        self._repo.update(self.ballot_id, {"no_available": True})
