import logging
from logging.config import dictConfig


class LoggerClient:
    """Logger client for the SKA SRC API Compute client."""

    _nameToLevel = {
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.FATAL,
        "ERROR": logging.ERROR,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }

    __DEFAULT_LOG_LEVEL = "INFO"

    __DEFAULT_LOGGING_FORMAT = "%(asctime)s|%(levelname)s|%(name)s - %(filename)s:%(lineno)d|Thread: %(threadName)s|%(message)s"

    __DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger("uvicorn")

    @staticmethod
    def __default_log_level(log_level: str | None = None) -> str:
        """Return the default log level if not specified in log_levels."""
        if not log_level:
            return LoggerClient.__DEFAULT_LOG_LEVEL
        log_level = log_level.strip().upper()
        if log_level not in LoggerClient._nameToLevel:
            log_level = LoggerClient.__DEFAULT_LOG_LEVEL
        return log_level

    @staticmethod
    def setup_logging(properties: dict | None = None):
        """Set up logging configuration."""
        properties = properties or {}
        default_log_level = LoggerClient.__default_log_level(properties.get("default_level", LoggerClient.__DEFAULT_LOG_LEVEL))
        log_format = properties.get("log_format", LoggerClient.__DEFAULT_LOGGING_FORMAT)
        time_format = properties.get("time_format", LoggerClient.__DEFAULT_TIME_FORMAT)

        logger_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": log_format,
                    "datefmt": time_format,
                },
                "access": {
                    "format": log_format,
                    "datefmt": time_format,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "access": {
                    "class": "logging.StreamHandler",
                    "formatter": "access",
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": default_log_level,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": default_log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": default_log_level,
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["default"],
                "level": default_log_level,
            },
        }
        log_levels = properties.get("levels", {})
        for name, level in log_levels.items():
            level = LoggerClient.__default_log_level(level)
            logger_config["loggers"][name] = {
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            }
        dictConfig(logger_config)

    @staticmethod
    def get_logger(name=None):
        """Get a logger with the given name; defaults to module name."""
        if name is None:
            name = __name__
        return logging.getLogger(name)
