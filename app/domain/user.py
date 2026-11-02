from __future__ import annotations

from datetime import datetime

from app.repositories.user_repository import UserRepository


class User:
    """사용자 도메인 객체 (클래스 다이어그램의 USER).

    Supabase 인증 계정·프로필·시간표 등록 상태를 관리한다. 속성은 클래스
    다이어그램과 1:1로 대응하며, DB 입출력은 `UserRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        user_id: int | None,
        auth_uid: str,
        email: str | None,
        name: str,
        major: str | None = None,
        profile_completed: bool = False,
        timetable_registered_at: datetime | None = None,
        timetable_version: int = 0,
        deleted_at: datetime | None = None,
        repo: UserRepository,
    ):
        self.user_id = user_id                               # Long (내부 PK)
        self.auth_uid = auth_uid                             # UUID (Supabase auth.users.id)
        self.email = email                                   # String (인증 이메일)
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
            auth_uid=row["auth_uid"],
            email=row.get("email"),
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
    def from_auth_user(
        cls,
        *,
        auth_uid: str,
        email: str | None,
        name: str,
        repo: UserRepository,
    ) -> User:
        """Supabase 인증 유저 → 앱 사용자 프로비저닝 (AUTH-01) → fromAuthUser():USER.

        로그인/회원가입(이메일·구글)은 Supabase Auth 가 처리하고, 백엔드는
        인증된 유저의 `auth_uid` 로 우리 users 행을 find-or-create 한다.
        """
        row = repo.find_by_auth_uid(auth_uid)
        if row is not None:
            return cls._from_row(row, repo)

        row = repo.insert(
            {
                "auth_uid": auth_uid,
                "email": email,
                "name": name,
                "profile_completed": False,
            }
        )
        return cls._from_row(row, repo)

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

    def withdraw(self) -> None:
        """회원 탈퇴(Soft Delete) → withdraw():void (AUTH-03).

        deleted_at 을 기록해 논리 삭제한다. 개인정보/시간표 물리 삭제는
        배치 또는 DB cascade 로 후처리한다.
        """
        self.deleted_at = datetime.now()
        self._repo.update(self.user_id, {"deleted_at": self.deleted_at.isoformat()})
