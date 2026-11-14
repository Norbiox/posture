import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Config:
    desk_mac: str
    tz: ZoneInfo
    retries: int
    db_path: Path
    log_path: Path
    static_dir: Path
    host: str
    port: int

    @classmethod
    def from_env(cls) -> Config:
        env = os.environ
        return cls(
            desk_mac=env["POSTURE_DESK_MAC"],
            tz=ZoneInfo(env.get("POSTURE_TZ", "Europe/Warsaw")),
            retries=int(env.get("POSTURE_RETRIES", "5")),
            db_path=Path(env.get("POSTURE_DB", "/var/lib/posture/posture.db")),
            log_path=Path(env.get("POSTURE_LOG", "/var/log/posture/posture.log")),
            static_dir=Path(env.get("POSTURE_STATIC_DIR", "frontend/dist")),
            host=env.get("POSTURE_HOST", "0.0.0.0"),  # noqa: S104 - LAN service by design
            port=int(env.get("POSTURE_PORT", "8000")),
        )
