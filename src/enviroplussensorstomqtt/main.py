"""Main module for running the Enviroplus Sensors to MQTT service."""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt
from setproctitle import setproctitle

from .args import args_handler
from .hardware import EnviroPlusHardware, HardwareInterface
from .log_setup import setup_logger
from .mqtt import create_mqtt_client, disconnect_mqtt_client, publish_payload
from .sensor import build_payload, read_sensors

LOGGER = logging.getLogger(__name__)


def run_service(
    config: dict[str, Any],
    *,
    stop_event: threading.Event | None = None,
    hardware: HardwareInterface | None = None,
    mqtt_client: mqtt.Client | None = None,
    max_cycles: int | None = None,
) -> None:
    """
    Run the sensor-to-MQTT service loop until stop_event is set or max_cycles reached.

    Args:
        config: Configuration dictionary.
        stop_event: Event to signal graceful shutdown.
        hardware: Sensor hardware interface instance.
        mqtt_client: MQTT client instance.
        max_cycles: Optional maximum number of cycles to run (useful for testing).
    """
    if stop_event is None:
        stop_event = threading.Event()

        def _handle_signal(signum: int, _frame: Any) -> None:
            LOGGER.info("Received signal %s; initiating graceful shutdown...", signum)
            stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

    topics = config.get("topics", [])
    interval = float(config.get("interval", 60))
    measurements = int(config.get("measurements", 3))

    hw = hardware if hardware is not None else EnviroPlusHardware()
    client = mqtt_client if mqtt_client is not None else create_mqtt_client(config)

    LOGGER.info("Starting Enviroplus Sensors to MQTT (interval: %ss, measurements: %s)", interval, measurements)

    cycle_count = 0
    try:
        while not stop_event.is_set():
            cycle_start = time.monotonic()
            cycle_count += 1

            try:
                offset = float(config.get("temperature_offset", 0.0))
                readings = read_sensors(hw, measurements=measurements, temperature_offset=offset)
                payload = build_payload(readings)
                publish_payload(client, topics, payload)
            except Exception as exc:
                LOGGER.exception("Unexpected error in sensor cycle: %s", exc)

            if max_cycles is not None and cycle_count >= max_cycles:
                break

            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0.5, interval - elapsed)

            if elapsed > interval:
                LOGGER.warning("Sensor cycle took %.2fs, exceeding configured interval of %ss", elapsed, interval)

            LOGGER.debug("Sleeping for %.2fs until next cycle", sleep_time)
            stop_event.wait(timeout=sleep_time)

    finally:
        LOGGER.info("Shutting down service...")
        try:
            disconnect_mqtt_client(client, topics)
        except Exception as exc:
            LOGGER.debug("Error disconnecting MQTT: %s", exc)

        try:
            hw.close()
        except Exception as exc:
            LOGGER.debug("Error closing hardware handles: %s", exc)
        LOGGER.info("Service shutdown completed.")


def main() -> None:
    """CLI entrypoint."""
    setproctitle("enviroplussensorstomqtt")
    try:
        config = args_handler(validate=True)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from None
    setup_logger(debug=config.get("debug", False), log_file=config.get("log_file"))
    run_service(config)


if __name__ == "__main__":
    main()
