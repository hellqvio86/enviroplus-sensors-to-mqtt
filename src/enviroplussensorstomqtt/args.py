"""Args handler module."""

import argparse
import os
from typing import Any

from .config import parse_config


def args_handler(argv: list[str] | None = None, *, config_file: str | None = None) -> dict[str, Any]:
    """
    Function for reading arguments and config file.

    Args:
        argv (list[str], optional): Arguments list to parse. Defaults to sys.argv[1:].
        config_file (str, optional): Default config file to use if not overridden by CLI.

    Returns:
        dict: Parsed and merged configuration dictionary.
    """
    parser = argparse.ArgumentParser(description="Publish Enviro+ sensor data to MQTT")
    parser.add_argument("--username", type=str, required=False, help="MQTT username")
    parser.add_argument("--password", type=str, required=False, help="MQTT password")
    parser.add_argument("--host", type=str, required=False, help="MQTT broker host")
    parser.add_argument("--port", type=int, required=False, help="MQTT broker port")
    parser.add_argument("--topics", type=str, required=False, help="Comma-separated MQTT topics")
    parser.add_argument("--config_file", type=str, required=False, help="Path to YAML configuration file")
    parser.add_argument("--log_file", type=str, required=False, help="Path to log file")
    parser.add_argument("--interval", type=int, required=False, help="Interval in seconds between cycles")
    parser.add_argument("--measurements", type=int, required=False, help="Number of samples to average per cycle")
    parser.add_argument("-D", "--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    if args.config_file:
        config = parse_config(config_file=args.config_file)
    elif config_file:
        config = parse_config(config_file=config_file)
    elif os.path.isfile("/etc/enviroplussensorstomqtt.yaml"):
        config = parse_config(config_file="/etc/enviroplussensorstomqtt.yaml")
    elif os.path.isfile("config.yaml"):
        config = parse_config(config_file="config.yaml")
    else:
        config = parse_config()

    if args.username is not None:
        config["username"] = args.username

    if args.password is not None:
        config["password"] = args.password

    if args.host is not None:
        config["host"] = args.host

    if args.port is not None:
        config["port"] = args.port

    if args.debug:
        config["debug"] = True

    if args.log_file is not None:
        config["log_file"] = args.log_file

    if args.interval is not None:
        config["interval"] = args.interval

    if args.measurements is not None:
        config["measurements"] = args.measurements

    if args.topics is not None:
        config["topics"] = [item.strip() for item in args.topics.split(",")]

    if config.get("debug"):
        debug_config = {k: ("***" if k == "password" and v else v) for k, v in config.items()}
        print(f"config: {debug_config}")

    return config
