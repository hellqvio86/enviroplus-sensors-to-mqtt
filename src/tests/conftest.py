"""Pytest fixtures and test fakes for enviroplussensorstomqtt."""

from __future__ import annotations

import json
from typing import Any

import pytest

from enviroplussensorstomqtt.hardware import GasReadings, LightReadings, NoiseReadings, PMReadings


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
        self.fail_pm = False
        self.fail_gas = False

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
        if self.fail_gas:
            raise RuntimeError("I2C read failure on MICS6814 gas sensor")
        return GasReadings(
            oxidising=self.gas[0],
            reducing=self.gas[1],
            nh3=self.gas[2],
        )

    def read_pm(self) -> PMReadings:
        if self.fail_pm:
            raise TimeoutError("PMS5003 read timeout")
        return PMReadings(
            pm1=self.pm[0],
            pm25=self.pm[1],
            pm10=self.pm[2],
        )

    def read_light(self) -> LightReadings:
        if getattr(self, "fail_light", False):
            raise RuntimeError("LTR559 read error")
        return LightReadings(lux=120.5, proximity=42)

    def close(self) -> None:
        self.closed = True


class FakeMessageInfo:
    """Fake MQTTMessageInfo returned by publish()."""

    def __init__(self, rc: int = 0) -> None:
        self.rc = rc

    def wait_for_publish(self, timeout: float | None = None) -> None:
        if self.rc != 0:
            raise RuntimeError(f"Publish failed with code {self.rc}")


class FakeMQTTClient:
    """Fake MQTT client recording interactions."""

    def __init__(self) -> None:
        self.credentials: tuple[str, str | None] | None = None
        self.connected_to: tuple[str, int, int] | None = None
        self.published_messages: list[dict[str, Any]] = []
        self.loop_started: bool = False
        self.loop_stopped: bool = False
        self.disconnected: bool = False
        self.will: tuple[str, str, int, bool] | None = None
        self.rc_for_publish: int = 0

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.credentials = (username, password)

    def connect(self, host: str, port: int = 1883, keepalive: int = 60) -> int:
        self.connected_to = (host, port, keepalive)
        return 0

    def will_set(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        self.will = (topic, payload, qos, retain)

    def loop_start(self) -> None:
        self.loop_started = True

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def is_connected(self) -> bool:
        return self.connected_to is not None and not self.disconnected

    def disconnect(self) -> None:
        self.disconnected = True

    def publish(self, topic: str, payload: bytes | str, qos: int = 0, retain: bool = False) -> FakeMessageInfo:
        raw_payload = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        try:
            data = json.loads(raw_payload)
        except Exception:
            data = raw_payload

        self.published_messages.append({
            "topic": topic,
            "raw": raw_payload,
            "data": data,
            "qos": qos,
            "retain": retain,
        })
        return FakeMessageInfo(rc=self.rc_for_publish)


@pytest.fixture
def fake_hardware():
    return FakeHardware()


@pytest.fixture
def fake_mqtt():
    return FakeMQTTClient()
