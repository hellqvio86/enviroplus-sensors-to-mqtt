"""Sensor reading and MQTT publishing module."""

from __future__ import annotations

import datetime
import json
import logging
from statistics import median
from time import sleep
from typing import Any, Callable

from paho.mqtt.client import Client as MqttClient

from .hardware import EnviroPlusHardware, HardwareInterface

LOGGER = logging.getLogger(__name__)


def sample_median(func: Callable[[], float], n: int = 3, delay: float = 1.0) -> float:
    """Take n samples calling func with a delay between them, returning the median."""
    samples: list[float] = []
    for i in range(n):
        samples.append(func())
        if i < n - 1 and delay > 0:
            sleep(delay)
    return median(samples)


def read_sensors(
    hardware: HardwareInterface,
    measurements: int = 3,
    sample_delay: float = 1.0,
) -> dict[str, float]:
    """Read all sensor groups from hardware and return median values."""
    readings: dict[str, float] = {}

    # Temperature, Humidity, Pressure
    readings["temperature"] = sample_median(hardware.read_temperature, n=measurements, delay=sample_delay)
    readings["humidity"] = sample_median(hardware.read_humidity, n=measurements, delay=sample_delay)
    readings["pressure"] = sample_median(hardware.read_pressure, n=measurements, delay=sample_delay)

    # Noise profile
    noise_low: list[float] = []
    noise_mid: list[float] = []
    noise_high: list[float] = []
    noise_amp: list[float] = []
    for i in range(measurements):
        n = hardware.read_noise()
        noise_low.append(n.low)
        noise_mid.append(n.mid)
        noise_high.append(n.high)
        noise_amp.append(n.amp)
        if i < measurements - 1 and sample_delay > 0:
            sleep(sample_delay)

    readings["noise_low"] = median(noise_low)
    readings["noise_mid"] = median(noise_mid)
    readings["noise_high"] = median(noise_high)
    readings["noise_amp"] = median(noise_amp)

    # Gas
    gas_ox: list[float] = []
    gas_red: list[float] = []
    gas_nh3: list[float] = []
    for i in range(measurements):
        g = hardware.read_gas()
        gas_ox.append(g.oxidising)
        gas_red.append(g.reducing)
        gas_nh3.append(g.nh3)
        if i < measurements - 1 and sample_delay > 0:
            sleep(sample_delay)

    readings["gas_oxidising"] = median(gas_ox)
    readings["gas_reducing"] = median(gas_red)
    readings["gas_nh3"] = median(gas_nh3)

    # Particulate matter
    pm1: list[float] = []
    pm25: list[float] = []
    pm10: list[float] = []
    for i in range(measurements):
        pm = hardware.read_pm()
        pm1.append(pm.pm1)
        pm25.append(pm.pm25)
        pm10.append(pm.pm10)
        if i < measurements - 1 and sample_delay > 0:
            sleep(sample_delay)

    readings["pm1"] = median(pm1)
    readings["pm25"] = median(pm25)
    readings["pm10"] = median(pm10)

    return readings


def build_payload(
    readings: dict[str, float],
    timestamp: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Construct MQTT JSON payload preserving all documented keys and units."""
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)

    payload: dict[str, Any] = {
        "temperature": readings.get("temperature"),
        "unit_of_temperature": "C",
        "humidity": readings.get("humidity"),
        "unit_of_humidity": "%",
        "pressure": readings.get("pressure"),
        "unit_of_pressure": "mbar",
        "noise_low": readings.get("noise_low"),
        "noise_mid": readings.get("noise_mid"),
        "noise_high": readings.get("noise_high"),
        "noise_amp": readings.get("noise_amp"),
        "gas_oxidising": readings.get("gas_oxidising"),
        "unit_of_gas_oxidising": "Ohms",
        "gas_reducing": readings.get("gas_reducing"),
        "unit_of_gas_reducing": "Ohms",
        "gas_nh3": readings.get("gas_nh3"),
        "unit_of_gas_nh3": "Ohms",
        "pm1": readings.get("pm1"),
        "pm10": readings.get("pm10"),
        "pm25": readings.get("pm25"),
        "time_utc": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    return payload


def publish_payload(
    mqtt_client: MqttClient,
    topics: list[str],
    payload: dict[str, Any],
) -> None:
    """Encode payload to JSON and publish to each topic."""
    data = json.dumps(payload).encode("utf-8")
    for topic in topics:
        LOGGER.info("Publishing msg: %s to topic: %s", data.decode("utf-8"), topic)
        mqtt_client.publish(topic=topic, payload=data, retain=True)
    LOGGER.info("messages published")


def send_sensor_data(
    *,
    config: dict[str, Any],
    mqtt_client: MqttClient,
    hardware: HardwareInterface | None = None,
    measurements: int = 3,
    sample_delay: float = 1.0,
) -> dict[str, Any]:
    """Read sensor data from Enviro+ hardware and publish to MQTT."""
    host = config["host"]
    port = config["port"]
    username = config.get("username")
    password = config.get("password")
    topics = config["topics"]

    hw = hardware if hardware is not None else EnviroPlusHardware()

    readings = read_sensors(hw, measurements=measurements, sample_delay=sample_delay)
    payload = build_payload(readings)

    safe_uri = f"mqtt://{host}:{port}"
    LOGGER.info("Connecting to %s", safe_uri)

    if username and password:
        mqtt_client.username_pw_set(username, password=password)
    mqtt_client.connect(host, port, 60)
    LOGGER.info("Connected to %s", safe_uri)

    publish_payload(mqtt_client, topics, payload)
    return payload
