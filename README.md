# Enviroplus Sensors to MQTT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A robust Python service that reads environmental sensor data from a Pimoroni Enviro+ HAT on a Raspberry Pi and publishes structured JSON payloads to an MQTT broker.

---

## Features

- **Sensors supported**: BME280 (temperature, humidity, pressure), MICS6814 (reducing, oxidising, NH3 gas resistance), MEMS microphone (noise low/mid/high/amp), and PMS5003 particulate matter sensor (PM1, PM2.5, PM10).
- **Fault-isolated sampling**: Transient I2C/serial/sensor errors are handled cleanly per sensor group rather than crashing the service.
- **Self-heating compensation**: Configurable temperature offset (`--temperature_offset` / `temperature_offset`).
- **Resilient MQTT loop**: Long-lived connection with automatic reconnect, error-checked publishing, and Last Will and Testament (LWT) offline messaging.
- **systemd-first architecture**: Direct console logging formatted for `journald` with graceful shutdown on `SIGTERM` / `SIGINT`.
- **Environment variable secrets**: Secure credential loading via `MQTT_HOST`, `MQTT_USERNAME`, and `MQTT_PASSWORD`.

---

## Hardware & System Prerequisites (Raspberry Pi)

Ensure the required Raspberry Pi hardware interfaces are enabled via `raspi-config`:
- **I2C**: Enabled (`Interface Options -> I2C`)
- **SPI**: Enabled (`Interface Options -> SPI`)
- **Serial Port**: Hardware serial enabled, serial console disabled (`Interface Options -> Serial Port`)
- **Microphone**: If using the MEMS noise sensor, ensure the microphone audio overlay is enabled in `/boot/config.txt`.

Install system libraries required by the sensor hardware stacks:
```bash
sudo apt-get update
sudo apt-get install -y python3-dev gcc i2c-tools cmake libffi-dev libopenblas0
```

---

## Installation & Setup

We recommend using [uv](https://github.com/astral-sh/uv) for fast, deterministic installs:

```bash
# Clone the repository
git clone https://github.com/hellqvio86/enviroplus-sensors-to-mqtt.git
cd enviroplus-sensors-to-mqtt

# Install dependencies into local virtualenv
make install
```

### Running Tests & Linting

```bash
make test
```

---

## Configuration

Configuration is loaded and merged with the following precedence (highest to lowest):
1. Command-line flags
2. Environment variables (`MQTT_HOST`, `MQTT_USERNAME`, `MQTT_PASSWORD`)
3. YAML config file (`--config_file <path>`, `/etc/enviroplussensorstomqtt.yaml`, or `./config.yaml`)
4. Built-in defaults

### Configuration Reference

| Option | CLI Flag | Environment Variable | Default | Description |
|---|---|---|---|---|
| `host` | `--host` | `MQTT_HOST` | *(required)* | MQTT broker hostname or IP |
| `port` | `--port` | - | `1883` | MQTT broker port (1-65535) |
| `topics` | `--topics` | - | *(required)* | Comma-separated list of MQTT topics |
| `username` | `--username` | `MQTT_USERNAME` | `None` | MQTT broker username (optional) |
| `password` | `--password` | `MQTT_PASSWORD` | `None` | MQTT broker password (optional) |
| `interval` | `--interval` | - | `60.0` | Seconds between measurement cycles |
| `measurements` | `--measurements` | - | `3` | Number of samples to median per cycle |
| `temperature_offset` | `--temperature_offset` | - | `0.0` | °C offset to subtract for board self-heating |
| `enable_ltr559` | `--disable-ltr559` | - | `true` | Enable/disable LTR559 light and proximity sensor |
| `client_id` | - | - | `None` | Optional MQTT client ID |
| `qos` | - | - | `1` | MQTT QoS level (0, 1, or 2) |
| `retain` | - | - | `true` | Retain published MQTT messages |
| `debug` | `-D`, `--debug` | - | `false` | Enable verbose debug logging |
| `log_file` | `--log_file` | - | `None` | Optional file path for file logging |

### YAML Configuration Example

Save as `/etc/enviroplussensorstomqtt.yaml` or `config.yaml` with permissions `chmod 600 config.yaml`:

```yaml
host: "192.168.1.50"
port: 1883
username: "mqtt_user"
password: "secure_password"
topics:
  - "home/sensors/livingroom/enviroplus"
interval: 60.0
measurements: 3
temperature_offset: 2.5
enable_ltr559: true
qos: 1
retain: true
debug: false
```

---

## Example MQTT Payload

Readings are published as a retained JSON object:

```json
{
  "temperature": 21.45,
  "unit_of_temperature": "C",
  "humidity": 45.20,
  "unit_of_humidity": "%",
  "pressure": 1013.2,
  "unit_of_pressure": "mbar",
  "noise_low": 0.12,
  "noise_mid": 0.08,
  "noise_high": 0.05,
  "noise_amp": 0.02,
  "gas_oxidising": 182500,
  "unit_of_gas_oxidising": "Ohms",
  "gas_reducing": 245000,
  "unit_of_gas_reducing": "Ohms",
  "gas_nh3": 312000,
  "unit_of_gas_nh3": "Ohms",
  "pm1": 2,
  "pm25": 6,
  "pm10": 9,
  "lux": 150.25,
  "unit_of_lux": "Lux",
  "proximity": 38,
  "time_utc": "2026-10-09T08:30:00.000000"
}
```

---

## Systemd Service Installation

To install as a background service:

```bash
make install-service
sudo systemctl enable enviroplussensorstomqtt
sudo systemctl start enviroplussensorstomqtt
```

Check status and follow logs:

```bash
sudo systemctl status enviroplussensorstomqtt
journalctl -u enviroplussensorstomqtt -f
```
