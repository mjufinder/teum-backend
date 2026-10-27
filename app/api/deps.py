"""FastAPI 의존성 프로바이더.

라우터(컨트롤러)가 repository 를 직접 생성하지 않고 `Depends` 로 주입받도록
한다. Spring 의 `@Autowired` 에 해당하는 역할. DB 클라이언트(`get_supabase`)를
받아 각 Repository 인스턴스를 만들어 넘긴다.
"""

from fastapi import Depends
from supabase import Client

from app.core.supabase import get_supabase
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.user_repository import UserRepository


def get_user_repository(db: Client = Depends(get_supabase)) -> UserRepository:
    return UserRepository(db)


def get_meeting_repository(db: Client = Depends(get_supabase)) -> MeetingRepository:
    return MeetingRepository(db)
