from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from posture.domain.stance import Stance, stance_for

MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class HeightEvent:
    ts: datetime
    # In force until the next event, also while the Connection is down or Posture is stopped.
    height_cm: float


@dataclass(frozen=True)
class StancePeriod:
    stance: Stance
    since: datetime


def _segments(
    events: list[HeightEvent], start: datetime, end: datetime
) -> list[tuple[datetime, datetime, float | None]]:
    # Everything is converted to UTC because subtracting aware datetimes that share a tzinfo
    # ignores DST changes. Events must be sorted by time.
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    segments: list[tuple[datetime, datetime, float | None]] = []
    cursor, height = start, None
    for event in events:
        ts = event.ts.astimezone(UTC)
        if ts <= start:
            height = event.height_cm
            continue
        if ts >= end:
            break
        segments.append((cursor, ts, height))
        cursor, height = ts, event.height_cm
    if end > cursor:
        segments.append((cursor, end, height))
    return segments


def stance_totals(
    events: list[HeightEvent], start: datetime, end: datetime, threshold_cm: float
) -> dict[Stance, timedelta]:
    totals = {Stance.SITTING: timedelta(), Stance.STANDING: timedelta()}
    for seg_start, seg_end, height in _segments(events, start, end):
        if height is not None:
            totals[stance_for(height, threshold_cm)] += seg_end - seg_start
    return totals


def minute_series(
    events: list[HeightEvent], start: datetime, end: datetime, now: datetime
) -> list[float | None]:
    """Height in force at the start of each minute of [start, end); None when unknown or future."""
    segments = _segments(events, start, min(end, now))
    series: list[float | None] = []
    minute, end, i = start.astimezone(UTC), end.astimezone(UTC), 0
    while minute < end:
        while i < len(segments) and segments[i][1] <= minute:
            i += 1
        series.append(segments[i][2] if i < len(segments) else None)
        minute += MINUTE
    return series


def stance_period(events: list[HeightEvent], threshold_cm: float) -> StancePeriod | None:
    """Find the current Stance period from Height events sorted by time."""
    period = None
    for event in reversed(events):
        stance = stance_for(event.height_cm, threshold_cm)
        if period is not None and period.stance is not stance:
            break
        period = StancePeriod(stance, event.ts)
    return period
