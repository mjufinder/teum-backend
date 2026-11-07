import logging

from fastapi import HTTPException
from httpx import HTTPError
from postgrest.exceptions import APIError

from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.candidate import CandidateInput, CandidateSetOut

logger = logging.getLogger(__name__)


def save_recommended_candidates(
    run_id: int, candidates: list[CandidateInput], repository: RecommendationRepository,
) -> CandidateSetOut:
    """백엔드 전용 저장 함수. 실행 컨텍스트 run_id는 추후 재계산 흐름에서 전달.

    빈 목록도 NO_CANDIDATE 묶음으로 저장한다. 기존 묶음을 덮어쓰지 않는다.
    DB 예외는 호출자에게 전파해 실패를 성공으로 처리하지 않도록 한다.
    """
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("run_id는 양의 정수여야 합니다.")
    if len(candidates) > 3:
        raise ValueError("후보는 최대 3개까지 저장할 수 있습니다.")
    validated = [CandidateInput.model_validate(item) for item in candidates]
    windows = {(item.day_of_week, item.start_time, item.end_time) for item in validated}
    if len(windows) != len(validated):
        raise ValueError("동일한 시간 후보를 중복 저장할 수 없습니다.")
    ordered = sorted(validated, key=lambda item: (-item.available_count, item.day_of_week, item.start_time))
    payload = [dict(item.model_dump(mode="json"), rank_no=rank)
               for rank, item in enumerate(ordered, start=1)]
    return CandidateSetOut.model_validate(repository.save(run_id, payload))


def read_latest_candidates(
    meeting_id: int, repository: RecommendationRepository,
) -> CandidateSetOut:
    try:
        result = repository.find_latest(meeting_id)
    except (APIError, HTTPError):
        logger.exception("Recommended candidate read failed")
        raise HTTPException(503, "추천 후보 조회에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None
    if result is None:
        raise HTTPException(404, "저장된 최신 추천 후보가 없습니다.")
    return CandidateSetOut.model_validate(result)
