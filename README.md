# Enviroplus Sensors to MQTT

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A python utility to publish data from Enviro+ sensors to an MQTT broker.

## Read-Only Filesystem
If running on a read-only filesystem, refer to [this guide](https://medium.com/swlh/make-your-raspberry-pi-file-system-read-only-raspbian-buster-c558694de79) for setup instructions.

## System Dependencies

Some system-level dependencies may be required before installing the python packages:

```bash
curl -sSL https://get.pimoroni.com/enviroplus | bash
sudo apt install python3-psutil python3-venv
```

## Requirements

- `make` (optional, for simplified build commands)
- `uv` (modern Python package manager, install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### System Dependencies
Before installing, you must install the required system libraries to compile hardware dependencies and interface with the I2C bus:
```bash
sudo apt-get update
sudo apt-get install -y python3-dev gcc i2c-tools cmake libffi-dev
```

## Installation & Setup

We recommend using the included `Makefile` to handle creating a virtual environment and installing dependencies safely using `uv`.

### 1. Local Development / Virtual Environment

To set up a local virtual environment (`.venv`) and install dependencies:

```bash
make install
```

You can then run the tool directly from the virtual environment:
```bash
uv run enviroplussensorstomqtt
```
Alternatively, activate the venv directly and run it:
```bash
source .venv/bin/activate
enviroplussensorstomqtt
```

### 2. Running Tests & Linting

To run the test suite and `ruff` linting using `uv`:

```bash
make test
```

## Configuration

The application can be configured via command-line arguments or a YAML configuration file. It will look for a config file in the following order:
1. File specified by `--config_file`
2. `/etc/enviroplussensorstomqtt.yaml`
3. `config.yaml` in the current directory

### YAML Configuration Example

```yaml
host: "192.168.1.100"
port: 1883
username: "mqtt_user"
password: "mqtt_password"
topics:
  - "home/sensors/enviroplus"
debug: false
daemon: false
```

### Command Line Arguments

You can override any YAML configuration via CLI flags:
- `--host`: MQTT broker host
- `--port`: MQTT broker port (default 1883)
- `--username`: MQTT username
- `--password`: MQTT password
- `--topics`: Comma-separated list of topics
- `--config_file`: Path to a custom YAML config file
- `--pid_file`: Path to store the PID file (useful when daemonized)
- `-D, --debug`: Enable debug logging
- `--daemon`: Run as a background daemon process

## Systemd Service

To install this application as a background service managed by `systemd`, run:

```bash
make install-service
```

This command will:
1. Create a wrapper script in `/usr/local/bin/enviroplussensorstomqtt` that natively targets the `.venv` isolated environment in this folder.
2. Copy the systemd unit file from `systemd/enviroplussensorstomqtt.service` to `/etc/systemd/system/`.
3. Reload the systemd daemon.

After installation, you can enable and start the service:

```bash
sudo systemctl enable enviroplussensorstomqtt
sudo systemctl start enviroplussensorstomqtt
```

To view logs:
```bash
journalctl -u enviroplussensorstomqtt -f
```
