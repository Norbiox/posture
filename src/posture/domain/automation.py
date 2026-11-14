from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


def timer_due(
    timer: Timer,
    now: datetime,
    work_hours: WorkHours,
    period: StancePeriod | None,
    last_fired: datetime | None,
) -> bool:
    if period is None or period.stance is not timer.stance:
        return False
    if last_fired is not None and last_fired >= period.since:
        return False
    # Time before Work Hours started today does not count towards the Timer.
    work_start = datetime.combine(now.date(), work_hours.start, now.tzinfo)
    anchor = max(period.since, work_start)
    return now.astimezone(UTC) - anchor.astimezone(UTC) >= timedelta(minutes=timer.minutes)


def should_retry(
    retries_done: int,
    max_retries: int,
    *,
    active: bool,
    stance: Stance | None,
    first_stance: Stance | None,
) -> bool:
    return retries_done < max_retries and active and stance is first_stance
