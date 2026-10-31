from pathlib import Path

import re

import numpy as np
from PIL import Image
from google.cloud import vision


START_HOUR = 9
END_HOUR = 22
SLOT_MINUTES = 30


class WeekdayHeaderError(ValueError):
    """요일 헤더가 누락되거나 기대한 열 순서와 다를 때 발생."""


def _validate_weekday_headers(text_boxes, vertical, header_bottom):
    """수업 영역의 글자는 제외하고 각 열의 헤더가 월~금인지 확인한다."""
    for day, expected in enumerate("월화수목금"):
        left, right = vertical[day + 1:day + 3]
        words = [
            (x0, text) for text, x0, y0, x1, y1 in text_boxes
            if 0 <= y0 < y1 <= header_bottom
            and left < (x0 + x1) / 2 < right
        ]
        label = re.sub(r"\s+", "", "".join(text for _, text in sorted(words)))
        if label not in (expected, expected + "요일"):
            raise WeekdayHeaderError(
                "요일 헤더를 확인할 수 없습니다. 상단에 월·화·수·목·금이 "
                "순서대로 모두 보이는 시간표 이미지를 업로드해 주세요."
            )


def _get_text_boxes(image_path):
    """Google OCR이 인식한 단어와 좌표를 반환한다."""
    from app.core.config import settings
    from google.oauth2 import service_account
    from google.auth.exceptions import DefaultCredentialsError

    credentials = None
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
        except (OSError, ValueError) as exc:
            raise DefaultCredentialsError("Invalid OCR credential file") from exc
    client = vision.ImageAnnotatorClient(credentials=credentials)
    response = client.document_text_detection(
        image=vision.Image(content=Path(image_path).read_bytes()), timeout=60, retry=None
    )
    if response.error.message:
        raise RuntimeError(f"Google OCR 오류: {response.error.message}")
    boxes = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    vertices = word.bounding_box.vertices
                    boxes.append((
                        "".join(symbol.text for symbol in word.symbols),
                        min(v.x for v in vertices), min(v.y for v in vertices),
                        max(v.x for v in vertices), max(v.y for v in vertices),
                    ))
    return boxes


def _line_centers(mask):
    """두께가 있는 격자선을 하나의 좌표로 합친다."""
    positions = np.flatnonzero(mask)
    if positions.size == 0:
        return np.array([], dtype=int)
    groups = np.split(positions, np.flatnonzero(np.diff(positions) > 1) + 1)
    return np.array([int(np.round(group.mean())) for group in groups])


def _read_start_hour(text_boxes, vertical, hours):
    """시간축의 OCR 라벨을 격자에 대응시켜 첫 행의 실제 시각을 구한다."""
    labels = {}
    for text, x0, y0, x1, y1 in text_boxes:
        if not vertical[0] < (x0 + x1) / 2 < vertical[1]:
            continue
        row = int(np.searchsorted(hours, (y0 + y1) / 2, side="right") - 1)
        if 0 <= row < len(hours) - 1:
            labels.setdefault(row, []).append((x0, text))

    readings = []
    for row, words in labels.items():
        # OCR이 '10'과 '시'를 별도 단어로 읽어도 같은 시간칸에서 합친다.
        label = "".join(text for _, text in sorted(words))
        match = re.fullmatch(r"(\d{1,2})(?:시|:00)?", re.sub(r"\s+", "", label))
        if match and 0 <= int(match.group(1)) <= 23:
            readings.append((row, int(match.group(1))))

    if len(readings) < 2:
        raise ValueError("시간축에서 시간 라벨을 2개 이상 읽어야 합니다.")
    # 일부 숫자 오독(9→6 등)은 여러 시간 라벨의 일치도로 걸러낸다.
    scores = {
        start: sum(value in (start + row, (start + row - 1) % 12 + 1)
                   for row, value in readings)
        for start in range(25 - (len(hours) - 1))
    }
    best = max(scores.values(), default=0)
    candidates = [start for start, score in scores.items()
                  if score == best and score >= max(2, len(readings) * 0.7)]
    if len(candidates) != 1:
        raise ValueError("시간 라벨과 격자가 일치하지 않거나 오전/오후를 구분할 수 없습니다.")
    return candidates[0]


def _find_grid(pixels):
    """배경과 대비되는 무채색 선을 읽고 생략된 좌우 테두리를 복원한다."""
    brightness = pixels.mean(axis=2)
    neutral = np.ptp(pixels, axis=2) < 8
    background = np.bincount(brightness[neutral].astype(int), minlength=256).argmax()
    contrast = np.abs(brightness - background)
    gray_lines = (np.ptp(pixels, axis=2) < 40) & (contrast > 15) & (contrast < 90)
    vertical = _line_centers(gray_lines.mean(axis=0) > 0.8)
    width = pixels.shape[1]
    internal = vertical[(vertical > 3) & (vertical < width - 4)]
    if len(internal) != 5 or not np.allclose(
        np.diff(internal), np.median(np.diff(internal)), rtol=0.05, atol=2
    ):
        raise ValueError("시간축과 월~금의 세로 격자선을 찾을 수 없습니다.")
    day_width = np.median(np.diff(internal))
    if abs((width - 1 - internal[-1]) - day_width) > max(4, day_width * 0.05):
        raise ValueError("금요일 열이 잘렸거나 지원하지 않는 시간표입니다.")
    vertical = np.concatenate(([0], internal, [width - 1]))
    gutter = gray_lines[:, 2 : vertical[1] - 2]
    horizontal = _line_centers(gutter.mean(axis=1) > 0.8)
    horizontal = horizontal[horizontal > 3]  # 존재하는 경우에만 위쪽 테두리 제거
    if len(horizontal) < 3:
        raise ValueError("1시간 간격의 가로 격자선을 찾을 수 없습니다.")
    step = np.median(np.diff(horizontal))
    # 시간표 아래 메모 영역의 테두리는 시간축에 포함하지 않는다.
    end = 1
    while end < len(horizontal) and np.isclose(
        horizontal[end] - horizontal[end - 1], step, rtol=0.05, atol=2
    ):
        end += 1
    hours = horizontal[:end]
    if len(hours) < 3:
        raise ValueError("일정한 1시간 간격의 가로 격자선을 찾을 수 없습니다.")
    return vertical, hours


def get_exact_timetable_matrix(image_path, *, return_time_slots=False):
    """밝은/어두운 테마의 에브리타임 주간 시간표를 30분 단위로 읽는다.

    열은 월~금, 행은 항상 09:00~22:00의 30분 간격 26개 구간이다.
    이미지에 표시되지 않은 시간은 공강으로 간주한다.
    공강(회의 참여 가능)은 1, 수업은 0이다(경계의 압축 노이즈 제외).
    Google OCR의 시간 라벨로 실제 시작 시간을 읽고 수업 블록을 확인한다.
    return_time_slots=True이면 (행렬, 시간 구간 목록)을 반환한다.
    배경색으로
    시작과 끝을 읽는다. 과목명으로 수업 길이를 추정하지 않는다.
    """
    with Image.open(image_path) as img:
        is_jpeg = img.format == "JPEG"
        pixels = np.asarray(img.convert("RGB"), dtype=np.int16)

    vertical, hours = _find_grid(pixels)

    text_boxes = _get_text_boxes(image_path)
    _validate_weekday_headers(text_boxes, vertical, hours[0])
    start_hour = _read_start_hour(text_boxes, vertical, hours)
    matrix = np.ones(((END_HOUR - START_HOUR) * 60 // SLOT_MINUTES, 5), dtype=int)
    dark_theme = np.median(pixels[:, :vertical[1]]) < 128
    # 어두운 JPEG의 경계에는 낮은 채도의 색 번짐이 생긴다.
    colored = np.ptp(pixels, axis=2) >= (24 if dark_theme and is_jpeg else 8)

    # OCR 좌표가 들어 있는 배경색 블록 전체를 수업으로 인식한다.
    # 글자가 없는 연강 구간도 같은 블록에 속하므로 함께 표시한다.
    occupied = np.zeros((pixels.shape[0], 5), dtype=bool)
    for day in range(5):
        left, right = vertical[day + 1 : day + 3]
        margin = max(2, int((right - left) * 0.05))
        rows = np.flatnonzero(
            colored[hours[0] + 1 : hours[-1], left + margin : right - margin]
            .mean(axis=1) > 0.3
        ) + hours[0] + 1
        if not rows.size:
            continue
        runs = np.split(rows, np.flatnonzero(np.diff(rows) > 4) + 1)
        for run in runs:
            top, bottom = run[0], run[-1] + 1
            if bottom - top < 4:  # JPEG 경계의 색 번짐 제외
                continue
            if not any(
                left < (x0 + x1) / 2 < right and y0 < bottom and y1 > top
                for _, x0, y0, x1, y1 in text_boxes
            ):
                raise ValueError(
                    f"{'월화수목금'[day]}요일 수업 블록(y={top}~{bottom})에서 "
                    "OCR 텍스트를 찾지 못했습니다. 이미지와 OCR 결과를 확인하세요."
                )
            occupied[top:bottom, day] = True

    for hour_index, (top, bottom) in enumerate(zip(hours[:-1], hours[1:])):
        half_hours = np.linspace(top, bottom, 3).round().astype(int)
        for half in range(2):
            row = (start_hour - START_HOUR) * 2 + hour_index * 2 + half
            if not 0 <= row < len(matrix):
                continue
            y_start, y_end = half_hours[half : half + 2]
            for day in range(5):
                matrix[row, day] = int(
                    occupied[y_start + 1 : y_end, day].sum()
                    < max(3, (y_end - y_start) * 0.05)
                )

    if return_time_slots:
        def format_time(minutes):
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        time_slots = [
            (format_time(START_HOUR * 60 + row * SLOT_MINUTES),
             format_time(START_HOUR * 60 + (row + 1) * SLOT_MINUTES))
            for row in range(len(matrix))
        ]
        return matrix, time_slots
    return matrix


