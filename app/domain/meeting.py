from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta, timezone

from app.repositories.meeting_repository import MeetingRepository


class Meeting:
    """모임 도메인 객체 (클래스 다이어그램의 MEETING).

    모임 기본 정보 + 공강 탐색 조건 + 초대/공유 정보를 관리한다.
    DB 입출력은 `MeetingRepository` 에 위임한다.
    """

    INVITE_TTL = timedelta(days=7)  # 초대 코드 유효 기간

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        meeting_id: int | None,
        name: str,
        description: str | None,
        period_start: date,
        period_end: date,
        search_start_time: time,
        search_end_time: time,
        travel_buffer_min: int,
        min_duration_min: int,
        needs_recalc: bool,
        invite_code: str | None,
        invite_expires_at: datetime | None,
        share_token: str | None,
        deleted_at: datetime | None,
        repo: MeetingRepository,
    ):
        self.meeting_id = meeting_id                  # Long
        self.name = name                              # String
        self.description = description                # String
        self.period_start = period_start              # LocalDate
        self.period_end = period_end                  # LocalDate
        self.search_start_time = search_start_time    # LocalTime
        self.search_end_time = search_end_time        # LocalTime
        self.travel_buffer_min = travel_buffer_min    # Integer (이동 여유, 분)
        self.min_duration_min = min_duration_min      # Integer (최소 회의, 분)
        self.needs_recalc = needs_recalc              # Boolean (재계산 필요 상태)
        self.invite_code = invite_code                # String
        self.invite_expires_at = invite_expires_at    # LocalDateTime
        self.share_token = share_token                # String
        self.deleted_at = deleted_at                  # LocalDateTime
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: MeetingRepository) -> Meeting:
        return cls(
            meeting_id=row["id"],
            name=row["name"],
            description=row.get("description"),
            period_start=row["period_start"],
            period_end=row["period_end"],
            search_start_time=row["search_start_time"],
            search_end_time=row["search_end_time"],
            travel_buffer_min=row["travel_buffer_min"],
            min_duration_min=row["min_duration_min"],
            needs_recalc=row["needs_recalc"],
            invite_code=row.get("invite_code"),
            invite_expires_at=row.get("invite_expires_at"),
            share_token=row.get("share_token"),
            deleted_at=row.get("deleted_at"),
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def create(
        cls,
        *,
        name: str,
        period_start: date,
        period_end: date,
        search_start_time: time,
        search_end_time: time,
        min_duration_min: int,
        description: str | None = None,
        travel_buffer_min: int = 0,
        repo: MeetingRepository,
    ) -> Meeting:
        """모임 생성 → create():MEETING."""
        row = repo.insert(
            {
                "name": name,
                "description": description,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "search_start_time": search_start_time.isoformat(),
                "search_end_time": search_end_time.isoformat(),
                "travel_buffer_min": travel_buffer_min,
                "min_duration_min": min_duration_min,
                "needs_recalc": False,
            }
        )
        return cls._from_row(row, repo)

    def update_info(self, *, name: str | None = None, description: str | None = None) -> None:
        """모임 이름/설명 수정 → updateInfo():void.

        식별 정보 변경이라 재계산(needs_recalc)과는 무관하다.
        """
        changes: dict = {}
        if name is not None:
            self.name = name
            changes["name"] = name
        if description is not None:
            self.description = description
            changes["description"] = description
        if changes:
            self._repo.update(self.meeting_id, changes)

    def update_conditions(
        self,
        *,
        search_start_time: time | None = None,
        search_end_time: time | None = None,
        travel_buffer_min: int | None = None,
        min_duration_min: int | None = None,
    ) -> None:
        """공강 탐색 조건 수정 → updateConditions():void.

        전달된 필드만 변경하고, 조건이 바뀌었으므로 needs_recalc 를 켠다.
        (DB 에서 복원된 객체의 시각 필드는 문자열일 수 있어, 전달값만 직렬화한다)
        """
        changes: dict = {}
        if search_start_time is not None:
            self.search_start_time = search_start_time
            changes["search_start_time"] = search_start_time.isoformat()
        if search_end_time is not None:
            self.search_end_time = search_end_time
            changes["search_end_time"] = search_end_time.isoformat()
        if travel_buffer_min is not None:
            self.travel_buffer_min = travel_buffer_min
            changes["travel_buffer_min"] = travel_buffer_min
        if min_duration_min is not None:
            self.min_duration_min = min_duration_min
            changes["min_duration_min"] = min_duration_min

        self.needs_recalc = True
        changes["needs_recalc"] = True
        self._repo.update(self.meeting_id, changes)

    def create_invite(self) -> str:
        """초대 코드 발급 → createInvite():String. 7일 유효.

        이미 코드가 있으면 새 코드로 바꿔 이전 링크를 무효화한다.
        timestamptz 컬럼에 저장하므로 UTC 기준 시각을 쓴다.
        """
        self.invite_code = secrets.token_urlsafe(8)
        self.invite_expires_at = datetime.now(timezone.utc) + self.INVITE_TTL
        self._repo.update(
            self.meeting_id,
            {
                "invite_code": self.invite_code,
                "invite_expires_at": self.invite_expires_at.isoformat(),
            },
        )
        return self.invite_code

    def revoke_invite(self) -> None:
        """초대 링크 끊기. 코드와 만료 시각을 지워 기존 링크로 참가할 수 없게 한다."""
        self.invite_code = None
        self.invite_expires_at = None
        self._repo.update(
            self.meeting_id, {"invite_code": None, "invite_expires_at": None}
        )

    def invite_expiry(self) -> datetime | None:
        """초대 만료 시각을 UTC datetime 으로 돌려준다. 코드가 없으면 None."""
        if self.invite_code is None or self.invite_expires_at is None:
            return None
        expires = self.invite_expires_at
        if not isinstance(expires, datetime):
            # Supabase 는 timestamptz 를 ISO 문자열로 돌려준다.
            expires = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires

    def is_invite_valid(self, now: datetime | None = None) -> bool:
        """초대 코드가 있고 아직 만료되지 않았는지 확인한다."""
        expires = self.invite_expiry()
        if expires is None:
            return False
        return (now or datetime.now(timezone.utc)) < expires

    def on_member_joined(self):
        """팀원 합류 시 공강 재계산 트리거 → onMemberJoined():MATCHING_RUN.

        참여자가 늘면 공통 공강이 달라지므로 새 MatchingRun 을 실행한다.
        """
        self.needs_recalc = True
        self._repo.update(self.meeting_id, {"needs_recalc": True})
        # TODO: MatchingRun.calculate(trigger_type="JOIN") 호출로 연결
        raise NotImplementedError("매칭 계산 연동은 MatchingRun 구현 후 연결 예정입니다.")

    def recalculate(self):
        """관리자 수동 재계산 → recalculate():MATCHING_RUN."""
        self.needs_recalc = False
        self._repo.update(self.meeting_id, {"needs_recalc": False})
        # TODO: MatchingRun.calculate(trigger_type="ADMIN_RECALC") 호출로 연결
        raise NotImplementedError("매칭 계산 연동은 MatchingRun 구현 후 연결 예정입니다.")

    def confirm(self):
        """최종 일정 확정 → confirm():CONFIRMED_SCHEDULE.

        확정 직전 재검사(PRE_CONFIRM_RECHECK) 후 ConfirmedSchedule 을 생성한다.
        """
        # TODO: 재검사 통과 시 ConfirmedSchedule.confirm() 으로 연결
        raise NotImplementedError("일정 확정 연동은 ConfirmedSchedule 구현 후 연결 예정입니다.")

    def delete(self) -> None:
        """모임 삭제(Soft Delete) → delete():void."""
        self.deleted_at = datetime.now()
        self._repo.update(self.meeting_id, {"deleted_at": self.deleted_at.isoformat()})
