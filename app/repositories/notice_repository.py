from supabase import Client


class NoticeRepository:
    """공지사항 DB 접근. 백엔드 service_role 클라이언트를 사용한다."""

    def __init__(self, db: Client):
        self.db = db

    def insert(self, data: dict) -> dict:
        return self.db.table("notices").insert(data).execute().data[0]
