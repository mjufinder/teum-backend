import pytest

from app.domain.timetable import Timetable


def test_weekday_matrix_serialization():
    matrix = [[1] * 5 for _ in range(26)]
    matrix[0][0] = 0
    matrix[2][1] = 0
    matrix[25][4] = 0
    timetable = Timetable.from_weekday_matrix(matrix)
    assert [i for i, bit in enumerate(timetable.class_bits) if bit == "0"] == [0, 28, 129]
    assert timetable.class_bits[130:] == "1" * 52
    assert timetable.manual_bits == "1" * 182


def test_and_preserves_leading_zeros_and_saved_weekend():
    timetable = Timetable("01" + "1" * 180, "10" + "1" * 179 + "0")
    assert timetable.available_bits == "00" + "1" * 179 + "0"
    assert timetable.manual_bits[-1] == "0"


@pytest.mark.parametrize("bits", [None, 1, "", "1" * 181, "1" * 183, "x" * 182])
@pytest.mark.parametrize("field", ["class_bits", "manual_bits"])
def test_invalid_bits(bits, field):
    values = {"class_bits": "1" * 182, "manual_bits": "1" * 182}
    values[field] = bits
    with pytest.raises(ValueError):
        Timetable(**values)


@pytest.mark.parametrize("matrix", [[], [[1] * 5] * 25, [[1] * 4] * 26,
                                   [[2] * 5] * 26, [[True] * 5] * 26,
                                   [[1.0] * 5] * 26])
def test_invalid_matrix(matrix):
    with pytest.raises(ValueError):
        Timetable.from_weekday_matrix(matrix)
