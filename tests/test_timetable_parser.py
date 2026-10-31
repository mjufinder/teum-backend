import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from app.services import timetable_parser as timetable


class FixedTimeRangeTests(unittest.TestCase):
    def parse_image(self, start_hour, end_hour, class_hour, day=0):
        vertical = np.array([0, 40, 140, 240, 340, 440, 540])
        hours = np.arange(20, 20 + (end_hour - start_hour + 1) * 100, 100)
        pixels = np.full((hours[-1] + 1, 541, 3), 255, dtype=np.uint8)
        top = 20 + (class_hour - start_hour) * 100
        left = vertical[day + 1]
        pixels[top + 1:top + 50, left + 1:left + 100] = [240, 150, 150]
        boxes = [(str(hour), 10, 25 + index * 100, 30, 45 + index * 100)
                 for index, hour in enumerate(range(start_hour, end_hour))]
        boxes.append(("class", left + 10, top + 10, left + 60, top + 30))
        boxes.extend((label, 60 + day * 100, 2, 80 + day * 100, 18)
                     for day, label in enumerate("월화수목금"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timetable.png"
            Image.fromarray(pixels).save(path)
            with patch.object(timetable, "_find_grid", return_value=(vertical, hours)), \
                 patch.object(timetable, "_get_text_boxes", return_value=boxes):
                return timetable.get_exact_timetable_matrix(path, return_time_slots=True)

    def test_missing_nine_keeps_ten_oclock_class_at_ten(self):
        matrix, slots = self.parse_image(10, 19, 10)
        self.assertEqual(matrix.shape, (26, 5))
        self.assertEqual(slots[0], ("09:00", "09:30"))
        self.assertEqual(slots[-1], ("21:30", "22:00"))
        self.assertEqual(slots[2], ("10:00", "10:30"))
        self.assertEqual(matrix[2, 0], 0)
        self.assertEqual(matrix.sum(), 129)

    def test_nine_oclock_class_and_friday_column(self):
        matrix, _ = self.parse_image(9, 19, 9, day=4)
        self.assertEqual(matrix[0, 4], 0)
        self.assertEqual(matrix.sum(), 129)

    def test_outside_hours_are_excluded(self):
        for class_hour in (8, 22):
            with self.subTest(class_hour=class_hour):
                matrix, _ = self.parse_image(8, 23, class_hour)
                self.assertEqual(matrix.shape, (26, 5))
                self.assertEqual(matrix.sum(), 130)

    def test_late_class_retains_its_time(self):
        matrix, slots = self.parse_image(10, 22, 21)
        self.assertEqual(slots[24], ("21:00", "21:30"))
        self.assertEqual(matrix[24, 0], 0)
        self.assertEqual(matrix.sum(), 129)


@pytest.mark.parametrize("labels", [list("월화수목금"), [d + "요일" for d in "월화수목금"]])
def test_weekday_headers_valid(labels):
    boxes = [(label, 60 + day * 100, 2, 90 + day * 100, 18)
             for day, label in enumerate(labels)]
    timetable._validate_weekday_headers(boxes, np.array([0, 40, 140, 240, 340, 440, 540]), 20)


@pytest.mark.parametrize("labels", [list("월화수목"), list("화월수목금"),
                                   list("월화수목토"), list("월월수목금"), []])
def test_weekday_headers_reject_missing_wrong_order_or_weekend(labels):
    boxes = [(label, 60 + day * 100, 2, 90 + day * 100, 18)
             for day, label in enumerate(labels)]
    with pytest.raises(timetable.WeekdayHeaderError):
        timetable._validate_weekday_headers(boxes, np.array([0, 40, 140, 240, 340, 440, 540]), 20)


def test_weekdays_in_class_area_do_not_replace_missing_header():
    boxes = [(label, 60 + day * 100, 22, 90 + day * 100, 38)
             for day, label in enumerate("월화수목금")]
    with pytest.raises(timetable.WeekdayHeaderError):
        timetable._validate_weekday_headers(boxes, np.array([0, 40, 140, 240, 340, 440, 540]), 20)


if __name__ == "__main__":
    unittest.main()
