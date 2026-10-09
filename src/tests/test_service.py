"""Tests for service lifecycle, loop exception handling, and MQTT error handling."""

from __future__ import annotations

import threading

from enviroplussensorstomqtt.main import run_service
from enviroplussensorstomqtt.mqtt import publish_payload


def test_run_service_lifecycle_and_graceful_shutdown(fake_hardware, fake_mqtt):
    """Test run_service completes cycles, closes handles, and sends offline status on exit (P0-5, P1-7)."""
    config = {
        "host": "localhost",
        "port": 1883,
        "topics": ["sensors/living"],
        "interval": 0.01,
        "measurements": 1,
    }
    stop_event = threading.Event()

    run_service(
        config=config,
        stop_event=stop_event,
        hardware=fake_hardware,
        mqtt_client=fake_mqtt,
        max_cycles=1,
    )

    # Hardware handles must be closed on exit
    assert fake_hardware.closed is True
    # MQTT client must be disconnected on exit
    assert fake_mqtt.disconnected is True
    # Sensor payload was published
    assert any(m["topic"] == "sensors/living" for m in fake_mqtt.published_messages)
    # LWT / offline message was published on shutdown
    assert any(m["topic"] == "sensors/living/status" and m["data"] == "offline" for m in fake_mqtt.published_messages)


def test_run_service_survives_cycle_exception(fake_hardware, fake_mqtt, monkeypatch, caplog):
    """Test that transient exceptions in sensor cycle do not crash the service (P0-4)."""
    config = {
        "host": "localhost",
        "port": 1883,
        "topics": ["sensors/living"],
        "interval": 0.01,
        "measurements": 1,
    }
    stop_event = threading.Event()

    calls = {"count": 0}

    from enviroplussensorstomqtt import main as main_module

    original_read = main_module.read_sensors

    def flaky_read(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Transient I2C bus lockup")
        return original_read(*args, **kwargs)

    monkeypatch.setattr(main_module, "read_sensors", flaky_read)

    run_service(
        config=config,
        stop_event=stop_event,
        hardware=fake_hardware,
        mqtt_client=fake_mqtt,
        max_cycles=2,
    )

    # Verified: loop ran 2 cycles, logged the exception, and survived to run second cycle
    assert calls["count"] == 2
    assert "Unexpected error in sensor cycle" in caplog.text
    assert fake_hardware.closed is True


def test_mqtt_publish_error_handling(fake_mqtt, caplog):
    """Test publish_payload logs errors when broker returns an error (P0-6)."""
    fake_mqtt.rc_for_publish = 1  # simulate failure
    payload = {"temp": 25.0}

    success = publish_payload(fake_mqtt, ["test/topic"], payload)

    assert success is False
    assert "Publish to test/topic failed or timed out" in caplog.text or "failed with code" in caplog.text
