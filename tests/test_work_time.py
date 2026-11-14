from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from posture.domain.work_time import WorkHours, day_bounds, is_work_time

HOURS = WorkHours(time(7, 0), time(17, 0))
WORKDAYS = frozenset(range(5))
HOLIDAYS = frozenset({date(2026, 11, 11)})  # a Wednesday


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 11, 10, 7, 0, tzinfo=UTC), True),  # Tuesday, start is inclusive
        (datetime(2026, 11, 10, 16, 59, tzinfo=UTC), True),
        (datetime(2026, 11, 10, 17, 0, tzinfo=UTC), False),  # end is exclusive
        (datetime(2026, 11, 10, 6, 59, tzinfo=UTC), False),
        (datetime(2026, 11, 14, 10, 0, tzinfo=UTC), False),  # Saturday is not a Workday
        (datetime(2026, 11, 11, 10, 0, tzinfo=UTC), False),  # Holiday on a Workday
    ],
)
def test_is_work_time(now: datetime, *, expected: bool) -> None:
    assert is_work_time(now, HOURS, WORKDAYS, HOLIDAYS) is expected


@pytest.mark.parametrize(
    ("day", "hours"),
    [(date(2026, 11, 14), 24), (date(2026, 3, 29), 23), (date(2026, 10, 25), 25)],
)
def test_day_bounds_follow_dst(day: date, hours: int) -> None:
    start, end = day_bounds(day, ZoneInfo("Europe/Warsaw"))
    assert (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() == hours * 3600
