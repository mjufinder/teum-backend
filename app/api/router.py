from fastapi import APIRouter

from app.api.routes import (
    auth,
    candidates,
    confirm,
    health,
    meeting_memos,
    meetings,
    share,
    timetable,
    votes,
)

# 모든 라우터를 여기에 등록합니다.
# 모듈 단위 개발: 새 기능 라우터를 만들고 아래에 include_router 로 추가하세요.
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meetings.router)
api_router.include_router(meeting_memos.router)
api_router.include_router(votes.router)
api_router.include_router(confirm.router)
api_router.include_router(share.router)
api_router.include_router(timetable.router)
api_router.include_router(candidates.router)
