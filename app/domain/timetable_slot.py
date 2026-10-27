from __future__ import annotations

from datetime import time

from app.repositories.timetable_slot_repository import TimetableSlotRepository


class TimetableSlot:
    """시간표 일정 도메인 객체 (클래스 다이어그램의 TIMETABLE_SLOT).

    개별 수업/일정 한 건. 공강 계산 시 '불참 구간' 판단 자료가 된다.
    DB 입출력은 `TimetableSlotRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        slot_id: int | None,
        user_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
        title: str,
        repo: TimetableSlotRepository,
    ):
        self.slot_id = slot_id              # Long
        self.user_id = user_id              # Long
        self.day_of_week = day_of_week      # Integer (0=일 ~ 6=토)
        self.start_time = start_time        # LocalTime
        self.end_time = end_time            # LocalTime
        self.title = title                  # String (과목명/일정명)
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: TimetableSlotRepository) -> TimetableSlot:
        return cls(
            slot_id=row["id"],
            user_id=row["user_id"],
            day_of_week=row["day_of_week"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            title=row["title"],
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    def validate_time(self) -> bool:
        """시간 유효성 검증 → validateTime():Boolean.

        요일 범위(0~6)와 시작 < 종료 조건을 만족하면 True.
        """
        return 0 <= self.day_of_week <= 6 and self.start_time < self.end_time

    def overlaps(self, other: TimetableSlot) -> bool:
        """다른 일정과 시간 겹침 여부 → overlaps():Boolean."""
        if self.day_of_week != other.day_of_week:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time

    def update(
        self,
        *,
        day_of_week: int | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        title: str | None = None,
    ) -> None:
        """일정 수정 → update():void. 검증 통과 시에만 DB 반영."""
        if day_of_week is not None:
            self.day_of_week = day_of_week
        if start_time is not None:
            self.start_time = start_time
        if end_time is not None:
            self.end_time = end_time
        if title is not None:
            self.title = title

        if not self.validate_time():
            raise ValueError("잘못된 시간 구간입니다. (요일 범위 또는 시작<종료 위반)")

        self._repo.update(
            self.slot_id,
            {
                "day_of_week": self.day_of_week,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "title": self.title,
            },
        )
