# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Temperature compensation for Enviro+ self-heating (`--temperature_offset` / `temperature_offset`).
- Typed configuration validation using `AppConfig` dataclass to fail fast on invalid configs.
- Environment variable support for credentials (`MQTT_HOST`, `MQTT_USERNAME`, `MQTT_PASSWORD`).
- Last Will and Testament (LWT) status messages (`offline` / `online`) on shutdown/crash.
- Hardware abstraction layer (`hardware.py`) decoupling hardware libraries from imports.
- Comprehensive test suite covering configuration, args, logging, payload generation, fault isolation, and shutdown.
- CI matrix workflow for Python 3.11, 3.12, and 3.13.

### Fixed
- All 7 Dependabot CVE vulnerability alerts resolved by upgrading `requires-python = ">=3.11"`.
- Fixed missing console logs under systemd / journald.
- Handled sensor fault isolation so PMS5003 or gas sensor errors do not crash the service loop.
- Ensured hardware handles and MQTT connections are persistent across cycles and properly closed on exit.
- Removed buggy custom daemonizer; fully aligned with systemd.
- Fixed unit file permissions and duplicate keys in systemd service.
- Applied precision rounding to sensor payload values.
