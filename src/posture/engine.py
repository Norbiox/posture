import asyncio
import itertools
from datetime import UTC, datetime, time
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from posture.db import AutomationRow, Db, Settings
from posture.desk import DeskController, DeskError
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
from posture.domain.stats import HeightEvent, StancePeriod, stance_period
from posture.domain.work_time import is_work_time

if TYPE_CHECKING:
    from collections.abc import Callable

    from posture.config import Config

RETRY_DELAY_S = 60
RECENT_EVENTS = 500  # enough history to find when the current Stance period began


class Engine:
    """Runs Automations. All decisions live in posture.domain; this only gathers the inputs."""

    def __init__(self, config: Config, db: Db, desk: DeskController) -> None:
        self._config = config
        self._db = db
        self._desk = desk
        self._scheduler = AsyncIOScheduler(timezone=config.tz)
        self._last_fired: dict[int, datetime] = {}
        self._running: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        await self._log_missed()
        self._scheduler.add_job(self._tick, "cron", minute="*", misfire_grace_time=30)
        self._scheduler.start()

    async def _log_missed(self) -> None:
        # Automations do not catch up after downtime; the log says what was skipped.
        now = datetime.now(self._config.tz)
        last_tick = await asyncio.to_thread(self._db.get_last_tick)
        if last_tick is None:
            return
        _, is_active, automations, _ = await asyncio.to_thread(self._read, now)
        schedules = [
            Schedule(a.id, time.fromisoformat(a.time_of_day))
            for a in automations
            if a.enabled and a.kind == "schedule" and a.time_of_day is not None
        ]
        for schedule, due in missed_schedules(schedules, last_tick, now, is_active):
            logger.warning(
                "Schedule {} was due at {} but Posture was not running; skipped",
                schedule.id,
                due.astimezone(self._config.tz).isoformat(timespec="minutes"),
            )

    async def timer_due_times(self) -> dict[int, datetime]:
        """When each enabled Timer fires in the current Stance period; others are left out."""
        now = datetime.now(self._config.tz)
        settings, _, automations, events = await asyncio.to_thread(self._read, now)
        period = stance_period(events, settings.threshold_cm)
        due: dict[int, datetime] = {}
        for automation in automations:
            match automation:
                case AutomationRow(
                    id=id_,
                    enabled=True,
                    kind="timer",
                    stance=str() as stance,
                    minutes=int() as minutes,
                ):
                    timer = Timer(id_, Stance(stance), minutes)
                    last_fired = self._last_fired.get(id_)
                    due_at = timer_due_at(timer, now, settings.work_hours(), period, last_fired)
                    if due_at is not None:
                        due[id_] = due_at
                case _:
                    pass
        return due

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        for task in self._running:
            task.cancel()
        await asyncio.gather(*self._running, return_exceptions=True)

    def _read(
        self, now: datetime
    ) -> tuple[Settings, Callable[[datetime], bool], list[AutomationRow], list[HeightEvent]]:
        settings = self._db.get_settings()
        holidays = frozenset(h.date for h in self._db.list_holidays([now.year - 1, now.year]))
        pause_until = self._db.get_pause_until()
        work_hours, workdays = settings.work_hours(), frozenset(settings.workdays)

        def is_active(at: datetime) -> bool:
            paused = pause_until is not None and at < pause_until
            return not paused and is_work_time(at, work_hours, workdays, holidays)

        automations = self._db.list_automations()
        return settings, is_active, automations, self._db.recent_events(RECENT_EVENTS)

    async def _tick(self) -> None:
        now = datetime.now(self._config.tz)
        settings, is_active, automations, events = await asyncio.to_thread(self._read, now)
        await asyncio.to_thread(self._db.set_last_tick, now)
        if not is_active(now):
            return
        period = stance_period(events, settings.threshold_cm)
        for automation in automations:
            if automation.enabled and self._due(automation, now, settings, period):
                logger.info("Automation {} ({}) is due", automation.id, automation.kind)
                self._last_fired[automation.id] = now.astimezone(UTC)
                task = asyncio.create_task(self._execute(automation, period))
                self._running.add(task)
                task.add_done_callback(self._running.discard)

    def _due(
        self,
        automation: AutomationRow,
        now: datetime,
        settings: Settings,
        period: StancePeriod | None,
    ) -> bool:
        match automation:
            case AutomationRow(id=id_, kind="schedule", time_of_day=str() as time_of_day):
                return schedule_due(Schedule(id_, time.fromisoformat(time_of_day)), now)
            case AutomationRow(
                id=id_, kind="timer", stance=str() as stance, minutes=int() as minutes
            ):
                timer = Timer(id_, Stance(stance), minutes)
                last_fired = self._last_fired.get(id_)
                return timer_due(timer, now, settings.work_hours(), period, last_fired)
            case _:
                return False

    async def _execute(self, automation: AutomationRow, period: StancePeriod | None) -> None:
        first_stance = period.stance if period else None
        for retries_done in itertools.count():
            height = await asyncio.to_thread(self._db.preset_height, automation.preset_id)
            if height is None:
                logger.warning("Automation {} has no Preset", automation.id)
                return
            try:
                moved = await self._desk.move_to(height, "automation")
            except DeskError as error:
                logger.warning("Automation {} failed: {}", automation.id, error)
            else:
                if moved:
                    logger.info("Automation {} moved the Desk to {} cm", automation.id, height)
                else:
                    logger.info(
                        "Automation {} skipped: the Desk is being moved by hand", automation.id
                    )
                return
            await asyncio.sleep(RETRY_DELAY_S)
            now = datetime.now(self._config.tz)
            settings, is_active, _, events = await asyncio.to_thread(self._read, now)
            current = stance_period(events, settings.threshold_cm)
            if not should_retry(
                retries_done + 1,
                self._config.retries,
                active=is_active(now),
                stance=current.stance if current else None,
                first_stance=first_stance,
            ):
                logger.warning("Automation {} gave up", automation.id)
                return
