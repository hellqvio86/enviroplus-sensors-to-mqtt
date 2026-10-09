"""Pytest fixtures and test fakes for enviroplussensorstomqtt."""

from __future__ import annotations

import json
from typing import Any

import pytest

from enviroplussensorstomqtt.hardware import GasReadings, NoiseReadings, PMReadings


class FakeHardware:
    """Fake hardware implementation returning deterministic values."""

    def __init__(
        self,
        temperature: float = 22.5,
        humidity: float = 45.0,
        pressure: float = 1013.2,
        noise: tuple[float, float, float, float] = (10.0, 20.0, 30.0, 5.0),
        gas: tuple[float, float, float] = (150.0, 250.0, 350.0),
        pm: tuple[float, float, float] = (5.0, 12.0, 25.0),
    ) -> None:
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.noise = noise
        self.gas = gas
        self.pm = pm
        self.closed = False

    def read_temperature(self) -> float:
        return self.temperature

    def read_humidity(self) -> float:
        return self.humidity

    def read_pressure(self) -> float:
        return self.pressure

    def read_noise(self) -> NoiseReadings:
        return NoiseReadings(
            low=self.noise[0],
            mid=self.noise[1],
            high=self.noise[2],
            amp=self.noise[3],
        )

    def read_gas(self) -> GasReadings:
        return GasReadings(
            oxidising=self.gas[0],
            reducing=self.gas[1],
            nh3=self.gas[2],
        )

    def read_pm(self) -> PMReadings:
        return PMReadings(
            pm1=self.pm[0],
            pm25=self.pm[1],
            pm10=self.pm[2],
        )

    def close(self) -> None:
        self.closed = True


class FakeMQTTClient:
    """Fake MQTT client recording interactions."""

    def __init__(self) -> None:
        self.credentials: tuple[str, str | None] | None = None
        self.connected_to: tuple[str, int, int] | None = None
        self.published_messages: list[dict[str, Any]] = []

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.credentials = (username, password)

    def connect(self, host: str, port: int = 1883, keepalive: int = 60) -> int:
        self.connected_to = (host, port, keepalive)
        return 0

    def publish(self, topic: str, payload: bytes | str, retain: bool = False) -> Any:
        raw_payload = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        self.published_messages.append({
            "topic": topic,
            "raw": raw_payload,
            "data": json.loads(raw_payload),
            "retain": retain,
        })
        return self


@pytest.fixture
def fake_hardware():
    return FakeHardware()


@pytest.fixture
def fake_mqtt():
    return FakeMQTTClient()
