from supabase import Client
from postgrest.exceptions import APIError


class NoticeCommentRepository:
    def __init__(self, db: Client):
        self.db = db

    def update(
        self, *, notice_id: int, comment_id: int, author_user_id: int, content: str,
    ) -> dict | None:
        try:
            result = self.db.rpc("update_notice_comment", {
                "p_notice_id": notice_id, "p_comment_id": comment_id,
                "p_author_user_id": author_user_id, "p_content": content,
            }).execute()
        except APIError as exc:
            if exc.code == "PT403":
                raise PermissionError("댓글 작성자만 수정할 수 있습니다.") from exc
            raise
        return result.data[0] if result.data else None

    def find_page(
        self, *, notice_id: int, page: int, page_size: int,
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        result = (
            self.db.table("notice_comments")
            .select("id,notice_id,author_user_id,content,created_at,updated_at", count="exact")
            .eq("notice_id", notice_id)
            .is_("deleted_at", "null")
            .order("created_at")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        return result.data, result.count

    def insert(self, *, notice_id: int, author_user_id: int, content: str) -> dict | None:
        """부모 공지를 잠그고 댓글을 작성한다. 없거나 삭제된 공지면 None."""
        result = self.db.rpc("create_notice_comment", {
            "p_notice_id": notice_id,
            "p_author_user_id": author_user_id,
            "p_content": content,
        }).execute()
        return result.data[0] if result.data else None
