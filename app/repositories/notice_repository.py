from supabase import Client


class NoticeRepository:
    """공지사항 DB 접근. 백엔드 service_role 클라이언트를 사용한다."""

    def __init__(self, db: Client):
        self.db = db

    def insert(self, data: dict) -> dict:
        return self.db.table("notices").insert(data).execute().data[0]

    def find_by_id(self, notice_id: int) -> dict | None:
        """삭제되지 않은 공지를 조회한다."""
        result = (
            self.db.table("notices")
            .select("id,author_user_id,title,content,created_at,updated_at")
            .eq("id", notice_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    def update(self, notice_id: int, changes: dict) -> dict | None:
        """삭제 여부를 UPDATE 조건에 포함하여 삭제된 공지의 수정을 막는다."""
        result = (
            self.db.table("notices")
            .update(changes)
            .eq("id", notice_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    def find_page(self, *, page: int, page_size: int) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        result = (
            self.db.table("notices")
            .select("id,author_user_id,title,created_at,updated_at", count="exact")
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .order("id", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        return result.data, result.count
