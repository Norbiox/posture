from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo


@dataclass(frozen=True)
class WorkHours:
    start: time
    end: time


def is_work_time(
    now: datetime,
    work_hours: WorkHours,
    workdays: frozenset[int],
    holidays: frozenset[date],
) -> bool:
    return (
        now.date() not in holidays
        and now.weekday() in workdays
        and work_hours.start <= now.time() < work_hours.end
    )


def day_bounds(day: date, tz: tzinfo) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, tz),
        datetime.combine(day + timedelta(days=1), time.min, tz),
    )
