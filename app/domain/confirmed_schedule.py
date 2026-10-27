from __future__ import annotations

from app.repositories.confirmed_schedule_repository import ConfirmedScheduleRepository
from app.repositories.candidate_repository import CandidateRepository


class ConfirmedSchedule:
    """확정 일정 도메인 객체 (클래스 다이어그램의 CONFIRMED_SCHEDULE).

    모임당 최대 1개의 최종 확정 일정. 확정한 후보(candidate)와 확정 직전
    재검사 이력(recheck_run)을 참조한다. DB 입출력은
    `ConfirmedScheduleRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        confirmed_id: int | None,
        meeting_id: int,
        candidate_id: int,
        recheck_run_id: int,
        confirmed_at=None,
        repo: ConfirmedScheduleRepository,
        candidate_repo: CandidateRepository,
    ):
        self.confirmed_id = confirmed_id        # Long
        self.meeting_id = meeting_id            # Long
        self.candidate_id = candidate_id        # Long
        self.recheck_run_id = recheck_run_id    # Long (확정 직전 재검사 이력)
        self.confirmed_at = confirmed_at        # LocalDateTime
        self._repo = repo
        self._candidate_repo = candidate_repo

    @classmethod
    def _from_row(
        cls,
        row: dict,
        repo: ConfirmedScheduleRepository,
        candidate_repo: CandidateRepository,
    ) -> ConfirmedSchedule:
        return cls(
            confirmed_id=row["id"],
            meeting_id=row["meeting_id"],
            candidate_id=row["candidate_id"],
            recheck_run_id=row["recheck_run_id"],
            confirmed_at=row.get("confirmed_at"),
            repo=repo,
            candidate_repo=candidate_repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def confirm(
        cls,
        *,
        meeting_id: int,
        candidate_id: int,
        recheck_run_id: int,
        repo: ConfirmedScheduleRepository,
        candidate_repo: CandidateRepository,
    ) -> ConfirmedSchedule:
        """일정 확정 → confirm():void.

        재검사(recheck_run) 통과 후 최종 후보를 모임의 확정 일정으로 저장한다.
        모임당 1개 제약은 DB uq_confirmed_meeting 로 보장된다.
        """
        row = repo.insert(
            {
                "meeting_id": meeting_id,
                "candidate_id": candidate_id,
                "recheck_run_id": recheck_run_id,
            }
        )
        return cls._from_row(row, repo, candidate_repo)

    def get_schedule(self) -> dict | None:
        """확정된 시간대 조회 → getSchedule():CANDIDATE."""
        return self._candidate_repo.find_by_id(self.candidate_id)

    def get_share_link(self, base_url: str, share_token: str) -> str:
        """공유 링크 생성 → getShareLink():String.

        모임의 share_token 으로 결과 공유 URL 을 조립한다.
        """
        return f"{base_url.rstrip('/')}/share/{share_token}"
