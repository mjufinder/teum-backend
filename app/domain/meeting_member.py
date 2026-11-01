from __future__ import annotations

from app.repositories.meeting_member_repository import MeetingMemberRepository


class MeetingMember:
    """모임 구성원 도메인 객체 (클래스 다이어그램의 MEETING_MEMBER).

    사용자-모임 참여 관계와 역할(ADMIN/MEMBER)·상태(ACTIVE/LEFT)를 관리한다.
    DB 입출력은 `MeetingMemberRepository` 에 위임한다.
    """

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        member_id: int | None,
        meeting_id: int,
        user_id: int,
        role: str = "MEMBER",
        status: str = "ACTIVE",
        repo: MeetingMemberRepository,
    ):
        self.member_id = member_id      # Long
        self.meeting_id = meeting_id    # Long
        self.user_id = user_id          # Long
        self.role = role                # String (ADMIN / MEMBER)
        self.status = status            # String (ACTIVE / LEFT)
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: MeetingMemberRepository) -> MeetingMember:
        return cls(
            member_id=row["id"],
            meeting_id=row["meeting_id"],
            user_id=row["user_id"],
            role=row["role"],
            status=row["status"],
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def register(
        cls,
        *,
        meeting_id: int,
        user_id: int,
        role: str = "MEMBER",
        repo: MeetingMemberRepository,
    ) -> MeetingMember:
        """모임에 구성원으로 등록한다 (ACTIVE 상태).

        role="ADMIN" 이면 관리자(모임 생성자), 기본은 일반 구성원.
        """
        row = repo.insert(
            {
                "meeting_id": meeting_id,
                "user_id": user_id,
                "role": role,
                "status": "ACTIVE",
            }
        )
        return cls._from_row(row, repo)

    @classmethod
    def accept_invite(
        cls,
        *,
        meeting_id: int,
        user_id: int,
        repo: MeetingMemberRepository,
    ) -> MeetingMember:
        """초대 수락(모임 합류) → acceptInvite():void.

        일반 구성원(MEMBER)·활성(ACTIVE) 상태로 참여 정보를 생성한다.
        """
        row = repo.insert(
            {
                "meeting_id": meeting_id,
                "user_id": user_id,
                "role": "MEMBER",
                "status": "ACTIVE",
            }
        )
        return cls._from_row(row, repo)

    def is_admin(self) -> bool:
        """관리자 여부 → isAdmin():Boolean."""
        return self.role == "ADMIN"

    def transfer_admin(self, target: MeetingMember) -> None:
        """관리자 권한 위임 → transferAdmin():void.

        현재 구성원이 관리자일 때만 대상에게 ADMIN 을 넘긴다.
        """
        if not self.is_admin():
            raise PermissionError("관리자만 권한을 위임할 수 있습니다.")
        self.role = "MEMBER"
        target.role = "ADMIN"
        self._repo.update(self.member_id, {"role": "MEMBER"})
        self._repo.update(target.member_id, {"role": "ADMIN"})

    def leave(self) -> None:
        """모임 탈퇴 → leave():void. 상태를 LEFT 로 전환."""
        self.status = "LEFT"
        self._repo.update(self.member_id, {"status": "LEFT"})
