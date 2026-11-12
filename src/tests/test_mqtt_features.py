"""Tests for MQTT features (TLS, per-metric topics, HA discovery) in enviroplus."""

import json
from unittest.mock import patch

from enviroplussensorstomqtt.mqtt import create_mqtt_client, publish_ha_discovery, publish_payload


def test_create_mqtt_client_tls():
    config = {
        "host": "tls.broker.local",
        "port": 8883,
        "topics": ["sensors/enviro"],
        "tls": True,
        "tls_ca_certs": "/etc/ssl/ca.pem",
        "tls_certfile": "/etc/ssl/cert.pem",
        "tls_keyfile": "/etc/ssl/key.pem",
        "tls_insecure": True,
    }
    with (
        patch("paho.mqtt.client.Client.tls_set") as mock_tls_set,
        patch("paho.mqtt.client.Client.tls_insecure_set") as mock_tls_insecure,
        patch("paho.mqtt.client.Client.connect"),
    ):
        client = create_mqtt_client(config)
        assert client is not None
        mock_tls_set.assert_called_once_with(
            ca_certs="/etc/ssl/ca.pem",
            certfile="/etc/ssl/cert.pem",
            keyfile="/etc/ssl/key.pem",
        )
        mock_tls_insecure.assert_called_once_with(True)


def test_publish_ha_discovery(fake_mqtt):
    config = {
        "ha_discovery": True,
        "ha_discovery_prefix": "homeassistant",
        "device_id": "living_enviro",
    }
    publish_ha_discovery(fake_mqtt, config, ["sensors/living"])

    assert len(fake_mqtt.published_messages) >= 3
    discovery_topics = [m["topic"] for m in fake_mqtt.published_messages]
    assert "homeassistant/sensor/living_enviro/temperature/config" in discovery_topics
    assert "homeassistant/sensor/living_enviro/humidity/config" in discovery_topics
    assert "homeassistant/sensor/living_enviro/pressure/config" in discovery_topics

    temp_msg = next(m for m in fake_mqtt.published_messages if "temperature" in m["topic"])
    data = json.loads(temp_msg["raw"])
    assert data["name"] == "living_enviro Temperature"
    assert data["state_topic"] == "sensors/living"
    assert data["availability_topic"] == "sensors/living/status"


def test_publish_payload_per_metric_topics(fake_mqtt):
    payload = {
        "temperature": 21.5,
        "humidity": 45.0,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
    }
    publish_payload(
        fake_mqtt,
        ["sensors/living"],
        payload,
        per_metric_topics=True,
    )
    topics = [m["topic"] for m in fake_mqtt.published_messages]
    assert "sensors/living" in topics
    assert "sensors/living/temperature" in topics
    assert "sensors/living/humidity" in topics
    assert "sensors/living/unit_of_temperature" not in topics


def test_create_mqtt_client_auth_and_callbacks():
    from unittest.mock import MagicMock

    from enviroplussensorstomqtt.mqtt import disconnect_mqtt_client

    config = {
        "host": "auth.broker.local",
        "port": 1883,
        "username": "myuser",
        "password": "mypassword",
        "topics": ["sensors/test"],
    }
    with (
        patch("paho.mqtt.client.Client.connect"),
        patch("paho.mqtt.client.Client.loop_start"),
        patch("paho.mqtt.client.Client.username_pw_set") as mock_auth,
        patch("paho.mqtt.client.Client.will_set") as mock_will,
    ):
        client = create_mqtt_client(config)
        mock_auth.assert_called_once_with("myuser", password="mypassword")
        mock_will.assert_called_once_with("sensors/test/status", "offline", qos=1, retain=True)

        # Trigger on_connect success
        mock_publish = MagicMock()
        client.publish = mock_publish
        client.on_connect(client, None, None, 0)
        mock_publish.assert_any_call("sensors/test/status", "online", qos=1, retain=True)

        # Trigger on_connect failure
        client.on_connect(client, None, None, 5)

        # Trigger on_disconnect non-zero and zero
        client.on_disconnect(client, None, None, 1)
        client.on_disconnect(client, None, None, 0)

        # Disconnect test with error handling
        bad_client = MagicMock()
        bad_client.publish.side_effect = RuntimeError("publish error")
        bad_client.disconnect.side_effect = RuntimeError("disconnect error")
        bad_client.loop_stop.side_effect = RuntimeError("loop error")
        disconnect_mqtt_client(bad_client, topics=["sensors/test"])
