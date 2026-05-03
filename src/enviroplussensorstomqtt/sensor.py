"""
Sensor module
"""
import datetime
import json
import logging
from statistics import median
from time import sleep

from bme280 import BME280
from enviroplus import gas
from enviroplus.noise import Noise
from paho.mqtt.client import Client as MqttClient
from pms5003 import PMS5003, ReadTimeoutError

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

LOGGER = logging.getLogger(__name__)


def read_pms5003(pms5003: PMS5003) -> dict:
    """
    Read values from PMS5003 particle sensor and return as dict.

    :param pms5003: An initialised PMS5003 sensor instance.
    :return: Dictionary with pm1, pm25, pm10 keys.
    """
    values = {}
    try:
        pm_values = pms5003.read()
        values["pm1"] = pm_values.pm_ug_per_m3(1)
        values["pm25"] = pm_values.pm_ug_per_m3(2.5)
        values["pm10"] = pm_values.pm_ug_per_m3(10)
    except ReadTimeoutError:
        pms5003.reset()
        pm_values = pms5003.read()
        values["pm1"] = pm_values.pm_ug_per_m3(1)
        values["pm25"] = pm_values.pm_ug_per_m3(2.5)
        values["pm10"] = pm_values.pm_ug_per_m3(10)
    return values


def send_sensor_data(
    *, config: dict, mqtt_client: MqttClient, measurements: int = 3
) -> None:
    """
    Read sensor data from Enviro+ and publish to MQTT broker.

    Takes median readings of temperature, humidity, pressure, noise,
    gas, and particulate matter, then publishes the results to each
    topic in the config as a JSON-encoded string.

    :param config: Configuration dict with host, port, username, password, topics.
    :param mqtt_client: An initialised paho MQTT client instance.
    :param measurements: Number of readings to take the median of.
    :return: None
    """
    msg = {}

    host = config["host"]
    username = config["username"]
    password = config["password"]
    port = config["port"]
    topics = config["topics"]

    bus = SMBus(1)
    device_bme280 = BME280(i2c_dev=bus)
    noise = Noise()

    # Take median of three readings for temperature
    tmp = []
    for _ in range(0, measurements):
        tmp.append(device_bme280.get_temperature())
        sleep(1)
    msg["temperature"] = median(tmp)
    msg["unit_of_temperature"] = "C"

    # Take median of three readings for humidity
    tmp = []
    for _ in range(0, measurements):
        tmp.append(device_bme280.get_humidity())
        sleep(1)
    msg["humidity"] = median(tmp)
    msg["unit_of_humidity"] = "%"

    # Take median of three readings for pressure
    tmp = []
    for _ in range(0, measurements):
        tmp.append(device_bme280.get_pressure())
        sleep(1)
    msg["pressure"] = median(tmp)
    msg["unit_of_pressure"] = "mbar"

    # Noise
    tmp_noise_low = []
    tmp_noise_mid = []
    tmp_noise_high = []
    tmp_noise_amp = []
    for _ in range(0, measurements):
        noise_low, noise_mid, noise_high, noise_amp = noise.get_noise_profile()

        tmp_noise_low.append(noise_low)
        tmp_noise_mid.append(noise_mid)
        tmp_noise_high.append(noise_high)
        tmp_noise_amp.append(noise_amp)
        sleep(1)
    msg["noise_low"] = median(tmp_noise_low)
    msg["noise_mid"] = median(tmp_noise_mid)
    msg["noise_high"] = median(tmp_noise_high)
    msg["noise_amp"] = median(tmp_noise_amp)

    # Gas readings
    tmp_gas_oxidising = []
    tmp_gas_reducing = []
    tmp_gas_nh3 = []

    for _ in range(0, measurements):
        gas_readings = gas.read_all()

        tmp_gas_oxidising.append(gas_readings.oxidising)
        tmp_gas_reducing.append(gas_readings.reducing)
        tmp_gas_nh3.append(gas_readings.nh3)
        sleep(1)

    msg["gas_oxidising"] = median(tmp_gas_oxidising)
    msg["unit_of_gas_oxidising"] = "Ohms"
    msg["gas_reducing"] = median(tmp_gas_reducing)
    msg["unit_of_gas_reducing"] = "Ohms"
    msg["gas_nh3"] = median(tmp_gas_nh3)
    msg["unit_of_gas_nh3"] = "Ohms"

    # Particulate matter
    pms5003 = PMS5003()
    tmp_pm1 = []
    tmp_pm10 = []
    tmp_pm25 = []

    for _ in range(0, measurements):
        pmm_values = read_pms5003(pms5003)

        tmp_pm1.append(pmm_values["pm1"])
        tmp_pm10.append(pmm_values["pm10"])
        tmp_pm25.append(pmm_values["pm25"])
        sleep(1)
    msg["pm1"] = median(tmp_pm1)
    msg["pm10"] = median(tmp_pm10)
    msg["pm25"] = median(tmp_pm25)

    msg["time_utc"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

    uri = f"mqtt://{username}:{password}@{host}:{port}"

    LOGGER.info(f"Connecting to {uri}")

    mqtt_client.username_pw_set(username, password=password)
    mqtt_client.connect(host, port, 60)

    LOGGER.info(f"Connected to {uri}")

    for topic in topics:
        data = json.dumps(msg).encode("utf-8")
        LOGGER.info(f"Publishing msg: {data.decode('utf-8')} to topic: {topic}")
        mqtt_client.publish(topic=topic, payload=data, retain=True)

    LOGGER.info("messages published")
