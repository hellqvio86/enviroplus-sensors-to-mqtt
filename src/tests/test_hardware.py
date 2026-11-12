"""Tests for EnviroPlusHardware adapter methods and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from enviroplussensorstomqtt.hardware import (
    EnviroPlusHardware,
    GasReadings,
    LightReadings,
    NoiseReadings,
    PMReadings,
)


def test_hardware_init():
    hw = EnviroPlusHardware(bus_id=2)
    assert hw.bus_id == 2
    assert hw._bus is None
    assert hw._bme280 is None


def test_get_bme280():
    hw = EnviroPlusHardware(bus_id=1)
    mock_smbus_cls = MagicMock()
    mock_bme_cls = MagicMock()

    with patch.dict(
        "sys.modules",
        {"smbus2": MagicMock(SMBus=mock_smbus_cls), "bme280": MagicMock(BME280=mock_bme_cls)},
    ):
        bme = hw.get_bme280()
        assert bme is not None
        mock_smbus_cls.assert_called_once_with(1)
        mock_bme_cls.assert_called_once_with(i2c_dev=mock_smbus_cls.return_value)

        # Caching check
        assert hw.get_bme280() is bme


def test_get_noise_gas_pms():
    hw = EnviroPlusHardware()
    mock_noise_cls = MagicMock()
    mock_gas_module = MagicMock()
    mock_pms_cls = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "enviroplus.noise": MagicMock(Noise=mock_noise_cls),
            "enviroplus": MagicMock(gas=mock_gas_module),
            "pms5003": MagicMock(PMS5003=mock_pms_cls),
        },
    ):
        noise = hw.get_noise()
        assert noise is not None
        assert hw.get_noise() is noise

        gas = hw.get_gas()
        assert gas is mock_gas_module
        assert hw.get_gas() is gas

        pms = hw.get_pms5003()
        assert pms is not None
        assert hw.get_pms5003() is pms


def test_get_ltr559():
    hw = EnviroPlusHardware()
    mock_ltr_cls = MagicMock()

    with patch.dict("sys.modules", {"ltr559": MagicMock(LTR559=mock_ltr_cls)}):
        ltr = hw.get_ltr559()
        assert ltr is not None
        assert hw.get_ltr559() is ltr


def test_get_ltr559_not_available():
    hw = EnviroPlusHardware()
    with patch.dict("sys.modules", {"ltr559": None}):
        ltr = hw.get_ltr559()
        assert ltr is None


def test_read_temperature_humidity_pressure():
    hw = EnviroPlusHardware()
    mock_bme = MagicMock()
    mock_bme.get_temperature.return_value = 23.45
    mock_bme.get_humidity.return_value = 52.1
    mock_bme.get_pressure.return_value = 1012.8
    hw._bme280 = mock_bme

    assert hw.read_temperature() == 23.45
    assert hw.read_humidity() == 52.1
    assert hw.read_pressure() == 1012.8


def test_read_noise():
    hw = EnviroPlusHardware()
    mock_noise = MagicMock()
    mock_noise.get_noise_profile.return_value = (0.1, 0.2, 0.3, 0.05)
    hw._noise = mock_noise

    readings = hw.read_noise()
    assert isinstance(readings, NoiseReadings)
    assert readings.low == 0.1
    assert readings.mid == 0.2
    assert readings.high == 0.3
    assert readings.amp == 0.05


def test_read_gas():
    hw = EnviroPlusHardware()
    mock_gas = MagicMock()
    mock_readings = MagicMock(oxidising=150000.0, reducing=250000.0, nh3=350000.0)
    mock_gas.read_all.return_value = mock_readings
    hw._gas = mock_gas

    readings = hw.read_gas()
    assert isinstance(readings, GasReadings)
    assert readings.oxidising == 150000.0
    assert readings.reducing == 250000.0
    assert readings.nh3 == 350000.0


def test_read_pm():
    hw = EnviroPlusHardware()
    mock_pms = MagicMock()
    mock_raw = MagicMock()
    mock_raw.pm_ug_per_m3.side_effect = lambda size: 1.0 if size == 1 else (2.5 if size == 2.5 else 10.0)
    mock_pms.read.return_value = mock_raw
    hw._pms5003 = mock_pms

    readings = hw.read_pm()
    assert isinstance(readings, PMReadings)
    assert readings.pm1 == 1.0
    assert readings.pm25 == 2.5
    assert readings.pm10 == 10.0


def test_read_pm_timeout_retry():
    hw = EnviroPlusHardware()
    mock_pms = MagicMock()
    mock_raw = MagicMock()
    mock_raw.pm_ug_per_m3.return_value = 5.0

    class FakeReadTimeoutError(Exception):
        pass

    mock_pms_mod = MagicMock()
    mock_pms_mod.ReadTimeoutError = FakeReadTimeoutError
    mock_pms.read.side_effect = [FakeReadTimeoutError("timeout"), mock_raw]
    hw._pms5003 = mock_pms

    with patch.dict("sys.modules", {"pms5003": mock_pms_mod}):
        readings = hw.read_pm()
        assert readings.pm1 == 5.0
        mock_pms.reset.assert_called_once()


def test_read_light_success():
    hw = EnviroPlusHardware()
    mock_ltr = MagicMock()
    mock_ltr.get_lux.return_value = 142.5
    mock_ltr.get_proximity.return_value = 35
    hw._ltr559 = mock_ltr

    readings = hw.read_light()
    assert isinstance(readings, LightReadings)
    assert readings.lux == 142.5
    assert readings.proximity == 35
    mock_ltr.update_sensor.assert_called_once()


def test_read_light_uninitialized_raises():
    hw = EnviroPlusHardware()
    hw.get_ltr559 = MagicMock(return_value=None)

    with pytest.raises(RuntimeError, match="LTR559 sensor not initialized"):
        hw.read_light()


def test_hardware_close():
    hw = EnviroPlusHardware()
    mock_bus = MagicMock()
    hw._bus = mock_bus
    hw._bme280 = MagicMock()
    hw._noise = MagicMock()
    hw._gas = MagicMock()
    hw._pms5003 = MagicMock()
    hw._ltr559 = MagicMock()

    hw.close()
    mock_bus.close.assert_called_once()
    assert hw._bus is None
    assert hw._bme280 is None
    assert hw._noise is None
    assert hw._gas is None
    assert hw._pms5003 is None
    assert hw._ltr559 is None


def test_hardware_close_bus_error_handled():
    hw = EnviroPlusHardware()
    mock_bus = MagicMock()
    mock_bus.close.side_effect = OSError("Bus error")
    hw._bus = mock_bus

    # Should not raise exception
    hw.close()
    assert hw._bus is None
