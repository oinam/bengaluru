import datetime as dt

import pytest

from bengaluru.night import NIGHT_WINDOW, closing_time


def at(day: int, clock: str) -> dt.datetime:
    return dt.datetime.combine(dt.date(2026, 11, day), dt.time.fromisoformat(clock))


@pytest.mark.parametrize(
    ("now", "closes"),
    [
        (at(16, "23:00"), at(17, "04:00")),
        (at(16, "23:59"), at(17, "04:00")),
        (at(17, "00:00"), at(17, "04:00")),
        (at(17, "03:59"), at(17, "04:00")),
    ],
)
def test_the_night_window_closes_the_next_morning(now, closes):
    assert closing_time(NIGHT_WINDOW, now) == closes


@pytest.mark.parametrize("clock", ["04:00", "09:30", "17:45", "22:59"])
def test_nothing_starts_outside_the_night_window(clock):
    assert closing_time(NIGHT_WINDOW, at(16, clock)) is None


def test_a_daytime_window_closes_the_same_day():
    assert closing_time("10:00-12:30", at(16, "11:00")) == at(16, "12:30")
    assert closing_time("10:00-12:30", at(16, "12:30")) is None
