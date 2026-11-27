from supabase import Client


class NoticeCommentRepository:
    def __init__(self, db: Client):
        self.db = db

    def insert(self, *, notice_id: int, author_user_id: int, content: str) -> dict | None:
        """부모 공지를 잠그고 댓글을 작성한다. 없거나 삭제된 공지면 None."""
        result = self.db.rpc("create_notice_comment", {
            "p_notice_id": notice_id,
            "p_author_user_id": author_user_id,
            "p_content": content,
        }).execute()
        return result.data[0] if result.data else None
