from pydantic import BaseModel, Field


class VoteRequest(BaseModel):
    """후보 선호 투표 요청. (VOTE-01)

    선호 후보를 선택하거나, '참석 가능 후보 없음'(no_available=true)을 제출한다.
    둘은 동시에 지정할 수 없다.
    """

    candidate_ids: list[int] = Field(
        default_factory=list,
        description="선호하는 후보 id 목록 (같은 후보 묶음 내)",
        examples=[[1, 2]],
    )
    no_available: bool = Field(
        False, description="참석 가능 후보 없음 제출 여부", examples=[False]
    )


class BallotOut(BaseModel):
    """제출된 투표지 정보."""

    ballot_id: int = Field(..., description="투표지 번호", examples=[1])
    set_id: int = Field(..., description="후보 묶음 번호", examples=[1])
    member_id: int = Field(..., description="구성원 번호", examples=[1])
    no_available: bool = Field(..., description="참석 가능 후보 없음 여부", examples=[False])
    candidate_ids: list[int] = Field(
        ..., description="선택한 후보 id 목록", examples=[[1, 2]]
    )


class CandidateTally(BaseModel):
    """후보별 득표 집계. (VOTE-02)"""

    candidate_id: int = Field(..., examples=[1])
    rank_no: int = Field(..., description="묶음 내 추천 순위", examples=[1])
    day_of_week: int = Field(..., description="월=0 ~ 일=6", examples=[0])
    start_time: str = Field(..., examples=["10:00:00"])
    end_time: str = Field(..., examples=["11:00:00"])
    available_count: int = Field(..., description="참석 가능 인원", examples=[2])
    votes: int = Field(..., description="득표수", examples=[3])


class TallyOut(BaseModel):
    """후보 묶음 투표 집계 결과. (VOTE-02)"""

    set_id: int = Field(..., examples=[1])
    vote_status: str = Field(..., description="OPEN / CLOSED / DISCARDED", examples=["OPEN"])
    total_ballots: int = Field(..., description="제출된 투표지 수", examples=[5])
    no_available_count: int = Field(..., description="'참석 가능 후보 없음' 수", examples=[1])
    candidates: list[CandidateTally]
    winner_candidate_id: int | None = Field(
        None, description="현재 1위 후보 (동률 시 참석 인원 > 추천 순위)", examples=[1]
    )


class ConfirmRequest(BaseModel):
    """일정 확정 요청. 확정할 후보를 지정한다. (VOTE-03)"""

    candidate_id: int = Field(..., description="확정할 후보 id", examples=[1])


class ConfirmResult(BaseModel):
    """일정 확정 결과. (VOTE-03)

    확정 직전 재검사(팀원 시간표 변경 여부)를 수행한다.
    변경이 감지되면 확정하지 않고 재계산을 안내한다.
    """

    confirmed: bool = Field(..., description="확정 성공 여부", examples=[True])
    recheck_passed: bool = Field(..., description="재검사 통과 여부", examples=[True])
    detail: str = Field(..., description="결과 설명")
    meeting_id: int = Field(..., examples=[1])
    candidate_id: int = Field(..., examples=[1])
    confirmed_id: int | None = Field(None, description="확정 일정 id (성공 시)", examples=[1])


class ShareOut(BaseModel):
    """외부 공유 링크 발급 결과. (VOTE-04)"""

    share_token: str = Field(..., description="공유 토큰", examples=["Hs3kP0a9bQ"])
    share_url: str = Field(..., description="공유 조회 경로", examples=["/api/v1/share/Hs3kP0a9bQ"])


class PublicScheduleOut(BaseModel):
    """비회원용 확정 일정 읽기전용 조회 결과. (VOTE-04)"""

    meeting_name: str = Field(..., examples=["캡스톤 2조 정기회의"])
    day_of_week: int = Field(..., description="월=0 ~ 일=6", examples=[0])
    start_time: str = Field(..., examples=["10:00:00"])
    end_time: str = Field(..., examples=["11:00:00"])
    confirmed_at: str = Field(..., description="확정 시각")
