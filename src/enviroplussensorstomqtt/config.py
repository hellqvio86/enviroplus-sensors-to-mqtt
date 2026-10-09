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
    client_id: str | None = None
    qos: int = 1
    retain: bool = True
    debug: bool = False
    log_file: str | None = None
    interval: float = 60.0
    measurements: int = 3
    temperature_offset: float = 0.0
    enable_ltr559: bool = True
    tls: bool = False
    tls_ca_certs: str | None = None
    tls_certfile: str | None = None
    tls_keyfile: str | None = None
    tls_insecure: bool = False
    per_metric_topics: bool = False
    ha_discovery: bool = False
    ha_discovery_prefix: str = "homeassistant"
    device_id: str = "enviroplus"

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
            qos_num = int(self.qos)
        except (ValueError, TypeError):
            raise ValueError(f"Configuration error: 'qos' must be an integer, got {self.qos!r}.") from None

        if qos_num not in (0, 1, 2):
            raise ValueError(f"Configuration error: 'qos' must be 0, 1, or 2, got {qos_num}.")
        self.qos = qos_num

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
            "client_id": self.client_id,
            "qos": self.qos,
            "retain": self.retain,
            "debug": self.debug,
            "log_file": self.log_file,
            "interval": self.interval,
            "measurements": self.measurements,
            "temperature_offset": self.temperature_offset,
            "enable_ltr559": self.enable_ltr559,
            "tls": self.tls,
            "tls_ca_certs": self.tls_ca_certs,
            "tls_certfile": self.tls_certfile,
            "tls_keyfile": self.tls_keyfile,
            "tls_insecure": self.tls_insecure,
            "per_metric_topics": self.per_metric_topics,
            "ha_discovery": self.ha_discovery,
            "ha_discovery_prefix": self.ha_discovery_prefix,
            "device_id": self.device_id,
        }


def get_default_config() -> dict[str, Any]:
    """Return default configuration options."""
    return {
        "debug": False,
        "port": 1883,
        "client_id": None,
        "qos": 1,
        "retain": True,
        "log_file": None,
        "interval": 60.0,
        "measurements": 3,
        "temperature_offset": 0.0,
        "enable_ltr559": True,
        "tls": False,
        "tls_ca_certs": None,
        "tls_certfile": None,
        "tls_keyfile": None,
        "tls_insecure": False,
        "per_metric_topics": False,
        "ha_discovery": False,
        "ha_discovery_prefix": "homeassistant",
        "device_id": "enviroplus",
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

    for k, v in get_default_config().items():
        config.setdefault(k, v)

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
        client_id=config.get("client_id"),
        qos=int(config.get("qos", 1)),
        retain=bool(config.get("retain", True)),
        debug=bool(config.get("debug", False)),
        log_file=config.get("log_file"),
        interval=config.get("interval", 60.0),
        measurements=config.get("measurements", 3),
        temperature_offset=config.get("temperature_offset", 0.0),
        enable_ltr559=bool(config.get("enable_ltr559", True)),
        tls=bool(config.get("tls", False)),
        tls_ca_certs=config.get("tls_ca_certs"),
        tls_certfile=config.get("tls_certfile"),
        tls_keyfile=config.get("tls_keyfile"),
        tls_insecure=bool(config.get("tls_insecure", False)),
        per_metric_topics=bool(config.get("per_metric_topics", False)),
        ha_discovery=bool(config.get("ha_discovery", False)),
        ha_discovery_prefix=str(config.get("ha_discovery_prefix", "homeassistant")),
        device_id=str(config.get("device_id", "enviroplus")),
    )
