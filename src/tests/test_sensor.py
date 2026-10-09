"""Unit tests for sensor reading, payload generation, and publishing."""

from __future__ import annotations

import datetime

import pytest

from enviroplussensorstomqtt.sensor import (
    build_payload,
    publish_payload,
    read_sensors,
    sample_median,
    send_sensor_data,
)


def test_sample_median():
    """Test sample_median helper correctly computes median."""
    calls = [10.0, 30.0, 20.0]
    result = sample_median(lambda: calls.pop(0), n=3, delay=0)
    assert result == 20.0


def test_read_sensors(fake_hardware):
    """Test read_sensors collects all expected measurement groups."""
    readings = read_sensors(fake_hardware, measurements=1, sample_delay=0)

    assert readings["temperature"] == 22.5
    assert readings["humidity"] == 45.0
    assert readings["pressure"] == 1013.2
    assert readings["noise_low"] == 10.0
    assert readings["noise_mid"] == 20.0
    assert readings["noise_high"] == 30.0
    assert readings["noise_amp"] == 5.0
    assert readings["gas_oxidising"] == 150.0
    assert readings["gas_reducing"] == 250.0
    assert readings["gas_nh3"] == 350.0
    assert readings["pm1"] == 5.0
    assert readings["pm25"] == 12.0
    assert readings["pm10"] == 25.0


def test_build_payload_preserves_keys_and_units():
    """Test build_payload contains all backward-compatible keys and unit annotations."""
    dummy_readings = {
        "temperature": 21.0,
        "humidity": 50.0,
        "pressure": 1000.0,
        "noise_low": 1.0,
        "noise_mid": 2.0,
        "noise_high": 3.0,
        "noise_amp": 4.0,
        "gas_oxidising": 10.0,
        "gas_reducing": 20.0,
        "gas_nh3": 30.0,
        "pm1": 2.0,
        "pm25": 5.0,
        "pm10": 10.0,
    }
    fixed_time = datetime.datetime(2026, 10, 9, 12, 0, 0, 123456, tzinfo=datetime.UTC)
    payload = build_payload(dummy_readings, timestamp=fixed_time)

    # Values
    assert payload["temperature"] == 21.0
    assert payload["unit_of_temperature"] == "C"
    assert payload["humidity"] == 50.0
    assert payload["unit_of_humidity"] == "%"
    assert payload["pressure"] == 1000.0
    assert payload["unit_of_pressure"] == "mbar"

    # Gas
    assert payload["gas_oxidising"] == 10.0
    assert payload["unit_of_gas_oxidising"] == "Ohms"
    assert payload["gas_reducing"] == 20.0
    assert payload["unit_of_gas_reducing"] == "Ohms"
    assert payload["gas_nh3"] == 30.0
    assert payload["unit_of_gas_nh3"] == "Ohms"

    # Noise & PM
    assert payload["noise_low"] == 1.0
    assert payload["pm1"] == 2.0
    assert payload["pm25"] == 5.0
    assert payload["pm10"] == 10.0

    # Timestamp
    assert payload["time_utc"] == "2026-10-09T12:00:00.123456"


def test_build_payload_rounding():
    """Test sensor values are sensibly rounded (P1-4)."""
    unrounded = {
        "temperature": 21.12645,
        "humidity": 45.9876,
        "pressure": 1013.256,
        "noise_low": 12.3456,
        "noise_mid": 23.4567,
        "noise_high": 34.5678,
        "noise_amp": 5.6789,
        "gas_oxidising": 150.7,
        "gas_reducing": 250.3,
        "gas_nh3": 350.6,
        "pm1": 2.8,
        "pm25": 12.4,
        "pm10": 25.1,
    }
    payload = build_payload(unrounded)
    assert payload["temperature"] == 21.13
    assert payload["humidity"] == 45.99
    assert payload["pressure"] == 1013.3
    assert payload["noise_low"] == 12.35
    assert payload["noise_mid"] == 23.46
    assert payload["noise_high"] == 34.57
    assert payload["noise_amp"] == 5.68
    assert payload["gas_oxidising"] == 151
    assert payload["gas_reducing"] == 250
    assert payload["gas_nh3"] == 351
    assert payload["pm1"] == 3
    assert payload["pm25"] == 12
    assert payload["pm10"] == 25


def test_publish_payload(fake_mqtt):
    """Test publish_payload publishes retained JSON to each configured topic."""
    payload = {"temperature": 20.0, "humidity": 40.0}
    topics = ["home/living/env", "home/all/env"]

    publish_payload(fake_mqtt, topics, payload)

    assert len(fake_mqtt.published_messages) == 2
    assert fake_mqtt.published_messages[0]["topic"] == "home/living/env"
    assert fake_mqtt.published_messages[0]["data"]["temperature"] == 20.0
    assert fake_mqtt.published_messages[0]["retain"] is True
    assert fake_mqtt.published_messages[1]["topic"] == "home/all/env"


def test_send_sensor_data_integration(fake_hardware, fake_mqtt):
    """Test send_sensor_data orchestrates connecting, reading, and publishing."""
    config = {
        "host": "broker.local",
        "port": 1883,
        "username": "user",
        "password": "pass",
        "topics": ["sensors/test"],
    }
    payload = send_sensor_data(
        config=config,
        mqtt_client=fake_mqtt,
        hardware=fake_hardware,
        measurements=1,
        sample_delay=0,
    )

    assert fake_mqtt.connected_to == ("broker.local", 1883, 60)
    assert fake_mqtt.credentials == ("user", "pass")
    assert len(fake_mqtt.published_messages) == 1
    assert fake_mqtt.published_messages[0]["topic"] == "sensors/test"
    assert payload["temperature"] == 22.5


def test_read_sensors_failing_pm_isolated(fake_hardware, caplog):
    """Test PMS5003 failure does not crash read_sensors and other readings are retained (P0-4)."""
    fake_hardware.fail_pm = True
    readings = read_sensors(fake_hardware, measurements=1, sample_delay=0)

    assert readings["pm1"] is None
    assert readings["pm25"] is None
    assert readings["pm10"] is None
    assert readings["temperature"] == 22.5
    assert readings["humidity"] == 45.0
    assert "Failed to read particulate matter" in caplog.text


def test_read_sensors_failing_gas_isolated(fake_hardware, caplog):
    """Test gas sensor failure does not crash read_sensors (P0-4)."""
    fake_hardware.fail_gas = True
    readings = read_sensors(fake_hardware, measurements=1, sample_delay=0)

    assert readings["gas_oxidising"] is None
    assert readings["gas_reducing"] is None
    assert readings["gas_nh3"] is None
    assert readings["temperature"] == 22.5
    assert "Failed to read gas concentrations" in caplog.text


def test_compensate_temperature_offset_and_cpu():
    """Test temperature offset and CPU-based compensation (P1-5)."""
    from enviroplussensorstomqtt.sensor import compensate_temperature

    assert compensate_temperature(None) is None
    # Offset subtraction: 25.0 - 2.5 = 22.5
    assert compensate_temperature(25.0, offset=2.5) == 22.5
    # CPU temperature self-heating compensation:
    # raw = 28.0, cpu = 40.0, factor = 1.2 => 28 - ((40 - 28) / 1.2) = 28 - 10 = 18.0
    assert pytest.approx(compensate_temperature(28.0, cpu_temperature=40.0, factor=1.2), 0.01) == 18.0
    # Combined with offset
    assert pytest.approx(compensate_temperature(28.0, offset=1.0, cpu_temperature=40.0, factor=1.2), 0.01) == 17.0


