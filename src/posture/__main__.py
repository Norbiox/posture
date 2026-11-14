import uvicorn

from posture.api import create_app
from posture.config import Config


def main() -> None:
    config = Config.from_env()
    # log_config=None leaves uvicorn's loggers to the loguru interception set up at startup.
    uvicorn.run(create_app(config), host=config.host, port=config.port, log_config=None)


if __name__ == "__main__":
    main()
