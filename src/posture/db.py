import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import TYPE_CHECKING

import holidays as public_holidays

from posture.domain.stats import HeightEvent
from posture.domain.work_time import WorkHours

if TYPE_CHECKING:
    from collections.abc import Generator

DEFAULTS = {
    "work_start": "07:00",
    "work_end": "17:00",
    "workdays": [0, 1, 2, 3, 4],
    "threshold_cm": 90.0,
}

# Heights measured on the owner's Desk.
DEFAULT_PRESETS = {
    "top": 119.5,
    "walk": 115.4,
    "upper-stand": 114.0,
    "stand": 107.2,
    "corechair": 70.0,
    "sit": 66.6,
    "bottom": 62.0,
}


@dataclass(frozen=True)
class Preset:
    id: int
    name: str
    height_cm: float


@dataclass(frozen=True)
class AutomationRow:
    id: int
    kind: str
    enabled: bool
    preset_id: int
    time_of_day: str | None
    stance: str | None
    minutes: int | None


@dataclass(frozen=True)
class Holiday:
    date: date
    name: str
    automatic: bool


@dataclass(frozen=True)
class Settings:
    work_start: str
    work_end: str
    workdays: list[int]
    threshold_cm: float

    def work_hours(self) -> WorkHours:
        return WorkHours(time.fromisoformat(self.work_start), time.fromisoformat(self.work_end))


def _iso(ts: datetime) -> str:
    # One fixed format keeps lexicographic order equal to time order.
    return ts.astimezone(UTC).isoformat(timespec="milliseconds")


def _event(row: tuple[str, float]) -> HeightEvent:
    return HeightEvent(datetime.fromisoformat(row[0]), row[1])


class Db:
    """Blocking sqlite3 access; callers run it through asyncio.to_thread."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(Path(__file__).with_name("schema.sql").read_text())
            # Seed once per database, so a Preset the owner deletes stays deleted.
            if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT OR IGNORE INTO presets (name, height_cm) VALUES (?, ?)",
                    DEFAULT_PRESETS.items(),
                )
                conn.execute("PRAGMA user_version = 1")

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection]:
        # A connection per call is cheap and keeps every thread on its own connection.
        with closing(sqlite3.connect(self._path)) as conn, conn:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn

    # Height events

    def add_event(self, ts: datetime, height_cm: float) -> None:
        with self._conn() as conn:
            conn.execute("INSERT INTO height_events VALUES (?, ?)", (_iso(ts), height_cm))

    def events_between(self, start: datetime, end: datetime) -> list[HeightEvent]:
        """Events in [start, end) plus the last one before start, which sets the initial state."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT ts, height_cm FROM (
                  SELECT ts, height_cm FROM height_events WHERE ts < :start
                  ORDER BY ts DESC LIMIT 1
                )
                UNION ALL
                SELECT ts, height_cm FROM height_events WHERE ts >= :start AND ts < :end
                ORDER BY ts
                """,
                {"start": _iso(start), "end": _iso(end)},
            ).fetchall()
        return [_event(row) for row in rows]

    def recent_events(self, limit: int) -> list[HeightEvent]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT ts, height_cm FROM height_events ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_event(row) for row in reversed(rows)]

    # Presets

    def list_presets(self) -> list[Preset]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, name, height_cm FROM presets ORDER BY height_cm")
            return [Preset(*row) for row in rows]

    def get_preset(self, name: str) -> Preset | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, name, height_cm FROM presets WHERE name = ?", (name,)
            ).fetchone()
        return Preset(*row) if row else None

    def preset_height(self, preset_id: int) -> float | None:
        with self._conn() as conn:
            row = conn.execute("SELECT height_cm FROM presets WHERE id = ?", (preset_id,))
            found = row.fetchone()
        return float(found[0]) if found else None

    def add_preset(self, name: str, height_cm: float) -> Preset:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO presets (name, height_cm) VALUES (?, ?)", (name, height_cm)
            )
        return Preset(cur.lastrowid or 0, name, height_cm)

    def update_preset(self, preset_id: int, name: str, height_cm: float) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE presets SET name = ?, height_cm = ? WHERE id = ?",
                (name, height_cm, preset_id),
            )
        return cur.rowcount > 0

    def delete_preset(self, preset_id: int) -> bool:
        with self._conn() as conn:
            return conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,)).rowcount > 0

    # Automations

    def list_automations(self) -> list[AutomationRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, kind, enabled, preset_id, time_of_day, stance, minutes"
                " FROM automations ORDER BY id"
            )
            return [AutomationRow(*row[:2], bool(row[2]), *row[3:]) for row in rows]

    def add_automation(self, a: AutomationRow) -> AutomationRow:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO automations (kind, enabled, preset_id, time_of_day, stance, minutes)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (a.kind, a.enabled, a.preset_id, a.time_of_day, a.stance, a.minutes),
            )
        return replace(a, id=cur.lastrowid or 0)

    def update_automation(self, a: AutomationRow) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE automations SET kind = ?, enabled = ?, preset_id = ?, time_of_day = ?,"
                " stance = ?, minutes = ? WHERE id = ?",
                (a.kind, a.enabled, a.preset_id, a.time_of_day, a.stance, a.minutes, a.id),
            )
        return cur.rowcount > 0

    def delete_automation(self, automation_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
        return cur.rowcount > 0

    # Holidays: manual dates from the database merged with Polish public holidays

    def list_holidays(self, years: list[int]) -> list[Holiday]:
        with self._conn() as conn:
            manual = conn.execute("SELECT date, name FROM holidays").fetchall()
        result = [Holiday(date.fromisoformat(d), name, automatic=False) for d, name in manual]
        automatic = public_holidays.country_holidays("PL", years=years, language="en_US")
        result += [Holiday(d, name, automatic=True) for d, name in automatic.items()]
        return sorted(result, key=lambda h: h.date)

    def add_holiday(self, day: date, name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO holidays VALUES (?, ?) ON CONFLICT (date) DO UPDATE SET name = ?",
                (day.isoformat(), name, name),
            )

    def delete_holiday(self, day: date) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM holidays WHERE date = ?", (day.isoformat(),))
        return cur.rowcount > 0

    # Settings and Pause

    def get_settings(self) -> Settings:
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        stored = {key: json.loads(value) for key, value in rows}
        return Settings(**{key: stored.get(key, default) for key, default in DEFAULTS.items()})

    def put_settings(self, settings: Settings) -> None:
        with self._conn() as conn:
            for key, value in asdict(settings).items():
                self._put(conn, key, value)

    def get_pause_until(self) -> datetime | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'pause_until'").fetchone()
        return datetime.fromisoformat(json.loads(row[0])) if row else None

    def set_pause_until(self, until: datetime | None) -> None:
        with self._conn() as conn:
            if until is None:
                conn.execute("DELETE FROM settings WHERE key = 'pause_until'")
            else:
                self._put(conn, "pause_until", _iso(until))

    def get_last_tick(self) -> datetime | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'last_tick'").fetchone()
        return datetime.fromisoformat(json.loads(row[0])) if row else None

    def set_last_tick(self, ts: datetime) -> None:
        with self._conn() as conn:
            self._put(conn, "last_tick", _iso(ts))

    @staticmethod
    def _put(conn: sqlite3.Connection, key: str, value: object) -> None:
        conn.execute(
            "INSERT INTO settings VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = ?",
            (key, json.dumps(value), json.dumps(value)),
        )
