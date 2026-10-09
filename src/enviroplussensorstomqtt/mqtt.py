"""MQTT client setup, connection lifecycle, and publishing."""

from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger(__name__)


ENVIROPLUS_HA_DISCOVERY_SENSORS = [
    {
        "metric": "temperature",
        "name": "Temperature",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "value_template": "{{ value_json.temperature }}",
    },
    {
        "metric": "humidity",
        "name": "Humidity",
        "device_class": "humidity",
        "unit": "%",
        "state_class": "measurement",
        "value_template": "{{ value_json.humidity }}",
    },
    {
        "metric": "pressure",
        "name": "Pressure",
        "device_class": "pressure",
        "unit": "hPa",
        "state_class": "measurement",
        "value_template": "{{ value_json.pressure }}",
    },
    {
        "metric": "lux",
        "name": "Illuminance",
        "device_class": "illuminance",
        "unit": "lx",
        "state_class": "measurement",
        "value_template": "{{ value_json.lux }}",
    },
    {
        "metric": "pm25",
        "name": "PM2.5",
        "device_class": "pm25",
        "unit": "µg/m³",
        "state_class": "measurement",
        "value_template": "{{ value_json.pm25 }}",
    },
    {
        "metric": "pm10",
        "name": "PM10",
        "device_class": "pm10",
        "unit": "µg/m³",
        "state_class": "measurement",
        "value_template": "{{ value_json.pm10 }}",
    },
]


def publish_ha_discovery(
    mqtt_client: mqtt.Client,
    config: dict[str, Any],
    topics: list[str],
) -> None:
    """Publish Home Assistant MQTT discovery sensor configurations for Enviro+."""
    if not bool(config.get("ha_discovery", False)):
        return
    prefix = str(config.get("ha_discovery_prefix", "homeassistant"))
    device_id = str(config.get("device_id", "enviroplus"))
    state_topic = topics[0] if topics else f"{device_id}/sensors"
    status_topic = f"{state_topic}/status"
    qos = int(config.get("qos", 1))

    device_info = {
        "identifiers": [device_id],
        "name": f"Enviro+ ({device_id})",
        "model": "Pimoroni Enviro+",
        "manufacturer": "Pimoroni",
    }

    for sensor in ENVIROPLUS_HA_DISCOVERY_SENSORS:
        metric = sensor["metric"]
        disc_topic = f"{prefix}/sensor/{device_id}/{metric}/config"
        disc_payload: dict[str, Any] = {
            "name": f"{device_id} {sensor['name']}",
            "unique_id": f"{device_id}_{metric}",
            "state_topic": state_topic,
            "value_template": sensor["value_template"],
            "device_class": sensor["device_class"],
            "unit_of_measurement": sensor["unit"],
            "state_class": sensor["state_class"],
            "availability_topic": status_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": device_info,
        }
        data = json.dumps(disc_payload).encode("utf-8")
        try:
            mqtt_client.publish(topic=disc_topic, payload=data, qos=qos, retain=True)
        except Exception as exc:
            LOGGER.debug("Could not publish HA discovery for %s: %s", metric, exc)


def create_mqtt_client(config: dict[str, Any]) -> mqtt.Client:
    """Create and connect a long-lived MQTT client with callbacks, LWT, and background loop."""
    host = config["host"]
    port = int(config.get("port", 1883))
    username = config.get("username")
    password = config.get("password")
    client_id = config.get("client_id")
    topics = config.get("topics", [])
    tls_enabled = bool(config.get("tls", False)) or bool(config.get("tls_ca_certs"))

    if client_id:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=str(client_id))
    else:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        if rc == 0:
            LOGGER.info("Successfully connected to MQTT broker at %s:%s", host, port)
            for topic in topics:
                client.publish(f"{topic}/status", "online", qos=1, retain=True)
            publish_ha_discovery(client, config, topics)
        else:
            LOGGER.error("Failed to connect to MQTT broker at %s:%s: code %s", host, port, rc)

    def on_disconnect(
        client: mqtt.Client, userdata: Any, disconnect_flags: Any, rc: Any, properties: Any = None
    ) -> None:
        if rc != 0:
            LOGGER.warning("Unexpected disconnection from MQTT broker (code %s). Reconnecting...", rc)
        else:
            LOGGER.info("Disconnected from MQTT broker.")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if tls_enabled and hasattr(client, "tls_set"):
        ca_certs = config.get("tls_ca_certs")
        certfile = config.get("tls_certfile")
        keyfile = config.get("tls_keyfile")
        insecure = bool(config.get("tls_insecure", False))
        client.tls_set(ca_certs=ca_certs, certfile=certfile, keyfile=keyfile)
        if hasattr(client, "tls_insecure_set"):
            client.tls_insecure_set(insecure)

    if username and password:
        client.username_pw_set(username, password=password)

    # Set Last Will and Testament for offline status upon unexpected termination
    for topic in topics:
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)

    protocol = "mqtts" if tls_enabled else "mqtt"
    LOGGER.info("Connecting to MQTT broker at %s://%s:%s", protocol, host, port)
    client.connect(host, port, keepalive=60)
    client.loop_start()

    return client


def publish_payload(
    mqtt_client: mqtt.Client,
    topics: list[str],
    payload: dict[str, Any],
    timeout: float = 10.0,
    qos: int = 1,
    retain: bool = True,
    per_metric_topics: bool = False,
) -> bool:
    """
    Publish JSON payload to all topics with configurable QoS and retain.

    Returns:
        bool: True if published successfully to all topics, False otherwise.
    """
    data = json.dumps(payload).encode("utf-8")
    all_succeeded = True

    for topic in topics:
        LOGGER.info("Publishing msg to topic %s: %s", topic, data.decode("utf-8"))
        msg_info = mqtt_client.publish(topic=topic, payload=data, qos=qos, retain=retain)
        if hasattr(msg_info, "wait_for_publish"):
            try:
                msg_info.wait_for_publish(timeout=timeout)
            except (ValueError, RuntimeError) as exc:
                LOGGER.error("Publish to %s failed or timed out: %s", topic, exc)
                all_succeeded = False
                continue

        if msg_info.rc != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.error("Publishing to topic %s failed with code: %s", topic, msg_info.rc)
            all_succeeded = False

        if per_metric_topics:
            for k, v in payload.items():
                if not k.startswith("unit_of_") and k != "time_utc":
                    subtopic = f"{topic.rstrip('/')}/{k}"
                    try:
                        mqtt_client.publish(topic=subtopic, payload=str(v).encode("utf-8"), qos=qos, retain=retain)
                    except Exception as exc:
                        LOGGER.debug("Could not publish per-metric to %s: %s", subtopic, exc)

    if all_succeeded:
        LOGGER.info("All messages successfully published.")
    return all_succeeded


def disconnect_mqtt_client(
    mqtt_client: mqtt.Client,
    topics: list[str] | None = None,
) -> None:
    """Publish offline status and disconnect cleanly."""
    if topics:
        for topic in topics:
            try:
                msg_info = mqtt_client.publish(f"{topic}/status", "offline", qos=1, retain=True)
                if hasattr(msg_info, "wait_for_publish"):
                    msg_info.wait_for_publish(timeout=2.0)
            except Exception as exc:
                LOGGER.debug("Could not publish offline status to %s: %s", topic, exc)

    try:
        mqtt_client.disconnect()
    except Exception as exc:
        LOGGER.debug("Error disconnecting MQTT client: %s", exc)

    try:
        mqtt_client.loop_stop()
    except Exception as exc:
        LOGGER.debug("Error stopping MQTT loop: %s", exc)
