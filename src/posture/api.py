import asyncio
import contextlib
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time, timedelta
from sqlite3 import IntegrityError
from typing import TYPE_CHECKING, Annotated, Literal, cast

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, model_validator
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocketDisconnect

from posture import logs
from posture.db import AutomationRow, Db, Holiday, Preset, Settings
from posture.desk import MAX_CM, MIN_CM, DeskController, DeskError, Direction
from posture.domain.stance import Stance, stance_for
from posture.domain.stats import minute_series, stance_totals
from posture.domain.work_time import day_bounds

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from posture.config import Config

Height = Annotated[float, Field(ge=MIN_CM, le=MAX_CM)]
Weekday = Annotated[int, Field(ge=0, le=6)]

router = APIRouter(prefix="/api")


class State(BaseModel):
    height_cm: float | None
    stance: Stance | None
    moving: bool
    connected: bool
    paused: bool


class Hub:
    """Fans messages out to WebSocket clients; safe to call from any thread."""

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self._queues: set[asyncio.Queue[dict[str, object]]] = set()

    def publish(self, message: dict[str, object]) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self._fan_out, message)

    def _fan_out(self, message: dict[str, object]) -> None:
        for queue in self._queues:
            # A client too slow to keep up loses messages instead of blocking the rest.
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(message)

    @contextlib.contextmanager
    def subscribe(self) -> Generator[asyncio.Queue[dict[str, object]]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=200)
        self._queues.add(queue)
        try:
            yield queue
        finally:
            self._queues.discard(queue)


class Context:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.db = Db(config.db_path)
        self.hub = Hub()
        self.desk = DeskController(config.desk_mac, self._record, self._on_change)
        # Cached so live Height messages need no database read.
        self.threshold_cm = 90.0
        self.pause_until: datetime | None = None

    async def _record(self, ts: datetime, height_cm: float | None) -> None:
        await asyncio.to_thread(self.db.add_event, ts, height_cm)

    def _on_change(self, kind: Literal["height", "state"]) -> None:
        state = self.state()
        if kind == "state":
            self.hub.publish({"type": "state", **state.model_dump(mode="json")})
        else:
            self.hub.publish(
                {
                    "type": "height",
                    "height_cm": state.height_cm,
                    "stance": state.stance,
                    "moving": state.moving,
                }
            )

    def state(self) -> State:
        height = self.desk.height_cm
        return State(
            height_cm=height,
            stance=None if height is None else stance_for(height, self.threshold_cm),
            moving=self.desk.moving,
            connected=self.desk.connected,
            paused=self.pause_until is not None and datetime.now(UTC) < self.pause_until,
        )

    def broadcast_state(self) -> State:
        state = self.state()
        self.hub.publish({"type": "state", **state.model_dump(mode="json")})
        return state


def get_context(connection: HTTPConnection) -> Context:
    return cast("Context", connection.app.state.ctx)


Ctx = Annotated[Context, Depends(get_context)]


# Desk control


@router.get("/state")
def get_state(ctx: Ctx) -> State:
    return ctx.state()


class MoveIn(BaseModel):
    preset: str | None = None
    height_cm: Height | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> MoveIn:
        if (self.preset is None) == (self.height_cm is None):
            msg = "give either preset or height_cm"
            raise ValueError(msg)
        return self


@router.post("/move")
async def move(body: MoveIn, ctx: Ctx) -> State:
    height = body.height_cm
    if body.preset is not None:
        preset = await asyncio.to_thread(ctx.db.get_preset, body.preset)
        if preset is None:
            raise HTTPException(404, f"Unknown preset {body.preset!r}")
        height = preset.height_cm
    if height is not None:
        await ctx.desk.move_to(height, "human")
    return ctx.state()


@router.post("/stop")
async def stop(ctx: Ctx) -> State:
    await ctx.desk.stop()
    return ctx.state()


def _end_of_today(ctx: Context) -> datetime:
    return day_bounds(datetime.now(ctx.config.tz).date(), ctx.config.tz)[1]


@router.post("/pause")
async def pause(ctx: Ctx) -> State:
    ctx.pause_until = _end_of_today(ctx)
    await asyncio.to_thread(ctx.db.set_pause_until, ctx.pause_until)
    return ctx.broadcast_state()


@router.delete("/pause")
async def unpause(ctx: Ctx) -> State:
    ctx.pause_until = None
    await asyncio.to_thread(ctx.db.set_pause_until, None)
    return ctx.broadcast_state()


# Presets


class PresetIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    # Omitted means "save the current Height".
    height_cm: Height | None = None


def _height_or_current(ctx: Context, height_cm: float | None) -> float:
    height = height_cm if height_cm is not None else ctx.desk.height_cm
    if height is None:
        raise HTTPException(409, "Height is unknown while the Desk is disconnected")
    return height


@router.get("/presets")
async def list_presets(ctx: Ctx) -> list[Preset]:
    return await asyncio.to_thread(ctx.db.list_presets)


@router.post("/presets", status_code=201)
async def create_preset(body: PresetIn, ctx: Ctx) -> Preset:
    height = _height_or_current(ctx, body.height_cm)
    try:
        return await asyncio.to_thread(ctx.db.add_preset, body.name, height)
    except IntegrityError:
        raise HTTPException(409, "A Preset with this name already exists") from None


@router.put("/presets/{preset_id}")
async def update_preset(preset_id: int, body: PresetIn, ctx: Ctx) -> Preset:
    height = _height_or_current(ctx, body.height_cm)
    try:
        found = await asyncio.to_thread(ctx.db.update_preset, preset_id, body.name, height)
    except IntegrityError:
        raise HTTPException(409, "A Preset with this name already exists") from None
    if not found:
        raise HTTPException(404, "Unknown Preset")
    return Preset(preset_id, body.name, height)


@router.delete("/presets/{preset_id}", status_code=204)
async def delete_preset(preset_id: int, ctx: Ctx) -> None:
    try:
        found = await asyncio.to_thread(ctx.db.delete_preset, preset_id)
    except IntegrityError:
        raise HTTPException(409, "An Automation uses this Preset") from None
    if not found:
        raise HTTPException(404, "Unknown Preset")


# Automations


class AutomationIn(BaseModel):
    kind: Literal["schedule", "timer"]
    enabled: bool = True
    preset_id: int
    time_of_day: time | None = None  # Schedule only
    stance: Stance | None = None  # Timer only
    minutes: Annotated[int, Field(ge=1, le=1440)] | None = None  # Timer only

    @model_validator(mode="after")
    def fields_match_kind(self) -> AutomationIn:
        if self.kind == "schedule":
            valid = self.time_of_day is not None and self.stance is None and self.minutes is None
        else:
            valid = (
                self.time_of_day is None and self.stance is not None and self.minutes is not None
            )
        if not valid:
            msg = "a Schedule takes time_of_day only, a Timer takes stance and minutes only"
            raise ValueError(msg)
        return self

    def row(self, automation_id: int = 0) -> AutomationRow:
        return AutomationRow(
            automation_id,
            self.kind,
            self.enabled,
            self.preset_id,
            self.time_of_day.strftime("%H:%M") if self.time_of_day else None,
            self.stance,
            self.minutes,
        )


@router.get("/automations")
async def list_automations(ctx: Ctx) -> list[AutomationRow]:
    return await asyncio.to_thread(ctx.db.list_automations)


@router.post("/automations", status_code=201)
async def create_automation(body: AutomationIn, ctx: Ctx) -> AutomationRow:
    try:
        return await asyncio.to_thread(ctx.db.add_automation, body.row())
    except IntegrityError:
        raise HTTPException(422, "Unknown Preset") from None


@router.put("/automations/{automation_id}")
async def update_automation(automation_id: int, body: AutomationIn, ctx: Ctx) -> AutomationRow:
    row = body.row(automation_id)
    try:
        found = await asyncio.to_thread(ctx.db.update_automation, row)
    except IntegrityError:
        raise HTTPException(422, "Unknown Preset") from None
    if not found:
        raise HTTPException(404, "Unknown Automation")
    return row


@router.delete("/automations/{automation_id}", status_code=204)
async def delete_automation(automation_id: int, ctx: Ctx) -> None:
    if not await asyncio.to_thread(ctx.db.delete_automation, automation_id):
        raise HTTPException(404, "Unknown Automation")


# Settings and Holidays


class SettingsIn(BaseModel):
    work_start: time
    work_end: time
    workdays: Annotated[list[Weekday], Field(max_length=7)]
    threshold_cm: Height

    @model_validator(mode="after")
    def start_before_end(self) -> SettingsIn:
        if self.work_start >= self.work_end:
            msg = "work_start must be before work_end"
            raise ValueError(msg)
        return self


@router.get("/settings")
async def get_settings(ctx: Ctx) -> Settings:
    return await asyncio.to_thread(ctx.db.get_settings)


@router.put("/settings")
async def put_settings(body: SettingsIn, ctx: Ctx) -> Settings:
    settings = Settings(
        body.work_start.strftime("%H:%M"),
        body.work_end.strftime("%H:%M"),
        sorted(set(body.workdays)),
        body.threshold_cm,
    )
    await asyncio.to_thread(ctx.db.put_settings, settings)
    ctx.threshold_cm = settings.threshold_cm
    ctx.broadcast_state()
    return settings


class HolidayIn(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=60)


@router.get("/holidays")
async def list_holidays(ctx: Ctx) -> list[Holiday]:
    year = datetime.now(ctx.config.tz).year
    return await asyncio.to_thread(ctx.db.list_holidays, [year, year + 1])


@router.post("/holidays", status_code=201)
async def add_holiday(body: HolidayIn, ctx: Ctx) -> HolidayIn:
    await asyncio.to_thread(ctx.db.add_holiday, body.date, body.name)
    return body


@router.delete("/holidays/{day}", status_code=204)
async def delete_holiday(day: date, ctx: Ctx) -> None:
    if not await asyncio.to_thread(ctx.db.delete_holiday, day):
        raise HTTPException(404, "No manual Holiday on this date")


# Statistics and logs


class DayStats(BaseModel):
    date: date
    # Height at the start of each minute of the day, null when unknown.
    heights: list[float | None]
    threshold_cm: float
    sitting_s: int
    standing_s: int


class DayTotals(BaseModel):
    date: date
    sitting_s: int
    standing_s: int


def _seconds(delta: timedelta) -> int:
    return int(delta.total_seconds())


@router.get("/stats/day")
async def stats_day(ctx: Ctx, day: Annotated[date | None, Query(alias="date")] = None) -> DayStats:
    tz = ctx.config.tz
    day = day or datetime.now(tz).date()
    start, end = day_bounds(day, tz)
    now = datetime.now(UTC)
    events = await asyncio.to_thread(ctx.db.events_between, start, end)
    totals = stance_totals(events, start, min(end, now), ctx.threshold_cm)
    return DayStats(
        date=day,
        heights=minute_series(events, start, end, now),
        threshold_cm=ctx.threshold_cm,
        sitting_s=_seconds(totals[Stance.SITTING]),
        standing_s=_seconds(totals[Stance.STANDING]),
    )


@router.get("/stats/daily")
async def stats_daily(ctx: Ctx, days: Annotated[int, Query(ge=1, le=90)] = 7) -> list[DayTotals]:
    tz = ctx.config.tz
    today = datetime.now(tz).date()
    first = today - timedelta(days=days - 1)
    now = datetime.now(UTC)
    events = await asyncio.to_thread(
        ctx.db.events_between, day_bounds(first, tz)[0], day_bounds(today, tz)[1]
    )
    result = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        start, end = day_bounds(day, tz)
        totals = stance_totals(events, start, min(end, now), ctx.threshold_cm)
        result.append(
            DayTotals(
                date=day,
                sitting_s=_seconds(totals[Stance.SITTING]),
                standing_s=_seconds(totals[Stance.STANDING]),
            )
        )
    return result


@router.get("/logs")
async def get_logs(
    ctx: Ctx, lines: Annotated[int, Query(ge=1, le=1000)] = 200
) -> list[dict[str, str]]:
    return await asyncio.to_thread(logs.tail, ctx.config.log_path, lines)


# WebSocket


class Hold(BaseModel):
    type: Literal["hold"]
    direction: Direction


class Release(BaseModel):
    type: Literal["release"]


client_message = TypeAdapter(Annotated[Hold | Release, Field(discriminator="type")])


async def _send_messages(websocket: WebSocket, queue: asyncio.Queue[dict[str, object]]) -> None:
    while True:
        await websocket.send_json(await queue.get())


async def websocket_endpoint(websocket: WebSocket, ctx: Ctx) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "state", **ctx.state().model_dump(mode="json")})
    holding = False
    with ctx.hub.subscribe() as queue:
        sender = asyncio.create_task(_send_messages(websocket, queue))
        try:
            async for raw in websocket.iter_json():
                try:
                    message = client_message.validate_python(raw)
                except ValidationError:
                    logger.warning("Ignoring invalid WebSocket message {}", raw)
                    continue
                try:
                    if isinstance(message, Hold):
                        holding = True
                        await ctx.desk.start_hold(message.direction)
                    else:
                        holding = False
                        await ctx.desk.stop()
                except DeskError as error:
                    logger.warning("{}", error)
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            if holding:
                # A client that vanishes while holding must not leave the Desk running.
                with contextlib.suppress(DeskError):
                    await ctx.desk.stop()


# App


def create_app(config: Config) -> FastAPI:
    ctx = Context(config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        ctx.hub.loop = asyncio.get_running_loop()
        logs.setup(config.log_path, ctx.hub.publish)
        settings = await asyncio.to_thread(ctx.db.get_settings)
        ctx.threshold_cm = settings.threshold_cm
        ctx.pause_until = await asyncio.to_thread(ctx.db.get_pause_until)
        desk_task = asyncio.create_task(ctx.desk.run())
        yield
        desk_task.cancel()
        await asyncio.wait({desk_task})

    app = FastAPI(title="Posture", lifespan=lifespan)
    app.state.ctx = ctx
    app.include_router(router)
    app.add_api_websocket_route("/ws", websocket_endpoint)

    @app.exception_handler(DeskError)
    def desk_error(_request: Request, error: DeskError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=503)

    # Mounted last so it does not shadow /api and /ws.
    if config.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=config.static_dir, html=True), name="static")
    return app
