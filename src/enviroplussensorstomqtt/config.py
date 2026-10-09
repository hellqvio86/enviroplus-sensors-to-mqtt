"""Config module."""

import os
from typing import Any

import yaml


def get_default_config() -> dict[str, Any]:
    """Return default configuration options."""
    return {
        "debug": False,
        "port": 1883,
        "log_file": None,
        "interval": 60,
        "measurements": 3,
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
    config.setdefault("interval", 60)
    config.setdefault("measurements", 3)

    return config
