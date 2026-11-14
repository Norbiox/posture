from datetime import UTC, datetime, timedelta

import pytest

from posture.domain.stance import Stance
from posture.domain.stats import (
    HeightEvent,
    StancePeriod,
    minute_series,
    stance_period,
    stance_totals,
)

T0 = datetime(2026, 11, 14, 8, 0, tzinfo=UTC)
THRESHOLD = 90.0


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def ev(minutes: int, height: float) -> HeightEvent:
    return HeightEvent(at(minutes), height)


@pytest.mark.parametrize(
    ("events", "sitting", "standing"),
    [
        ([], 0, 0),  # nothing known
        ([ev(-30, 70)], 60, 0),  # state carried in from before the range
        ([ev(-30, 70), ev(20, 110)], 20, 40),
        ([ev(0, 110)], 0, 60),  # event exactly at the start
        ([ev(10, 70), ev(40, 110)], 30, 20),  # time before the first event is excluded
        ([ev(-5, 70), ev(60, 110)], 60, 0),  # event exactly at the end is outside
        ([ev(-5, 70), ev(90, 110)], 60, 0),
    ],
)
def test_stance_totals(events: list[HeightEvent], sitting: int, standing: int) -> None:
    totals = stance_totals(events, at(0), at(60), THRESHOLD)
    assert totals == {
        Stance.SITTING: timedelta(minutes=sitting),
        Stance.STANDING: timedelta(minutes=standing),
    }


def test_stance_totals_empty_range() -> None:
    totals = stance_totals([ev(-5, 70)], at(10), at(10), THRESHOLD)
    assert totals == {Stance.SITTING: timedelta(), Stance.STANDING: timedelta()}


def test_minute_series() -> None:
    events = [ev(-5, 70), ev(2, 110), ev(4, 75)]
    series = minute_series(events, at(0), at(8), at(6))
    assert series == [70, 70, 110, 110, 75, 75, None, None]  # minutes 6 and 7 are future


def test_minute_series_of_a_future_day() -> None:
    assert minute_series([ev(-5, 70)], at(10), at(12), at(0)) == [None, None]


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ([], None),
        ([ev(0, 70)], StancePeriod(Stance.SITTING, at(0))),
        ([ev(0, 70), ev(5, 75)], StancePeriod(Stance.SITTING, at(0))),  # same Stance keeps since
        ([ev(0, 70), ev(5, 110)], StancePeriod(Stance.STANDING, at(5))),
    ],
)
def test_stance_period(events: list[HeightEvent], expected: StancePeriod | None) -> None:
    assert stance_period(events, THRESHOLD) == expected
