from typing import Literal

from pydantic import BaseModel, Field


class TimetableRecognitionOut(BaseModel):
    """요일별 26비트를 월~일 순서로 연결. 1=가능, 0=불가."""

    class_bits: str = Field(pattern=r"^[01]{182}$")
    manual_bits: str = Field(default="1" * 182, pattern=r"^[01]{182}$")
    available_bits: str = Field(pattern=r"^[01]{182}$")
    days: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    start_time: Literal["09:00"] = "09:00"
    end_time: Literal["22:00"] = "22:00"
    slot_minutes: Literal[30] = 30
    slots_per_day: Literal[26] = 26
    bit_order: Literal["day_major"] = "day_major"
    warnings: list[str]
