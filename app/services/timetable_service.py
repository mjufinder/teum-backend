import logging
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException, UploadFile
from google.api_core.exceptions import DeadlineExceeded, GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from PIL import Image, UnidentifiedImageError
from postgrest.exceptions import APIError
from httpx import HTTPError

from app.domain.timetable import Timetable
from app.schemas.timetable import TimetableRecognitionOut
from app.schemas.timetable import TimetableSaveRequest, TimetableSaveOut
from app.repositories.timetable_repository import TimetableRepository
from app.services.timetable_parser import WeekdayHeaderError, get_exact_timetable_matrix

logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000


def save_timetable(
    user_id: int, payload: TimetableSaveRequest, repository: TimetableRepository,
) -> TimetableSaveOut:
    timetable = Timetable(class_bits=payload.class_bits, manual_bits=payload.manual_bits)
    try:
        row = repository.save(user_id, timetable)
    except APIError as exc:
        if exc.code == "PT401":
            raise HTTPException(401, "유효하지 않은 사용자입니다.") from None
        logger.exception("Timetable database save failed")
        raise HTTPException(503, "시간표 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None
    except HTTPError:
        logger.exception("Timetable database connection failed")
        raise HTTPException(503, "시간표 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None
    return TimetableSaveOut(**row)


def recognize_timetable(file: UploadFile) -> TimetableRecognitionOut:
    """동기 라우트의 worker thread에서 실행하며 임시 파일은 항상 정리한다."""
    try:
        with TemporaryDirectory(prefix="teum-timetable-") as directory:
            path = Path(directory) / "upload"
            size = 0
            with path.open("wb") as target:
                while chunk := file.file.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "이미지는 10MB 이하여야 합니다.")
                    target.write(chunk)
            if size == 0:
                raise HTTPException(400, "빈 이미지 파일입니다.")

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(path) as image:
                        if image.format not in {"PNG", "JPEG"}:
                            raise HTTPException(415, "PNG 또는 JPEG 이미지만 지원합니다.")
                        if image.width * image.height > MAX_IMAGE_PIXELS:
                            raise HTTPException(413, "이미지는 1200만 픽셀 이하여야 합니다.")
                        image.verify()
            except (Image.DecompressionBombError, Image.DecompressionBombWarning):
                raise HTTPException(413, "이미지 해상도가 너무 큽니다.") from None
            except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
                raise HTTPException(400, "올바른 이미지 파일이 아닙니다.") from None

            try:
                matrix = get_exact_timetable_matrix(path)
            except WeekdayHeaderError as exc:
                raise HTTPException(422, str(exc)) from None
            except DeadlineExceeded:
                raise HTTPException(504, "OCR 응답 시간이 초과되었습니다.") from None
            except GoogleAuthError:
                logger.exception("OCR authentication failed")
                raise HTTPException(503, "OCR 인증 설정을 확인해 주세요.") from None
            except (GoogleAPICallError, RuntimeError):
                logger.exception("OCR request failed")
                raise HTTPException(502, "OCR 서비스 호출에 실패했습니다.") from None
            except (ValueError, OSError):
                raise HTTPException(
                    422, "시간표를 인식할 수 없습니다. 월~금 격자와 시간축이 보이는 에브리타임 이미지를 사용해 주세요."
                ) from None

            try:
                timetable = Timetable.from_weekday_matrix(matrix.tolist())
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(500, "시간표 인식 결과 형식이 올바르지 않습니다.") from None
            return TimetableRecognitionOut(
                class_bits=timetable.class_bits,
                manual_bits=timetable.manual_bits,
                available_bits=timetable.available_bits,
                warnings=[
                    "토요일과 일요일은 모두 가능으로 설정했습니다. 주말 불가 시간을 확인해 주세요.",
                    "이미지에 표시되지 않은 시간은 가능으로 설정했습니다. 저장 전에 전체 시간표를 확인해 주세요.",
                ],
            )
    finally:
        file.file.close()
