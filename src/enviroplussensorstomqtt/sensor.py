"""Sensor reading and MQTT publishing module."""

from __future__ import annotations

import datetime
import logging
from statistics import median
from time import sleep
from typing import Any, Callable

from paho.mqtt.client import Client as MqttClient

from .hardware import EnviroPlusHardware, HardwareInterface
from .mqtt import create_mqtt_client, publish_payload

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
) -> dict[str, float | None]:
    """
    Read all sensor groups from hardware with fault isolation.

    If any sensor group encounters an error, it is logged and its readings
    are recorded as None, allowing other sensors to continue normally.
    """
    readings: dict[str, float | None] = {}

    temps: list[float] = []
    hums: list[float] = []
    press: list[float] = []
    noise_low, noise_mid, noise_high, noise_amp = [], [], [], []
    gas_ox, gas_red, gas_nh3 = [], [], []
    pm1, pm25, pm10 = [], [], []

    has_temp_err = False
    has_hum_err = False
    has_press_err = False
    has_noise_err = False
    has_gas_err = False
    has_pm_err = False

    for i in range(measurements):
        if not has_temp_err:
            try:
                temps.append(hardware.read_temperature())
            except Exception as exc:
                LOGGER.warning("Failed to read temperature from sensor: %s", exc)
                has_temp_err = True

        if not has_hum_err:
            try:
                hums.append(hardware.read_humidity())
            except Exception as exc:
                LOGGER.warning("Failed to read humidity from sensor: %s", exc)
                has_hum_err = True

        if not has_press_err:
            try:
                press.append(hardware.read_pressure())
            except Exception as exc:
                LOGGER.warning("Failed to read pressure from sensor: %s", exc)
                has_press_err = True

        if not has_noise_err:
            try:
                n = hardware.read_noise()
                noise_low.append(n.low)
                noise_mid.append(n.mid)
                noise_high.append(n.high)
                noise_amp.append(n.amp)
            except Exception as exc:
                LOGGER.warning("Failed to read noise profile from sensor: %s", exc)
                has_noise_err = True

        if not has_gas_err:
            try:
                g = hardware.read_gas()
                gas_ox.append(g.oxidising)
                gas_red.append(g.reducing)
                gas_nh3.append(g.nh3)
            except Exception as exc:
                LOGGER.warning("Failed to read gas concentrations from sensor: %s", exc)
                has_gas_err = True

        if not has_pm_err:
            try:
                p = hardware.read_pm()
                pm1.append(p.pm1)
                pm25.append(p.pm25)
                pm10.append(p.pm10)
            except Exception as exc:
                LOGGER.warning("Failed to read particulate matter from PMS5003 sensor: %s", exc)
                has_pm_err = True

        if i < measurements - 1 and sample_delay > 0:
            sleep(sample_delay)

    readings["temperature"] = median(temps) if temps else None
    readings["humidity"] = median(hums) if hums else None
    readings["pressure"] = median(press) if press else None

    readings["noise_low"] = median(noise_low) if noise_low else None
    readings["noise_mid"] = median(noise_mid) if noise_mid else None
    readings["noise_high"] = median(noise_high) if noise_high else None
    readings["noise_amp"] = median(noise_amp) if noise_amp else None

    readings["gas_oxidising"] = median(gas_ox) if gas_ox else None
    readings["gas_reducing"] = median(gas_red) if gas_red else None
    readings["gas_nh3"] = median(gas_nh3) if gas_nh3 else None

    readings["pm1"] = median(pm1) if pm1 else None
    readings["pm25"] = median(pm25) if pm25 else None
    readings["pm10"] = median(pm10) if pm10 else None

    return readings


def _round_float(val: float | None, digits: int = 2) -> float | None:
    return round(val, digits) if val is not None else None


def _round_int(val: float | None) -> int | None:
    return int(round(val)) if val is not None else None


def build_payload(
    readings: dict[str, float | None],
    timestamp: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Construct MQTT JSON payload preserving all documented keys and units with sensible rounding."""
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)

    payload: dict[str, Any] = {
        "temperature": _round_float(readings.get("temperature"), 2),
        "unit_of_temperature": "C",
        "humidity": _round_float(readings.get("humidity"), 2),
        "unit_of_humidity": "%",
        "pressure": _round_float(readings.get("pressure"), 1),
        "unit_of_pressure": "mbar",
        "noise_low": _round_float(readings.get("noise_low"), 2),
        "noise_mid": _round_float(readings.get("noise_mid"), 2),
        "noise_high": _round_float(readings.get("noise_high"), 2),
        "noise_amp": _round_float(readings.get("noise_amp"), 2),
        "gas_oxidising": _round_int(readings.get("gas_oxidising")),
        "unit_of_gas_oxidising": "Ohms",
        "gas_reducing": _round_int(readings.get("gas_reducing")),
        "unit_of_gas_reducing": "Ohms",
        "gas_nh3": _round_int(readings.get("gas_nh3")),
        "unit_of_gas_nh3": "Ohms",
        "pm1": _round_int(readings.get("pm1")),
        "pm10": _round_int(readings.get("pm10")),
        "pm25": _round_int(readings.get("pm25")),
        "time_utc": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    return payload


def send_sensor_data(
    *,
    config: dict[str, Any],
    mqtt_client: MqttClient | None = None,
    hardware: HardwareInterface | None = None,
    measurements: int = 3,
    sample_delay: float = 1.0,
) -> dict[str, Any]:
    """Read sensor data from Enviro+ hardware and publish to MQTT."""
    topics = config.get("topics", [])

    if mqtt_client is not None:
        client = mqtt_client
        if hasattr(client, "is_connected") and not client.is_connected():
            host = config["host"]
            port = config.get("port", 1883)
            username = config.get("username")
            password = config.get("password")
            if username and password:
                client.username_pw_set(username, password=password)
            client.connect(host, port, 60)
    else:
        client = create_mqtt_client(config)

    hw = hardware if hardware is not None else EnviroPlusHardware()
    readings = read_sensors(hw, measurements=measurements, sample_delay=sample_delay)
    payload = build_payload(readings)

    publish_payload(client, topics, payload)
    return payload
