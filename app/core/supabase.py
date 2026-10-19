from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """Supabase 클라이언트를 반환합니다.

    SUPABASE_URL / SUPABASE_KEY 가 설정되어 있어야 합니다.
    FastAPI 의존성으로 주입해서 사용하세요:

        @router.get("/items")
        def list_items(db: Client = Depends(get_supabase)):
            return db.table("items").select("*").execute().data
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_KEY 가 설정되지 않았습니다. .env 를 확인하세요."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
