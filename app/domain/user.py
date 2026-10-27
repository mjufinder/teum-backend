from __future__ import annotations

from datetime import datetime

from app.repositories.user_repository import UserRepository


class User:
    """사용자 도메인 객체 (클래스 다이어그램의 USER).

    소셜 계정·프로필·시간표 등록 상태를 관리한다. 속성은 클래스
    다이어그램과 1:1로 대응하며, DB 입출력은 `UserRepository` 에 위임한다.

    > 메서드 이름은 다이어그램의 camelCase(`socialLogin`)를 파이썬 관례인
    > snake_case(`social_login`)로 옮긴 것이다. (1:1 대응)
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        user_id: int | None,
        provider: str,
        provider_user_id: str,
        name: str,
        major: str | None = None,
        profile_completed: bool = False,
        timetable_registered_at: datetime | None = None,
        timetable_version: int = 0,
        deleted_at: datetime | None = None,
        repo: UserRepository,
    ):
        self.user_id = user_id                               # Long
        self.provider = provider                             # String (google/kakao/naver)
        self.provider_user_id = provider_user_id             # String
        self.name = name                                     # String
        self.major = major                                   # String (온보딩 전이면 None)
        self.profile_completed = profile_completed           # Boolean
        self.timetable_registered_at = timetable_registered_at  # LocalDateTime
        self.timetable_version = timetable_version           # Integer
        self.deleted_at = deleted_at                         # LocalDateTime
        self._repo = repo                                    # 영속성 위임 대상

    # ── 매핑 헬퍼: DB 행(dict) ↔ 도메인 객체 ───────────────────────
    @classmethod
    def _from_row(cls, row: dict, repo: UserRepository) -> User:
        return cls(
            user_id=row["id"],
            provider=row["provider"],
            provider_user_id=row["provider_user_id"],
            name=row["name"],
            major=row.get("major"),
            profile_completed=row["profile_completed"],
            timetable_registered_at=row.get("timetable_registered_at"),
            timetable_version=row["timetable_version"],
            deleted_at=row.get("deleted_at"),
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def social_login(
        cls,
        *,
        provider: str,
        provider_user_id: str,
        name: str,
        repo: UserRepository,
    ) -> User:
        """소셜 로그인/회원가입 (AUTH-01) → socialLogin():USER.

        기존 계정이면 조회해서 반환하고, 없으면 신규 생성한다.
        """
        row = repo.find_by_provider(provider, provider_user_id)
        if row is not None:
            return cls._from_row(row, repo)

        row = repo.insert(
            {
                "provider": provider,
                "provider_user_id": provider_user_id,
                "name": name,
                "profile_completed": False,
            }
        )
        return cls._from_row(row, repo)

    def is_new(self) -> bool:
        """온보딩(프로필+시간표 등록) 미완료 여부."""
        return not self.profile_completed

    def update_profile(self, *, name: str | None = None, major: str | None = None) -> None:
        """프로필 수정 → updateProfile():void.

        이름/전공이 모두 채워지면 프로필 완료 상태로 전환한다.
        """
        if name is not None:
            self.name = name
        if major is not None:
            self.major = major
        self.profile_completed = bool(self.name and self.major)

        self._repo.update(
            self.user_id,
            {
                "name": self.name,
                "major": self.major,
                "profile_completed": self.profile_completed,
            },
        )

    def import_timetable(self, image_bytes: bytes) -> None:
        """시간표 이미지 OCR/AI 분석 → importTimetable():void.

        분석 결과(수업 목록)는 호출부에서 TimetableSlot 으로 저장한다.
        """
        # TODO: OCR/AI 분석 파이프라인 연동 (현재 미구현)
        raise NotImplementedError("시간표 이미지 분석은 아직 구현되지 않았습니다.")

    def save_timetable(self) -> None:
        """시간표 최초 등록 완료 표시 → saveTimetable():void."""
        self.timetable_registered_at = datetime.now()
        self.timetable_version = 1
        self._repo.update(
            self.user_id,
            {
                "timetable_registered_at": self.timetable_registered_at.isoformat(),
                "timetable_version": self.timetable_version,
            },
        )

    def update_timetable(self) -> None:
        """시간표 수정 → updateTimetable():void.

        버전을 +1 하고, 참여 중인 모임들이 재계산 필요함을 인지하도록
        버전을 갱신한다. (모임별 needs_recalc 처리는 Meeting 쪽에서 수행)
        """
        self.timetable_version += 1
        self.timetable_registered_at = datetime.now()
        self._repo.update(
            self.user_id,
            {
                "timetable_version": self.timetable_version,
                "timetable_registered_at": self.timetable_registered_at.isoformat(),
            },
        )

    def logout(self) -> None:
        """로그아웃 → logout():void.

        세션/토큰 무효화는 인증 계층(JWT 블랙리스트 등)에서 처리하며,
        도메인 상태 변경은 없다.
        """
        return None
