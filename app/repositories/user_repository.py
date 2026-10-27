from supabase import Client


class UserRepository:
    """`users` 테이블 영속성 담당.

    도메인 객체(`User`)는 비즈니스 규칙만 다루고, 실제 DB 입출력은
    이 클래스에 위임한다. (클래스 다이어그램의 User 속성을 DB 행과 매핑)
    """

    TABLE = "users"

    def __init__(self, db: Client):
        self.db = db

    def find_by_provider(self, provider: str, provider_user_id: str) -> dict | None:
        """소셜 계정 (provider, provider_user_id) 로 사용자 조회. 없으면 None."""
        res = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("provider", provider)
            .eq("provider_user_id", provider_user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return res.data[0] if res.data else None

    def find_by_id(self, user_id: int) -> dict | None:
        res = self.db.table(self.TABLE).select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None

    def insert(self, data: dict) -> dict:
        """신규 사용자 저장 후 생성된 행(자동 id 포함)을 반환."""
        return self.db.table(self.TABLE).insert(data).execute().data[0]

    def update(self, user_id: int, data: dict) -> dict:
        """user_id 행을 data 로 부분 수정 후 갱신된 행을 반환."""
        return (
            self.db.table(self.TABLE)
            .update(data)
            .eq("id", user_id)
            .execute()
            .data[0]
        )
