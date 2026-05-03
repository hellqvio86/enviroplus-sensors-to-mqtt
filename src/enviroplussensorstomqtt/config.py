"""
Config
"""
import os

import yaml


def parse_config(config_file: str = "config.yaml") -> dict:
    """
    Parse configuration file in YAML format.

    Args:
        config_file (str, optional): Path to configuration file. Defaults to "config.yaml".

    Returns:
        dict: A dictionary containing the parsed configuration values.

    Raises:
        FileNotFoundError: If the specified config file is not found.

    Examples:
        >>> parse_config("config.yaml")
        {
            'host': 'mqtt.example.com',
            'port': 1883,
            'topics': ['sensors/enviroplus']
        }
    """

    config = {}

    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

    with open(config_file, "r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

        if config is None:
            config = {}

    config.setdefault("debug", False)
    config.setdefault("port", 1883)
    config.setdefault("daemon", False)
    config.setdefault(
        "log_file", "/var/log/enviroplussensorstomqtt/enviroplussensorstomqtt.log"
    )
    config.setdefault(
        "pid_file", "/run/enviroplussensorstomqtt/enviroplussensorstomqtt.pid"
    )

    return config
