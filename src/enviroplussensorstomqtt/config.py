"""Config module."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class AppConfig:
    """Validated application configuration."""

    host: str
    topics: list[str]
    port: int = 1883
    username: str | None = None
    password: str | None = None
    debug: bool = False
    log_file: str | None = None
    interval: float = 60.0
    measurements: int = 3
    temperature_offset: float = 0.0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate configuration values and raise ValueError on error."""
        if not self.host or not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("Configuration error: 'host' must be a non-empty string.")

        if not self.topics:
            raise ValueError("Configuration error: 'topics' must be a non-empty list of topic strings.")

        if isinstance(self.topics, str):
            raise ValueError("Configuration error: 'topics' must be a list of strings, not a single string.")

        if not all(isinstance(t, str) and t.strip() for t in self.topics):
            raise ValueError("Configuration error: all items in 'topics' must be non-empty strings.")

        try:
            port_num = int(self.port)
        except (ValueError, TypeError):
            raise ValueError(f"Configuration error: 'port' must be an integer, got {self.port!r}.") from None

        if not (1 <= port_num <= 65535):
            raise ValueError(f"Configuration error: 'port' must be between 1 and 65535, got {port_num}.")
        self.port = port_num

        try:
            self.interval = float(self.interval)
            if self.interval <= 0:
                raise ValueError
        except (ValueError, TypeError):
            msg = f"Configuration error: 'interval' must be a positive number, got {self.interval!r}."
            raise ValueError(msg) from None

        try:
            self.measurements = int(self.measurements)
            if self.measurements <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(
                f"Configuration error: 'measurements' must be a positive integer, got {self.measurements!r}."
            ) from None

        try:
            self.temperature_offset = float(self.temperature_offset)
        except (ValueError, TypeError):
            raise ValueError(
                f"Configuration error: 'temperature_offset' must be a float, got {self.temperature_offset!r}."
            ) from None

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary format for backward compatibility."""
        return {
            "host": self.host,
            "topics": self.topics,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "debug": self.debug,
            "log_file": self.log_file,
            "interval": self.interval,
            "measurements": self.measurements,
            "temperature_offset": self.temperature_offset,
        }


def get_default_config() -> dict[str, Any]:
    """Return default configuration options."""
    return {
        "debug": False,
        "port": 1883,
        "log_file": None,
        "interval": 60.0,
        "measurements": 3,
        "temperature_offset": 0.0,
    }


def parse_config(config_file: str | None = None) -> dict[str, Any]:
    """
    Parse configuration file in YAML format.

    Args:
        config_file (str, optional): Path to configuration file. If None, returns default config.

    Returns:
        dict: A dictionary containing parsed configuration values merged with defaults.

    Raises:
        FileNotFoundError: If the specified config file is not found.
    """
    config = get_default_config()

    if config_file is not None:
        if not os.path.isfile(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

        with open(config_file, encoding="utf-8") as stream:
            loaded = yaml.safe_load(stream)
            if loaded and isinstance(loaded, dict):
                config.update(loaded)

    config.setdefault("debug", False)
    config.setdefault("port", 1883)
    config.setdefault("log_file", None)
    config.setdefault("interval", 60.0)
    config.setdefault("measurements", 3)
    config.setdefault("temperature_offset", 0.0)

    # Normalize topics if given as comma-separated string in YAML
    if isinstance(config.get("topics"), str):
        config["topics"] = [t.strip() for t in config["topics"].split(",") if t.strip()]

    return config


def validate_config(config: dict[str, Any]) -> AppConfig:
    """Validate a raw configuration dict and return an AppConfig instance."""
    # Normalize topics if still string
    topics = config.get("topics")
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split(",") if t.strip()]

    return AppConfig(
        host=config.get("host", ""),
        topics=topics if isinstance(topics, list) else [],
        port=config.get("port", 1883),
        username=config.get("username"),
        password=config.get("password"),
        debug=bool(config.get("debug", False)),
        log_file=config.get("log_file"),
        interval=config.get("interval", 60.0),
        measurements=config.get("measurements", 3),
        temperature_offset=config.get("temperature_offset", 0.0),
    )
