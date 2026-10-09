"""MQTT client setup, connection lifecycle, and publishing."""

from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger(__name__)


def create_mqtt_client(config: dict[str, Any]) -> mqtt.Client:
    """Create and connect a long-lived MQTT client with callbacks, LWT, and background loop."""
    host = config["host"]
    port = int(config.get("port", 1883))
    username = config.get("username")
    password = config.get("password")
    client_id = config.get("client_id")
    topics = config.get("topics", [])

    if client_id:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    else:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        if rc == 0:
            LOGGER.info("Successfully connected to MQTT broker at %s:%s", host, port)
            for topic in topics:
                client.publish(f"{topic}/status", "online", qos=1, retain=True)
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

    if username and password:
        client.username_pw_set(username, password=password)

    # Set Last Will and Testament for offline status upon unexpected termination
    for topic in topics:
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)

    LOGGER.info("Connecting to MQTT broker at mqtt://%s:%s", host, port)
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
