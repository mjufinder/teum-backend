from datetime import time
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, model_validator

PositiveId = Annotated[int, Field(strict=True, gt=0)]


class CandidateInput(BaseModel):
    """내부 저장 함수 입력. 월~일 요일과 한국 현지 시각으로 표현한 주간 후보."""

    day_of_week: int = Field(strict=True, ge=0, le=6, description="월=0 ~ 일=6")
    start_time: time
    end_time: time
    available_count: int = Field(strict=True, gt=0)
    available_member_ids: list[PositiveId]

    @model_validator(mode="after")
    def validate_candidate(self):
        if self.start_time.tzinfo is not None or self.end_time.tzinfo is not None:
            raise ValueError("시간에는 UTC 오프셋을 넣지 않습니다. 한국 현지 시각을 사용하세요.")
        if not time(9) <= self.start_time < self.end_time <= time(22):
            raise ValueError("종료 시각은 시작 시각 이후여야 합니다.")
        if len(set(self.available_member_ids)) != len(self.available_member_ids):
            raise ValueError("참여 가능 팀원 ID가 중복되었습니다.")
        if self.available_count != len(self.available_member_ids):
            raise ValueError("참여 가능 인원수와 팀원 목록이 일치해야 합니다.")
        return self


class CandidateOut(BaseModel):
    candidate_id: int
    rank_no: int
    day_of_week: int = Field(strict=True, ge=0, le=6, description="월=0 ~ 일=6")
    start_time: time
    end_time: time
    available_count: int
    available_member_ids: list[int]


class CandidateSetOut(BaseModel):
    meeting_id: int
    run_id: int
    set_id: int
    result_status: Literal["HAS_CANDIDATE", "NO_CANDIDATE"]
    vote_status: Literal["OPEN", "CLOSED", "DISCARDED"]
    created_at: AwareDatetime
    candidates: list[CandidateOut]
