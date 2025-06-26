"""Utility functions for logging and configuration."""

import logging
from logging.handlers import RotatingFileHandler
import os
import yaml

_LOGGER = None


def _setup_logger(log_file: str = "bot.log") -> logging.Logger:
    """Create and configure a rotating file logger."""
    logger = logging.getLogger("bot")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def get_logger() -> logging.Logger:
    """Return a shared logger instance."""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = _setup_logger()
    return _LOGGER


def log(message: str, level: str = "info") -> None:
    """Log *message* with the specified severity *level*."""
    logger = get_logger()
    getattr(logger, level.lower())(message)


def load_config(path: str = "config.yaml") -> dict:
    """Load YAML configuration and override credentials from environment."""
    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    config["email"] = os.getenv("BOT_EMAIL", config.get("email"))
    config["password"] = os.getenv("BOT_PASSWORD", config.get("password"))
    return config


def entry_strength(confluence_count: int) -> str:
    """Classify entry strength based on the number of confluences."""
    if confluence_count >= 7:
        return "forte"
    if confluence_count >= 5:
        return "media"
    if confluence_count >= 3:
        return "fraca"
    return "nenhuma"