from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.domain.user import User
from app.schemas.timetable import TimetableRecognitionOut
from app.services.timetable_service import recognize_timetable

router = APIRouter(prefix="/timetable", tags=["timetable"])


@router.post(
    "/recognize",
    response_model=TimetableRecognitionOut,
    summary="시간표 이미지 인식",
    responses={
        400: {"description": "빈 파일 또는 손상된 이미지"},
        401: {"description": "로그인 필요 또는 유효하지 않은 토큰"},
        413: {"description": "파일 용량 또는 해상도 초과"},
        415: {"description": "지원하지 않는 이미지 형식"},
        422: {"description": "파일 누락 또는 시간표 인식 실패"},
        502: {"description": "OCR 서비스 오류"},
        503: {"description": "OCR 인증 설정 오류"},
        504: {"description": "OCR 시간 초과"},
    },
)
def recognize(
    file: UploadFile = File(description="월~금 에브리타임 시간표 PNG/JPEG (최대 10MB)"),
    current_user: User = Depends(get_current_user),
) -> TimetableRecognitionOut:
    """인증된 사용자에게 182비트 초안을 반환한다. 이미지와 시간표는 영구 저장하지 않는다.

    월~일 순서로 각 요일의 09:00~22:00을 30분 간격으로 연결한다.
    1은 가능, 0은 불가이며 주말과 추가 일정의 기본값은 모두 1이다.
    """
    return recognize_timetable(file)
