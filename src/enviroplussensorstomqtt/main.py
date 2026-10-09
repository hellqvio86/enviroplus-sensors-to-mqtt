"""Main module."""

import logging
import time
from time import sleep

import paho.mqtt.client as mqtt
from setproctitle import setproctitle

from .args import args_handler
from .log_setup import setup_logger
from .sensor import send_sensor_data

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Main function."""
    setproctitle("enviroplussensorstomqtt")

    config = args_handler()

    setup_logger(debug=config.get("debug", False), log_file=config.get("log_file"))

    LOGGER.info("Starting Enviroplus Sensors to MQTT")

    while True:
        before_work = time.time()
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        send_sensor_data(config=config, mqtt_client=mqtt_client)

        after_work = time.time()

        sleep_time = round(60 - (after_work - before_work))

        LOGGER.debug(f"Sleeping {sleep_time} seconds")

        if sleep_time > 0:
            sleep(sleep_time)


if __name__ == "__main__":
    main()
