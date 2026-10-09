"""Args handler module."""

from __future__ import annotations

import argparse
import os
from typing import Any

from .config import parse_config, validate_config


def args_handler(
    argv: list[str] | None = None,
    *,
    config_file: str | None = None,
    validate: bool = False,
) -> dict[str, Any]:
    """
    Function for reading arguments and config file.

    Args:
        argv (list[str], optional): Arguments list to parse. Defaults to sys.argv[1:].
        config_file (str, optional): Default config file to use if not overridden by CLI.
        validate (bool, optional): Whether to validate config immediately against AppConfig schema.

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
    parser.add_argument("--interval", type=float, required=False, help="Interval in seconds between cycles")
    parser.add_argument("--measurements", type=int, required=False, help="Number of samples to average per cycle")
    parser.add_argument(
        "--temperature_offset",
        type=float,
        required=False,
        help="Temperature offset in °C to subtract/compensate for self-heating",
    )
    parser.add_argument("--client_id", type=str, required=False, help="MQTT client ID")
    parser.add_argument("--tls", action=argparse.BooleanOptionalAction, default=None, help="Enable TLS")
    parser.add_argument("--tls_ca_certs", type=str, required=False, help="Path to CA certificate")
    parser.add_argument("--tls_certfile", type=str, required=False, help="Path to client certificate")
    parser.add_argument("--tls_keyfile", type=str, required=False, help="Path to client key")
    parser.add_argument("--tls_insecure", action=argparse.BooleanOptionalAction, default=None, help="Skip TLS verify")
    parser.add_argument(
        "--per_metric_topics", action=argparse.BooleanOptionalAction, default=None, help="Publish per-metric"
    )
    parser.add_argument(
        "--ha_discovery", action=argparse.BooleanOptionalAction, default=None, help="Enable HA discovery"
    )
    parser.add_argument("--ha_discovery_prefix", type=str, required=False, help="HA discovery prefix")
    parser.add_argument("--device_id", type=str, required=False, help="Device ID for HA discovery")
    parser.add_argument(
        "--disable-ltr559",
        action="store_true",
        help="Disable LTR559 light and proximity sensor",
    )
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

    if args.disable_ltr559:
        config["enable_ltr559"] = False

    if args.log_file is not None:
        config["log_file"] = args.log_file

    if args.interval is not None:
        config["interval"] = args.interval

    if args.measurements is not None:
        config["measurements"] = args.measurements

    if args.temperature_offset is not None:
        config["temperature_offset"] = args.temperature_offset

    if args.topics is not None:
        config["topics"] = [item.strip() for item in args.topics.split(",") if item.strip()]

    if args.client_id is not None:
        config["client_id"] = args.client_id

    if args.tls is not None:
        config["tls"] = args.tls

    if args.tls_ca_certs is not None:
        config["tls_ca_certs"] = args.tls_ca_certs

    if args.tls_certfile is not None:
        config["tls_certfile"] = args.tls_certfile

    if args.tls_keyfile is not None:
        config["tls_keyfile"] = args.tls_keyfile

    if args.tls_insecure is not None:
        config["tls_insecure"] = args.tls_insecure

    if args.per_metric_topics is not None:
        config["per_metric_topics"] = args.per_metric_topics

    if args.ha_discovery is not None:
        config["ha_discovery"] = args.ha_discovery

    if args.ha_discovery_prefix is not None:
        config["ha_discovery_prefix"] = args.ha_discovery_prefix

    if args.device_id is not None:
        config["device_id"] = args.device_id

    # Environment variable fallbacks for secrets and broker config
    if not config.get("password") and "MQTT_PASSWORD" in os.environ:
        config["password"] = os.environ["MQTT_PASSWORD"]

    if not config.get("username") and "MQTT_USERNAME" in os.environ:
        config["username"] = os.environ["MQTT_USERNAME"]

    if not config.get("host") and "MQTT_HOST" in os.environ:
        config["host"] = os.environ["MQTT_HOST"]

    # Validate configuration if requested
    if validate:
        app_config = validate_config(config)
        config = app_config.to_dict()

    if config.get("debug"):
        debug_config = {k: ("***" if k == "password" and v else v) for k, v in config.items()}
        print(f"config: {debug_config}")

    return config
