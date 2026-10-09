"""Hardware interface and adapter for Enviro+ sensors."""

from __future__ import annotations

import logging
from typing import NamedTuple, Protocol

LOGGER = logging.getLogger(__name__)


class GasReadings(NamedTuple):
    oxidising: float
    reducing: float
    nh3: float


class PMReadings(NamedTuple):
    pm1: float
    pm25: float
    pm10: float


class NoiseReadings(NamedTuple):
    low: float
    mid: float
    high: float
    amp: float


class HardwareInterface(Protocol):
    """Protocol defining hardware operations for Enviro+ sensors."""

    def read_temperature(self) -> float: ...
    def read_humidity(self) -> float: ...
    def read_pressure(self) -> float: ...
    def read_noise(self) -> NoiseReadings: ...
    def read_gas(self) -> GasReadings: ...
    def read_pm(self) -> PMReadings: ...
    def close(self) -> None: ...


class EnviroPlusHardware:
    """Hardware adapter for real Enviro+ hardware."""

    def __init__(self, bus_id: int = 1) -> None:
        self.bus_id = bus_id
        self._bus = None
        self._bme280 = None
        self._noise = None
        self._gas = None
        self._pms5003 = None

    def get_bme280(self):
        """Lazily initialize BME280 sensor."""
        if self._bme280 is None:
            try:
                from smbus2 import SMBus
            except ImportError:
                from smbus import SMBus  # type: ignore[import-not-found]
            from bme280 import BME280

            self._bus = SMBus(self.bus_id)
            self._bme280 = BME280(i2c_dev=self._bus)
        return self._bme280

    def get_noise(self):
        """Lazily initialize Noise sensor."""
        if self._noise is None:
            from enviroplus.noise import Noise

            self._noise = Noise()
        return self._noise

    def get_gas(self):
        """Lazily initialize Gas sensor."""
        if self._gas is None:
            from enviroplus import gas

            self._gas = gas
        return self._gas

    def get_pms5003(self):
        """Lazily initialize PMS5003 particle sensor."""
        if self._pms5003 is None:
            from pms5003 import PMS5003

            self._pms5003 = PMS5003()
        return self._pms5003

    def read_temperature(self) -> float:
        """Read temperature in Celsius."""
        return float(self.get_bme280().get_temperature())

    def read_humidity(self) -> float:
        """Read relative humidity in percent."""
        return float(self.get_bme280().get_humidity())

    def read_pressure(self) -> float:
        """Read atmospheric pressure in mbar."""
        return float(self.get_bme280().get_pressure())

    def read_noise(self) -> NoiseReadings:
        """Read noise frequency bands and amplitude."""
        low, mid, high, amp = self.get_noise().get_noise_profile()
        return NoiseReadings(low=float(low), mid=float(mid), high=float(high), amp=float(amp))

    def read_gas(self) -> GasReadings:
        """Read gas resistances in Ohms."""
        readings = self.get_gas().read_all()
        return GasReadings(
            oxidising=float(readings.oxidising),
            reducing=float(readings.reducing),
            nh3=float(readings.nh3),
        )

    def read_pm(self) -> PMReadings:
        """Read particulate matter (PM1, PM2.5, PM10)."""
        from pms5003 import ReadTimeoutError

        pms = self.get_pms5003()
        try:
            raw = pms.read()
        except ReadTimeoutError:
            pms.reset()
            raw = pms.read()
        return PMReadings(
            pm1=float(raw.pm_ug_per_m3(1)),
            pm25=float(raw.pm_ug_per_m3(2.5)),
            pm10=float(raw.pm_ug_per_m3(10)),
        )

    def close(self) -> None:
        """Release hardware handles."""
        if self._bus is not None and hasattr(self._bus, "close"):
            try:
                self._bus.close()
            except Exception as exc:
                LOGGER.debug("Error closing I2C bus: %s", exc)
            self._bus = None
        self._bme280 = None
        self._noise = None
        self._gas = None
        self._pms5003 = None
