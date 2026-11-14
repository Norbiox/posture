import logging
import sys
from collections import deque
from typing import TYPE_CHECKING, override

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

type LogLine = dict[str, str]

FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"


class _InterceptHandler(logging.Handler):
    """Routes standard logging (uvicorn, idasen, bleak, apscheduler) into loguru."""

    @override
    def emit(self, record: logging.LogRecord) -> None:
        level = logger.level(record.levelname).name
        # Walk out of the logging module so loguru reports the real caller.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup(log_path: Path, publish: Callable[[dict[str, object]], None]) -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(log_path, level="INFO", format=FILE_FORMAT, rotation="10 MB", retention=5)
    logger.add(
        lambda message: publish(
            {
                "type": "log",
                "ts": message.record["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "level": message.record["level"].name,
                "message": message.record["message"],
            }
        ),
        level="INFO",
        format="{message}",
    )
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
    # Access lines and scheduler chatter would drown the log and the live Logs tab.
    for noisy in ("uvicorn.access", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def tail(log_path: Path, lines: int) -> list[LogLine]:
    if not log_path.exists():
        return []
    with log_path.open(encoding="utf-8") as file:
        recent = deque(file, maxlen=lines)
    entries: list[LogLine] = []
    for line in recent:
        # Lines that do not split into three parts are traceback continuations.
        match line.rstrip("\n").split(" | ", 2):
            case [ts, level, message]:
                entries.append({"ts": ts, "level": level, "message": message})
            case _:
                pass
    return entries
