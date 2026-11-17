import asyncio
import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from idasen import IdasenDesk
from loguru import logger

from posture.domain.move import interrupted

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

Source = Literal["human", "automation"]
Direction = Literal["up", "down"]

MIN_CM = 62.0
MAX_CM = 127.0
HOLD_INTERVAL_S = 0.2
REST_AFTER_S = 1.0  # no notification for this long means the Desk stopped
BACKOFF_MAX_S = 30.0
# Lets the Desk finish its anti-collision back-off before the move is resumed.
RETRY_DELAY_S = 2.0


class DeskError(Exception):
    pass


class FakeDesk:
    """Stands in for IdasenDesk (same methods, metres) so the app runs without hardware."""

    SPEED_M_S = 0.04
    TICK_S = 0.1
    TOLERANCE_M = 1e-4

    def __init__(self) -> None:
        self.is_connected = False
        self._height_m = 0.75
        self._callback: Callable[[float, float], Awaitable[None]] | None = None

    async def connect(self) -> None:
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def monitor(self, callback: Callable[[float, float], Awaitable[None]]) -> None:
        self._callback = callback

    async def get_height_and_speed(self) -> tuple[float, float]:
        return self._height_m, 0.0

    async def _step(self, delta_m: float, speed_m_s: float) -> None:
        low, high = MIN_CM / 100, MAX_CM / 100
        self._height_m = min(max(self._height_m + delta_m, low), high)
        if self._callback:
            await self._callback(self._height_m, speed_m_s)

    async def move_up(self) -> None:
        await self._step(self.SPEED_M_S * HOLD_INTERVAL_S, self.SPEED_M_S)

    async def move_down(self) -> None:
        await self._step(-self.SPEED_M_S * HOLD_INTERVAL_S, -self.SPEED_M_S)

    async def move_to_target(self, target_m: float) -> None:
        while abs(diff := target_m - self._height_m) > self.TOLERANCE_M:
            sign = 1 if diff > 0 else -1
            await self._step(
                sign * min(self.SPEED_M_S * self.TICK_S, abs(diff)), sign * self.SPEED_M_S
            )
            await asyncio.sleep(self.TICK_S)
        await self._step(0.0, 0.0)

    async def stop(self) -> None:
        pass


type Desk = IdasenDesk | FakeDesk


def make_desk(mac: str, on_lost: Callable[[], None]) -> Desk:
    if mac == "fake":
        return FakeDesk()
    return IdasenDesk(mac, disconnected_callback=lambda _client: on_lost())


def _log_failure(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and (error := task.exception()):
        logger.error("Moving the Desk failed: {}", error)


class DeskController:
    """Owns the persistent connection to the Desk (ADR 0001) and every move."""

    def __init__(
        self,
        mac: str,
        record: Callable[[datetime, float], Awaitable[None]],
        on_change: Callable[[Literal["height", "state"]], None],
    ) -> None:
        self.height_cm: float | None = None
        self.moving = False
        self.connected = False
        self._mac = mac
        self._record = record
        self._on_change = on_change
        self._desk: Desk | None = None
        self._task: asyncio.Task[None] | None = None
        self._source: Source | None = None
        self._rest_timer: asyncio.TimerHandle | None = None
        self._last_notification = datetime.now(UTC)
        self._recorded: float | None = None
        self._background: set[asyncio.Task[None]] = set()
        # How many times a move is resumed after an Interruption; set from Settings.
        self.move_retries = 2

    # Connection

    async def run(self) -> None:
        try:
            await self._connect_forever()
        finally:
            await self._cancel_move()
            if self._desk:
                with contextlib.suppress(Exception):
                    await self._desk.disconnect()

    async def _connect_forever(self) -> None:
        delay = 1.0
        while True:
            lost = asyncio.Event()
            desk = make_desk(self._mac, lost.set)
            try:
                await desk.connect()
                await desk.monitor(self._on_notification)
                height_m, _ = await desk.get_height_and_speed()
            except Exception as error:  # noqa: BLE001 - any failure must end in a reconnect
                logger.warning("Desk connection failed ({}), retrying in {:.0f} s", error, delay)
                with contextlib.suppress(Exception):
                    await desk.disconnect()
                await asyncio.sleep(delay)
                delay = min(delay * 2, BACKOFF_MAX_S)
                continue
            delay = 1.0
            await self._connected(desk, round(height_m * 100, 1))
            await lost.wait()
            await self._disconnected(desk)

    async def _connected(self, desk: Desk, height_cm: float) -> None:
        logger.info("Desk connected, Height {} cm", height_cm)
        self._desk, self.connected, self.height_cm = desk, True, height_cm
        if height_cm != self._recorded:
            await self._record_event(datetime.now(UTC), height_cm)
        self._on_change("state")

    async def _disconnected(self, desk: Desk) -> None:
        logger.warning("Desk connection lost")
        if self._rest_timer:
            self._rest_timer.cancel()
        await self._cancel_move()
        # The last known Height stays in force, so a short drop does not break a Stance period.
        self._desk, self.connected, self.moving = None, False, False
        self._on_change("state")
        with contextlib.suppress(Exception):
            await desk.disconnect()

    async def _record_event(self, ts: datetime, height_cm: float) -> None:
        self._recorded = height_cm
        await self._record(ts, height_cm)

    # Live Height

    async def _on_notification(self, height_m: float, speed_m_s: float) -> None:
        self.height_cm = round(height_m * 100, 1)
        self.moving = speed_m_s != 0
        self._last_notification = datetime.now(UTC)
        if self._rest_timer:
            self._rest_timer.cancel()
        self._rest_timer = asyncio.get_running_loop().call_later(REST_AFTER_S, self._at_rest)
        self._on_change("height")

    def _at_rest(self) -> None:
        self.moving = False
        self._on_change("height")
        if self.height_cm is not None and self.height_cm != self._recorded:
            task = asyncio.create_task(self._record_event(self._last_notification, self.height_cm))
            self._background.add(task)
            task.add_done_callback(self._background.discard)

    # Moves

    def _require(self) -> Desk:
        if self._desk is None:
            msg = "Desk is not connected"
            raise DeskError(msg)
        return self._desk

    async def _cancel_move(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.wait({self._task})
        self._task = None

    async def move_to(self, height_cm: float, source: Source) -> bool:
        """Move and wait for arrival. False when an Automation yields to a human-started move."""
        desk = self._require()
        if source == "automation" and self._human_move_running():
            return False
        await self._cancel_move()
        self._source = source
        task = self._task = asyncio.create_task(self._move(desk, height_cm, self.move_retries))
        await asyncio.wait({task})
        if not task.cancelled() and (error := task.exception()):
            raise DeskError(str(error)) from error
        return True

    async def _move(self, desk: Desk, target_cm: float, retries: int) -> None:
        # Runs as one task, so Stop, a hold or a newer move also cancels a pending retry.
        for attempt in range(retries + 1):
            await desk.move_to_target(target_cm / 100)
            height_m, _ = await desk.get_height_and_speed()
            height_cm = round(height_m * 100, 1)
            if not interrupted(height_cm, target_cm):
                return
            if attempt == retries:
                logger.warning(
                    "Move to {} cm interrupted at {} cm, leaving the Desk there after {} retries",
                    target_cm,
                    height_cm,
                    retries,
                )
                return
            logger.warning(
                "Move to {} cm interrupted at {} cm, retry {} of {}",
                target_cm,
                height_cm,
                attempt + 1,
                retries,
            )
            await asyncio.sleep(RETRY_DELAY_S)

    async def start_hold(self, direction: Direction) -> None:
        desk = self._require()
        await self._cancel_move()
        self._source = "human"
        self._task = asyncio.create_task(self._hold(desk, direction))
        self._task.add_done_callback(_log_failure)

    async def _hold(self, desk: Desk, direction: Direction) -> None:
        step = desk.move_up if direction == "up" else desk.move_down
        while True:
            await step()
            await asyncio.sleep(HOLD_INTERVAL_S)

    async def stop(self) -> None:
        desk = self._require()
        await self._cancel_move()
        await desk.stop()
        self.moving = False
        self._on_change("height")

    def _human_move_running(self) -> bool:
        return self._source == "human" and self._task is not None and not self._task.done()
