import datetime as dt
import json
import os
import time

import pytest

from bengaluru import night
from bengaluru.areas import Area
from bengaluru.fetch import bounds_path, raw_dir
from bengaluru.night import NIGHT_WINDOW, closing_time, next_opening, schedule_wake
from bengaluru.prepare import stats_path


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


def test_the_next_opening_is_tonight_or_tomorrow_night():
    assert next_opening(NIGHT_WINDOW, at(16, "05:58")) == at(16, "23:00")
    assert next_opening(NIGHT_WINDOW, at(16, "23:00")) == at(17, "23:00")
    assert next_opening(NIGHT_WINDOW, at(17, "02:00")) == at(17, "23:00")


class Recorder:
    """Stands in for subprocess.run: records each command and answers as told."""

    def __init__(self, listed: str = "") -> None:
        self.commands: list[list[str]] = []
        self.listed = listed

    def __call__(self, command, **_):
        self.commands.append(command)
        return type("Done", (), {"returncode": 0, "stdout": self.listed, "stderr": ""})()


def test_no_wake_is_asked_for_without_the_permission(tmp_path, monkeypatch):
    run = Recorder()
    monkeypatch.setattr(night, "WAKE_RULE", tmp_path / "missing")
    monkeypatch.setattr(night.subprocess, "run", run)
    schedule_wake(at(16, "23:00"))
    assert run.commands == []


def test_a_wake_is_set_once_for_the_opening(tmp_path, monkeypatch):
    rule = tmp_path / "claude-wake"
    rule.write_text("")
    monkeypatch.setattr(night, "WAKE_RULE", rule)
    run = Recorder()
    monkeypatch.setattr(night.subprocess, "run", run)
    schedule_wake(at(16, "23:00"))
    assert run.commands[-1] == [
        "sudo",
        "-n",
        "/usr/bin/pmset",
        "schedule",
        "wake",
        "11/16/26 23:00:00",
    ]

    already = Recorder(listed=" [0]  wake at 11/16/2026 23:00:00 by 'pmset'")
    monkeypatch.setattr(night.subprocess, "run", already)
    schedule_wake(at(16, "23:00"))
    assert all(command[0] != "sudo" for command in already.commands)


def test_an_area_whose_bounds_moved_is_fetched_and_prepared_again(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = Area("city", 12.0, 77.0, 13.0, 78.0)
    after = Area("city", 12.0, 77.0, 13.5, 78.0)
    done: list[str] = []
    clock = iter(range(1, 100))

    def stamp(path):
        """Write a file a second later than the last, as the real steps take time."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        tick = next(clock)
        os.utime(path, (tick, tick))

    def fetch(area):
        done.append("fetch")
        stamp(raw_dir(area) / "SOURCES.txt")
        bounds_path(area).write_text(json.dumps(area.bounds))

    def prepare(area):
        done.append("prepare")
        stamp(stats_path(area))

    def build(_area, deadline):
        done.append("build")
        return deadline > time.time()

    monkeypatch.setattr(night, "fetch", fetch)
    monkeypatch.setattr(night, "prepare", prepare)
    monkeypatch.setattr(night, "build", build)
    later = time.time() + 60

    assert night._work(before, later)
    assert night._work(before, later)
    assert done == ["fetch", "prepare", "build", "build"]

    del done[:]
    assert night._work(after, later)
    assert done == ["fetch", "prepare", "build"]
