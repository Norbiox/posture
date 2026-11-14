from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from posture.domain.stance import Stance
    from posture.domain.stats import StancePeriod
    from posture.domain.work_time import WorkHours


@dataclass(frozen=True)
class Schedule:
    id: int
    time_of_day: time


@dataclass(frozen=True)
class Timer:
    id: int
    stance: Stance
    minutes: int


# The engine only evaluates due-ness while it is work time and no Pause is on ("active").


def schedule_due(schedule: Schedule, now: datetime) -> bool:
    # Minute resolution: the engine ticks once a minute.
    return (now.hour, now.minute) == (schedule.time_of_day.hour, schedule.time_of_day.minute)


MISSED_LOOKBACK = timedelta(days=7)


def missed_schedules(
    schedules: list[Schedule],
    last_tick: datetime,
    now: datetime,
    is_active: Callable[[datetime], bool],
) -> list[tuple[Schedule, datetime]]:
    """Schedules that were due while Posture was not running, in (last_tick, now)."""
    # ponytail: minute-by-minute scan, capped at MISSED_LOOKBACK (~10k steps per Schedule)
    # Scan in now's timezone: Schedules are wall-clock times, last_tick may be stored in UTC.
    minute = max(last_tick.astimezone(now.tzinfo), now - MISSED_LOOKBACK)
    minute = minute.replace(second=0, microsecond=0)
    minute += timedelta(minutes=1)
    missed: list[tuple[Schedule, datetime]] = []
    while minute < now:
        missed += [(s, minute) for s in schedules if schedule_due(s, minute) and is_active(minute)]
        minute += timedelta(minutes=1)
    return missed


def timer_due_at(
    timer: Timer,
    now: datetime,
    work_hours: WorkHours,
    period: StancePeriod | None,
    last_fired: datetime | None,
) -> datetime | None:
    """When the Timer fires in the current Stance period, or None if it will not."""
    if period is None or period.stance is not timer.stance:
        return None
    if last_fired is not None and last_fired >= period.since:
        return None
    # Time before Work Hours started today does not count towards the Timer.
    work_start = datetime.combine(now.date(), work_hours.start, now.tzinfo)
    anchor = max(period.since, work_start)
    return anchor.astimezone(UTC) + timedelta(minutes=timer.minutes)


def timer_due(
    timer: Timer,
    now: datetime,
    work_hours: WorkHours,
    period: StancePeriod | None,
    last_fired: datetime | None,
) -> bool:
    due_at = timer_due_at(timer, now, work_hours, period, last_fired)
    return due_at is not None and now >= due_at


def should_retry(
    retries_done: int,
    max_retries: int,
    *,
    active: bool,
    stance: Stance | None,
    first_stance: Stance | None,
) -> bool:
    return retries_done < max_retries and active and stance is first_stance
