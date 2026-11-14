from datetime import UTC, datetime, time, timedelta, timezone

import pytest

from posture.domain.automation import (
    Schedule,
    Timer,
    missed_schedules,
    schedule_due,
    should_retry,
    timer_due,
    timer_due_at,
)
from posture.domain.stance import Stance
from posture.domain.stats import StancePeriod
from posture.domain.work_time import WorkHours

HOURS = WorkHours(time(7, 0), time(17, 0))
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
STANDING_TIMER = Timer(1, Stance.STANDING, 60)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 11, 10, 9, 30, 20, tzinfo=UTC), True),
        (datetime(2026, 11, 10, 9, 31, tzinfo=UTC), False),
        (datetime(2026, 11, 10, 10, 30, tzinfo=UTC), False),
    ],
)
def test_schedule_due(now: datetime, *, expected: bool) -> None:
    assert schedule_due(Schedule(1, time(9, 30)), now) is expected


def minutes_ago(minutes: int) -> datetime:
    return NOW - timedelta(minutes=minutes)


@pytest.mark.parametrize(
    ("period", "last_fired", "expected"),
    [
        (None, None, False),
        (StancePeriod(Stance.SITTING, minutes_ago(90)), None, False),  # wrong Stance
        (StancePeriod(Stance.STANDING, minutes_ago(59)), None, False),  # not long enough
        (StancePeriod(Stance.STANDING, minutes_ago(60)), None, True),
        (StancePeriod(Stance.STANDING, minutes_ago(90)), minutes_ago(100), True),  # old firing
        (StancePeriod(Stance.STANDING, minutes_ago(90)), minutes_ago(30), False),  # fired already
        # in Standing since 06:00, Work Hours started 07:00: 5 h counted
        (StancePeriod(Stance.STANDING, datetime(2026, 11, 10, 6, 0, tzinfo=UTC)), None, True),
    ],
)
def test_timer_due(
    period: StancePeriod | None, last_fired: datetime | None, *, expected: bool
) -> None:
    assert timer_due(STANDING_TIMER, NOW, HOURS, period, last_fired) is expected


def test_timer_ignores_time_before_work_hours() -> None:
    period = StancePeriod(Stance.STANDING, datetime(2026, 11, 10, 3, 0, tzinfo=UTC))
    now = datetime(2026, 11, 10, 7, 30, tzinfo=UTC)
    assert not timer_due(STANDING_TIMER, now, HOURS, period, None)
    assert timer_due(STANDING_TIMER, now + timedelta(minutes=30), HOURS, period, None)


@pytest.mark.parametrize(
    ("retries_done", "active", "stance", "expected"),
    [
        (0, True, Stance.SITTING, True),
        (4, True, Stance.SITTING, True),
        (5, True, Stance.SITTING, False),  # budget spent
        (1, False, Stance.SITTING, False),  # work time ended or Pause is on
        (1, True, Stance.STANDING, False),  # Stance changed since the first attempt
        (1, True, None, False),
    ],
)
def test_should_retry(
    retries_done: int, *, active: bool, stance: Stance | None, expected: bool
) -> None:
    result = should_retry(
        retries_done, 5, active=active, stance=stance, first_stance=Stance.SITTING
    )
    assert result is expected


def test_missed_schedules() -> None:
    nine, noon = Schedule(1, time(9, 0)), Schedule(2, time(12, 0))
    last_tick = datetime(2026, 11, 10, 8, 30, 15, tzinfo=UTC)
    now = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
    missed = missed_schedules([nine, noon], last_tick, now, lambda at: at.day == 10)
    assert missed == [
        (nine, datetime(2026, 11, 10, 9, 0, tzinfo=UTC)),
        (noon, datetime(2026, 11, 10, 12, 0, tzinfo=UTC)),
    ]


def test_missed_schedules_looks_back_at_most_a_week() -> None:
    now = datetime(2026, 11, 20, 0, 0, tzinfo=UTC)
    missed = missed_schedules([Schedule(1, time(9, 0))], NOW, now, lambda _: True)
    assert [due.day for _, due in missed] == [13, 14, 15, 16, 17, 18, 19]


def test_missed_schedules_use_the_wall_clock_of_now() -> None:
    warsaw = timezone(timedelta(hours=1))
    last_tick = datetime(2026, 11, 10, 7, 0, tzinfo=UTC)  # 08:00 in Warsaw
    now = datetime(2026, 11, 10, 10, 0, tzinfo=warsaw)
    missed = missed_schedules([Schedule(1, time(9, 0))], last_tick, now, lambda _: True)
    assert [due for _, due in missed] == [datetime(2026, 11, 10, 9, 0, tzinfo=warsaw)]


def test_timer_due_at() -> None:
    period = StancePeriod(Stance.STANDING, minutes_ago(20))
    assert timer_due_at(STANDING_TIMER, NOW, HOURS, period, None) == NOW + timedelta(minutes=40)
    assert timer_due_at(STANDING_TIMER, NOW, HOURS, period, minutes_ago(10)) is None
