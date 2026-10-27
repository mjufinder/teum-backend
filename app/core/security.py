"""JWT 액세스 토큰 발급·검증 유틸.

소셜 로그인 성공 후 자체 JWT 를 발급하고, 보호된 엔드포인트에서 이 토큰을
검증해 사용자를 식별한다. (Spring Security 의 토큰 발급/필터에 해당)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_access_token(user_id: int) -> str:
    """사용자 ID 를 subject 로 하는 액세스 토큰 발급.

    payload: sub(사용자 ID), exp(만료), iat(발급 시각).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """토큰을 검증하고 사용자 ID 를 반환.

    서명 불일치/만료/형식 오류 시 `jwt.InvalidTokenError` 계열 예외가 발생한다.
    (호출부에서 401 로 변환)
    """
    payload = jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    return int(payload["sub"])
