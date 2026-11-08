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
