from dataclasses import dataclass
from typing import ClassVar, Sequence


@dataclass(frozen=True)
class Timetable:
    """월~일, 09~22시의 가능 시간. 왼쪽부터 요일별 26칸, 1=가능."""

    class_bits: str
    manual_bits: str

    DAYS: ClassVar[tuple[str, ...]] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    START_HOUR: ClassVar[int] = 9
    END_HOUR: ClassVar[int] = 22
    SLOT_MINUTES: ClassVar[int] = 30
    SLOTS_PER_DAY: ClassVar[int] = 26
    TOTAL_BITS: ClassVar[int] = 182

    def __post_init__(self) -> None:
        for name in ("class_bits", "manual_bits"):
            bits = getattr(self, name)
            if not isinstance(bits, str) or len(bits) != self.TOTAL_BITS:
                raise ValueError(f"{name}는 {self.TOTAL_BITS}자리 문자열이어야 합니다.")
            if any(bit not in "01" for bit in bits):
                raise ValueError(f"{name}에는 0과 1만 사용할 수 있습니다.")

    @classmethod
    def from_weekday_matrix(cls, matrix: Sequence[Sequence[int]]) -> "Timetable":
        """OCR 초안을 생성한다. 저장된 시간표 복원에는 생성자를 직접 사용한다."""
        if len(matrix) != cls.SLOTS_PER_DAY:
            raise ValueError("시간표는 26개의 시간 구간이어야 합니다.")
        if any(not isinstance(row, (list, tuple)) or len(row) != 5 for row in matrix):
            raise ValueError("각 시간 구간에는 월~금 5개 값이 필요합니다.")
        if any(type(value) is not int or value not in (0, 1)
               for row in matrix for value in row):
            raise ValueError("시간표 값은 정수 0 또는 1이어야 합니다.")
        weekday_bits = "".join(
            str(matrix[slot][day])
            for day in range(5)
            for slot in range(cls.SLOTS_PER_DAY)
        )
        return cls(
            class_bits=weekday_bits + "1" * (cls.SLOTS_PER_DAY * 2),
            manual_bits="1" * cls.TOTAL_BITS,
        )

    @property
    def available_bits(self) -> str:
        result = int(self.class_bits, 2) & int(self.manual_bits, 2)
        return format(result, f"0{self.TOTAL_BITS}b")
