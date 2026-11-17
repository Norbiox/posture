import asyncio
from typing import TYPE_CHECKING, Literal, override

import pytest

from posture import desk as desk_module
from posture.desk import DeskController, FakeDesk

if TYPE_CHECKING:
    from datetime import datetime

TARGET_CM = 110.0  # far enough from FakeDesk's 75 cm start that half the way is an Interruption


class KnockedDesk(FakeDesk):
    """Stops halfway on the first `knocks` moves, like a Desk whose anti-collision reacted."""

    def __init__(self, knocks: int) -> None:
        super().__init__()
        self.knocks = knocks
        self.moves = 0

    @override
    async def move_to_target(self, target_m: float) -> None:
        self.moves += 1
        if self.moves <= self.knocks:
            target_m = (self._height_m + target_m) / 2
        await super().move_to_target(target_m)


async def _move(desk: KnockedDesk, retries: int) -> float:
    connected = asyncio.Event()

    async def record(_ts: datetime, _height_cm: float) -> None:
        pass

    def on_change(kind: Literal["height", "state"]) -> None:
        if kind == "state":
            connected.set()

    controller = DeskController("fake", record, on_change)
    controller.move_retries = retries
    runner = asyncio.create_task(controller.run())
    await connected.wait()
    await controller.move_to(TARGET_CM, "human")
    height, _ = await desk.get_height_and_speed()
    runner.cancel()
    await asyncio.wait({runner})
    return round(height * 100, 1)


@pytest.fixture(autouse=True)
def no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desk_module, "RETRY_DELAY_S", 0)
    # Same 4 cm step per tick as the real FakeDesk, a thousand times faster.
    monkeypatch.setattr(FakeDesk, "TICK_S", 0.0001)
    monkeypatch.setattr(FakeDesk, "SPEED_M_S", 400.0)


@pytest.mark.parametrize("knocks", [0, 1, 2])
def test_interrupted_move_is_resumed(monkeypatch: pytest.MonkeyPatch, knocks: int) -> None:
    desk = KnockedDesk(knocks)
    monkeypatch.setattr(desk_module, "make_desk", lambda _mac, _on_lost: desk)
    assert asyncio.run(_move(desk, retries=2)) == TARGET_CM
    assert desk.moves == knocks + 1


def test_desk_is_left_where_it_stopped_after_the_last_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    desk = KnockedDesk(3)
    monkeypatch.setattr(desk_module, "make_desk", lambda _mac, _on_lost: desk)
    assert asyncio.run(_move(desk, retries=2)) < TARGET_CM - 1.0
    assert desk.moves == 3


def test_zero_retries_never_resumes(monkeypatch: pytest.MonkeyPatch) -> None:
    desk = KnockedDesk(1)
    monkeypatch.setattr(desk_module, "make_desk", lambda _mac, _on_lost: desk)
    assert asyncio.run(_move(desk, retries=0)) < TARGET_CM - 1.0
    assert desk.moves == 1
