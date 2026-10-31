from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 환경설정. .env 파일 또는 환경변수에서 로드됩니다."""

    # 기본 정보
    PROJECT_NAME: str = "mjufinder-be"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # CORS: 프론트엔드 주소 (쉼표로 구분)
    CORS_ORIGINS: str = "http://localhost:3000"

    # Supabase (인증 JWT 검증도 Supabase 가 담당 — 별도 앱 JWT 시크릿 불필요)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # service_role 또는 anon 키

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
