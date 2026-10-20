from fastapi import APIRouter

from app.api.routes import auth, health

# 모든 라우터를 여기에 등록합니다.
# 모듈 단위 개발: 새 기능 라우터를 만들고 아래에 include_router 로 추가하세요.
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
