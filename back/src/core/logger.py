import logging
from sys import stdout

from loguru import logger

from src.core.config import AppConfig


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logger(config: AppConfig) -> None:
    logger.remove()

    format = "<white>{time:YYYY-MM-DD HH:mm:ss}</white> <level>{level}</level>: <white>{message}</white> <cyan>{extra}</cyan>"
    logger.add(stdout, level=logging.INFO, colorize=True, format=format)
    logger.level("INFO", color="<green>")

    for name in logging.root.manager.loggerDict:
        if name in ("uvicorn"):
            uvicorn_logger = logging.getLogger(name)
            uvicorn_logger.handlers.clear()
            uvicorn_logger.setLevel(config.app_loger_level.upper())
            uvicorn_logger.addHandler(InterceptHandler())
