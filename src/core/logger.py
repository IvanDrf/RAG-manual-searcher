import structlog

from src.core.config import AppConfig


def configure_logger(config: AppConfig) -> None:
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(config.app_loger_level))
