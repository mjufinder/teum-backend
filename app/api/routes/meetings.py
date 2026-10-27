from fastapi import APIRouter, Depends, status

from app.api.deps import get_meeting_repository
from app.domain.meeting import Meeting
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import MeetingCreateRequest, MeetingOut

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post(
    "",
    response_model=MeetingOut,
    status_code=status.HTTP_201_CREATED,
    summary="모임 생성",
)
def create_meeting(
    payload: MeetingCreateRequest,
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> MeetingOut:
    """모임을 생성한다 (MEETING-01).

    컨트롤러 → `Meeting.create()`(domain) → `MeetingRepository`(DB) 흐름으로 처리.
    """
    meeting = Meeting.create(
        name=payload.name,
        description=payload.description,
        period_start=payload.period_start,
        period_end=payload.period_end,
        search_start_time=payload.search_start_time,
        search_end_time=payload.search_end_time,
        min_duration_min=payload.min_duration_min,
        travel_buffer_min=payload.travel_buffer_min,
        repo=meeting_repo,
    )

    return MeetingOut(
        meeting_id=meeting.meeting_id,
        name=meeting.name,
        description=meeting.description,
        period_start=meeting.period_start,
        period_end=meeting.period_end,
        search_start_time=meeting.search_start_time,
        search_end_time=meeting.search_end_time,
        travel_buffer_min=meeting.travel_buffer_min,
        min_duration_min=meeting.min_duration_min,
        needs_recalc=meeting.needs_recalc,
    )
