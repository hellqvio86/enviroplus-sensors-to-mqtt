# todo.md: critical review of enviroplus-sensors-to-mqtt

Audience: AI coding agents (and humans). Read `AGENTS.md` first.
Reviewed at commit `b58a5a3` (version 0.0.2).

How to use this file:
- Work top-down by priority. One item per change set. Tick the box when merged.
- Each item has: **Where** (files), **Problem**, **Fix**, **Done when** (testable acceptance criteria).
- Evidence tags: `[verified]` = reproduced by running the code in a sandbox; `[code]` = established by
  reading the code (not run on hardware); `[hw]` = needs a Raspberry Pi + Enviro+ to confirm.
- Tests must not touch hardware or a real broker (fake `SMBus`/`BME280`/`gas`/`Noise`/`PMS5003`/MQTT client).

## Summary

The project does its one job in the happy path, but it is fragile: any transient I2C, serial or
network error kills the process, the default (non-debug) run mode emits no logs at all, CLI-only
configuration is impossible despite the README, hardware/MQTT handles are never released, and the
test suite is one import check. The daemonizer is legacy code with real bugs that systemd makes
unnecessary. Fix P0 first; P1 makes it trustworthy; P2/P3 are quality and features.

---

## P0: Bugs that break documented or default behaviour

### [x] P0-1 CLI-only configuration crashes when no config file exists `[verified]`
- **Where:** `args.py:30-37`, `config.py:33-34`
- **Problem:** `args_handler()` always ends in `parse_config()`, which raises `FileNotFoundError` if
  `config.yaml` is missing. Running `enviroplussensorstomqtt --host h --username u --password p --topics t`
  with no config file produces a traceback. README says config can come from CLI args *or* YAML.
- **Fix:** Make the config file optional. Resolve in order: `--config_file` (error if given but missing),
  `/etc/enviroplussensorstomqtt.yaml`, `./config.yaml`, then fall back to defaults only. Apply defaults
  in one place after merging file + CLI.
- **Done when:** a test runs `args_handler` (refactored to accept `argv`) with only CLI flags and no file and
  gets a valid config; a test shows `--config_file /nonexistent` still errors clearly.

### [x] P0-2 Default run mode produces no logs `[verified]`
- **Where:** `logging.py:22-37`
- **Problem:** With neither `--debug` nor `--daemon`, `setup_logger` sets the root level to INFO but adds
  **no handler**. Python then falls back to `logging.lastResort`, which only emits WARNING+ to stderr.
  Under systemd (the documented deployment) all `LOGGER.info(...)` output, including "Connecting",
  "Publishing" and "messages published", is silently dropped. Verified: `handlers: []` after setup.
- **Fix:** Always attach a console `StreamHandler` (stderr) so journald captures it; add the rotating file
  handler only when a log file is explicitly configured. `--debug` just lowers the level.
- **Done when:** test calls `setup_logger()` with defaults, emits an INFO record, and captures it via a handler
  on the root logger (assert `root.handlers` non-empty and the record is formatted).

### [x] P0-3 `--debug` fails unless `/var/log/enviroplussensorstomqtt/` exists and is writable `[verified]`
- **Where:** `logging.py:22-27`, `config.py:45-47`
- **Problem:** `-D` always creates a `RotatingFileHandler` at the default `/var/log/...` path. On a dev box or
  as a non-root user this raises `FileNotFoundError`/`PermissionError` before the app starts.
- **Fix:** Only create a file handler if `log_file` is explicitly set; default to `None`. If the file cannot
  be opened, log a warning and continue with console logging.
- **Done when:** `setup_logger(debug=True)` succeeds with no `log_file`; test with an unwritable path logs a
  warning and does not raise.

### [ ] P0-4 Any exception kills the service; there is no error handling in the main loop `[code]`
- **Where:** `main.py:34-47`, `sensor.py:23-42, 158-166`
- **Problem:** `send_sensor_data` can raise on I2C errors, `PMS5003` timeouts (the retry inside
  `read_pms5003` is itself unguarded), DNS/connection failures from `mqtt_client.connect`, etc. Nothing in
  `main()` catches them, so one transient failure terminates the process and relies on systemd to restart it
  (and the unit has contradictory `Restart=` lines, see P1-8).
- **Fix:** Wrap each cycle in `try/except Exception`, log with `LOGGER.exception`, and continue with the next
  cycle. Isolate sensors so one failing sensor (e.g. PMS5003 absent) does not discard the others: publish what
  was read and omit or null the missing fields. Back off after repeated failures.
- **Done when:** tests inject a failing PMS5003 and a failing `connect`; the loop survives, other sensors'
  values are still published, and the failure is logged.

### [ ] P0-5 Hardware handles and the MQTT client are created every cycle and never released `[code]` `[hw]`
- **Where:** `sensor.py:68-71, 136`, `main.py:36`
- **Problem:** Every cycle creates a new `SMBus(1)`, `BME280`, `Noise`, `PMS5003`, and a new
  `mqtt.Client`. None are closed (`SMBus.close()`, serial/GPIO release, `mqtt_client.disconnect()`).
  Over days this leaks file descriptors and sockets, and re-acquiring GPIO/serial lines each minute can fail
  with "device busy" on some stacks (needs confirmation on a Pi).
- **Fix:** Initialise sensors once at startup (a `Sensors` class or context manager with `close()`), reuse them
  across cycles, and create one long-lived MQTT client with `loop_start()`, automatic reconnect, and
  `disconnect()`/`loop_stop()` on shutdown. If per-cycle init must stay, use `try/finally` to release.
- **Done when:** unit test with fakes asserts each opened resource is closed exactly once on both success and
  failure paths; a long-run check on a Pi (human) shows stable FD count (`ls /proc/<pid>/fd | wc -l`).

### [ ] P0-6 MQTT publish is fire-and-forget with no loop, no result check, no disconnect `[code]`
- **Where:** `sensor.py:158-168`
- **Problem:** `connect()` + `publish()` without `loop_start()/loop_forever()` or `wait_for_publish()`.
  Return codes are ignored, so "messages published" is logged even if nothing was delivered. The client never
  disconnects. `connect()` failure raises (see P0-4).
- **Fix:** Use the long-lived client from P0-5; check `MQTTMessageInfo.rc`, call `wait_for_publish(timeout=...)`,
  log failures, and set `on_connect`/`on_disconnect` callbacks. Choose QoS deliberately (default 1).
- **Done when:** test with a fake client asserts failed publish returns are logged as errors and not as success.

### [x] P0-7 Pidfile bug writes the *stale* PID `[code]`
- **Where:** `daemonizer.py:43-63`
- **Problem:** `pid` is reassigned from the pidfile contents. If a stale pidfile exists for a dead process, the
  code then writes that **old** PID instead of `os.getpid()`. Non-numeric content leaves `pid` as `str`, so
  `psutil.pid_exists(pid)` raises `TypeError`. The file handle in the read branch is never closed.
- **Fix:** Use separate variables, validate with `int()` in try/except, use `with open(...)`. (Or remove the
  daemonizer entirely, see P1-1, which supersedes this item.)
- **Done when:** if P1-1 is not done first, tests cover stale, live, and garbage pidfiles.

---

## P1: Reliability, correctness and security

### [x] P1-1 Remove (or quarantine) the hand-rolled daemonizer `[code]`
- **Where:** `daemonizer.py`, `main.py:27-30`, `args.py` (`--daemon`, `--pid_file`), `config.py`, `logging.py`, `pyproject.toml` (`psutil`)
- **Problem:** The service is meant to run under systemd with `Type=simple`; self-daemonising conflicts with that
  and the module has multiple defects beyond P0-7: `Daemonizer.__init__` performs the forks (side effects in
  a constructor); `start()` daemonises twice; uses `os.setpgrp()` rather than `os.setsid()`; sets `umask(0)`
  (world-writable files); redirects stdio after logging is configured; never removes the pidfile; assumes
  `/run/enviroplussensorstomqtt/` exists; `___setup_pidfile` has a three-underscore name.
- **Fix:** Delete the module and the `--daemon`/`--pid_file` options (deprecate with a warning for one release if
  you want), drop `psutil`. Document systemd as the supported way to run in the background.
- **Done when:** no references remain, `psutil` is removed from dependencies and `uv.lock`, README updated.

### [ ] P1-2 Validate configuration; fail fast with clear errors `[code]`
- **Where:** `sensor.py:62-66`, `args.py:21,48-49`, `config.py`
- **Problem:** Required keys (`host`, `topics`, and `username`/`password`) are read with `config[...]` deep inside
  the sensor function, producing a bare `KeyError` mid-run. Anonymous brokers (no credentials) are impossible.
  `--port` is parsed as `str` then `int()`'d (bad input = traceback). `topics` accepts a YAML string or list
  without checking. Empty `topics` silently publishes nothing.
- **Fix:** Introduce a typed config object (a `dataclass` with a `validate()` step): required `host`, non-empty
  `topics: list[str]`, `port: int` (1-65535), optional `username`/`password`. Validate once at startup and exit
  with a readable message. Make `--port` `type=int`.
- **Done when:** parametrised tests cover missing host, empty topics, bad port, anonymous broker (works), and
  YAML-string vs list topics.

### [ ] P1-3 Password handling: leaks and weak storage `[code]`
- **Where:** `args.py:66-67`, `README.md` (config example), `Makefile`/systemd unit
- **Problem:** `-D` prints the whole config dict including the **MQTT password** to stdout. Passing
  `--password` on the command line exposes it in `ps`/`/proc/*/cmdline`. README example encourages plaintext
  creds in a world-readable `/etc` file.
- **Fix:** Redact secrets in any config logging (`password: "***"`). Support `MQTT_PASSWORD` (and
  `MQTT_USERNAME`) env vars and/or `password_file`; document `chmod 600` on the config; consider
  `EnvironmentFile=`/`LoadCredential=` in the unit. Warn on startup if the config file is group/world readable.
- **Done when:** test asserts the debug config dump never contains the password; env-var override is tested.

### [ ] P1-4 Fix datetime usage and payload hygiene `[code]`
- **Where:** `sensor.py:152`, `sensor.py:73-133`
- **Problem:** `datetime.utcnow()` is deprecated (3.12) and returns a naive timestamp with microseconds and no
  `Z`/offset, so consumers cannot tell it is UTC. Floats are unrounded (e.g. `23.456789012`). Every message
  repeats `unit_of_*` keys. Noise values have no unit. All 5 key families are mixed in one flat dict.
- **Fix:** `datetime.now(datetime.UTC).isoformat(timespec="seconds")` (or epoch). Round values sensibly
  (temp/hum 0.01, pressure 0.1, gas int, PM int). Decide and document a versioned payload schema; keep the
  existing keys for backward compatibility (see AGENTS.md pitfall 2) or bump a `schema_version` field.
- **Done when:** schema documented in README; test builds a payload from fake readings and asserts keys, types,
  rounding and an offset-aware timestamp.

### [ ] P1-5 Sensor accuracy: temperature self-heating and warm-up `[code]` `[hw]`
- **Where:** `sensor.py:73-79, 115-133, 136-150`
- **Problem:** BME280 temperature on an Enviro+ reads several °C high because of CPU/board heat; there is no
  compensation or configurable offset, and humidity (derived from the same temperature) is therefore also
  wrong. PMS5003 and the MICS6814 gas sensor need warm-up/stabilisation; the code reads after a fresh init
  and first samples can be stale or zero. The median of 3 one-second samples does not address either.
- **Fix:** Add config for `temperature_offset` and/or CPU-temperature-based compensation (the Pimoroni examples
  show the pattern), and optional warm-up discard (`discard_first_n`). Document known accuracy limits.
- **Done when:** compensation is a pure function with unit tests; README documents the option and its caveat.

### [ ] P1-6 Make the cycle time deterministic and configurable `[code]`
- **Where:** `main.py:34-47`, `sensor.py:46,75-150`
- **Problem:** Six sensor groups x 3 samples x `sleep(1)` is at least 18 s of blocking sleeps before MQTT
  work, so readings are taken seconds apart and the cycle length is implicit. The 60 s interval and
  `measurements` are hardcoded and not exposed. If a cycle exceeds 60 s the loop spins with no sleep
  (`sleep_time <= 0` skips the sleep, which also means no minimum pause).
- **Fix:** Add `interval` and `measurements` to config/CLI; sample sensors in a loop of N rounds (read all
  sensors per round) so fewer sleeps are needed; use `time.monotonic()`; enforce a minimum sleep.
- **Done when:** tests with a fake clock verify cadence and that overrun cycles log a warning.

### [ ] P1-7 Graceful shutdown and signals `[code]`
- **Where:** `main.py:34`
- **Problem:** `while True` with no `SIGTERM`/`SIGINT` handling: `systemctl stop` kills mid-read; MQTT is never
  disconnected cleanly; retained messages stay forever with no availability signal.
- **Fix:** Use a `threading.Event` for the loop and sleeping; handle SIGTERM/SIGINT; on exit publish an
  "offline" status and disconnect. Use a Last Will and Testament (`will_set`) for crash detection.
- **Done when:** test sets the stop event and asserts resources are closed and the offline message published.

### [ ] P1-8 Fix the systemd unit `[code]`
- **Where:** `systemd/enviroplussensorstomqtt.service`, `Makefile` (`install-service`)
- **Problem:** Description says "Sense hat sensors to MQTT" and a comment says "Python Demo Service" (wrong
  product). `Restart=always` is declared and then overridden by a later `Restart=on-failure` (duplicate key).
  `RemainAfterExit=yes` is meaningless for `Type=simple`. `After=network.target` should be
  `network-online.target` (+ `Wants=`). Runs as **root** with no hardening. File has CRLF line endings.
  `TimeoutStartSec=600` is unexplained. The unit does not pass `--config_file`, so the service silently depends
  on `/etc/...yaml` existing. The installed wrapper hardcodes `$(CURDIR)/.venv/bin/...`, so moving or deleting
  the checkout breaks the service.
- **Fix:** Correct description; single `Restart=on-failure`/`always` with `RestartSec`; remove
  `RemainAfterExit`; `network-online.target`; run as a dedicated user in the needed groups (`i2c`, `gpio`,
  `spi`, `audio`, `dialout`; verify on a Pi); add hardening
  (`NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, etc., validated with
  `systemd-analyze security`); convert to LF; consider installing into a fixed venv path
  (e.g. `/opt/enviroplussensorstomqtt`) instead of the checkout.
- **Done when:** `systemd-analyze verify` passes in CI (or documented manual check); no duplicate keys; LF endings.

### [ ] P1-9 Real test suite, and make the code testable `[code]`
- **Where:** `src/tests/test_basic.py` (only test), `sensor.py`, `args.py`
- **Problem:** The only test asserts the package imports and has a `main` attribute: effectively 0 % behavioural
  coverage. `args_handler()` reads `sys.argv` internally and can't be tested without monkeypatching.
  `send_sensor_data` is a ~120-line function mixing hardware access, statistics, and networking, with four
  copy-pasted "collect 3 samples then median" blocks.
- **Fix:** Refactor into `read_*` helpers + `build_payload()` + `publish()`; extract
  `median_of(fn, n, delay)`; give `args_handler(argv=None)` an argv parameter. Add
  `tests/conftest.py` with fakes. Cover: config merging and precedence, validation, payload building and
  rounding, failing-sensor isolation, publish error handling, loop control, logging setup.
- **Done when:** `pytest --cov=enviroplussensorstomqtt` reports >= 80 % and runs with no hardware libs
  importable (stub them in `sys.modules`); add a coverage gate in CI.

### [ ] P1-10 Package imports pull in hardware stacks eagerly `[code]`
- **Where:** `__init__.py:4`, `sensor.py:10-18`
- **Problem:** `import enviroplussensorstomqtt` imports `main` -> `sensor` -> `bme280`, `enviroplus.gas`, `pms5003`
  (and `Noise` lazily at `sensor.py:70`). The current import test only passes because those wheels install
  on x86 Linux; on other platforms or minimal environments the import fails, and `Noise` is imported lazily
  for the same reason, inconsistently.
- **Fix:** Keep `__init__` light (export version only). Import hardware modules inside a `hardware.py`
  adapter, behind interfaces, so everything else is importable and testable.
- **Done when:** `python -c "import enviroplussensorstomqtt"` succeeds with the hardware libs absent.

---

## P2: Packaging, dependencies, CI and docs

### [ ] P2-1 Tests are shipped inside the wheel `[verified]`
- **Where:** `pyproject.toml` (`[tool.setuptools.packages.find]`), `src/tests/`
- **Problem:** Building the wheel includes a top-level `tests/test_basic.py` (namespace package auto-discovery).
- **Fix:** Move tests to repo-root `tests/` **or** set `include = ["enviroplussensorstomqtt*"]` in the `find`
  config. Update Makefile and CI paths accordingly.
- **Done when:** `pip wheel . --no-deps` contains only `enviroplussensorstomqtt/` and dist-info.

### [ ] P2-2 Declare and bound dependencies correctly `[code]`
- **Where:** `pyproject.toml`
- **Problem:** `paho-mqtt` has no lower bound but the code requires `>=2.0` (`CallbackAPIVersion`). Directly used
  libs are only transitively installed (`smbus2`, `pimoroni-bme280`, `pms5003`) and `sensor.py` has a
  `smbus2` -> `smbus` fallback that metadata doesn't reflect. `pyyaml` is duplicated in the `tests` extra.
  `ruff` is installed ad hoc by the Makefile rather than declared. Unneeded heavy deps: `setproctitle`
  (native build, cosmetic) and `psutil` (only for the daemonizer).
- **Fix:** Add bounds (`paho-mqtt>=2.0,<3`), declare directly imported packages, add a `dev` extra
  (`pytest`, `pytest-cov`, `ruff`, type checker), drop `psutil` (P1-1), make `setproctitle` optional or remove.
- **Done when:** a clean venv install from metadata alone runs tests; `uv lock --check` passes.

### [ ] P2-3 Makefile does not use the lockfile; wasteful `test` target `[code]`
- **Where:** `Makefile`
- **Problem:** `uv.lock` exists and Dependabot manages it, but `uv pip install -e` ignores it, so installs are
  not reproducible. `test` depends on `install`, so every test run reinstalls. `--system-site-packages` +
  `--index-strategy unsafe-best-match` is a dependency-confusion-prone setting. `install-service` writes via
  `/tmp` with `echo` (fragile quoting).
- **Fix:** Use `uv sync --extra tests`/`dev` (document when `--system-site-packages` is truly required on a Pi);
  split `install` and `test`; restrict extra-index usage to piwheels only where needed; install the wrapper
  with `install -m 0755` from a template file.
- **Done when:** `make test` does not reinstall when nothing changed; install is reproducible from `uv.lock`.

### [ ] P2-4 CI improvements `[code]`
- **Where:** `.github/workflows/ci.yml`
- **Problem:** Single Python version (3.11 only) although `>=3.11` is claimed; apt-installed `python3-*`
  packages are installed for the system interpreter but tests run in a different venv (largely redundant);
  `setup-uv` is `version: "latest"`; actions pinned by tag not SHA; no coverage, type-check, wheel build
  check, or `systemd-analyze verify`.
- **Fix:** Matrix 3.11/3.12/3.13; pin tool versions and action SHAs; add `ruff format --check`, type check,
  coverage threshold, `python -m build` + `twine check`, and wheel-contents assertion.
- **Done when:** CI is green on the matrix and fails on a deliberately broken wheel/test.

### [ ] P2-5 Tighten linting and add type checking `[code]`
- **Where:** `pyproject.toml` (`[tool.ruff.lint]`), source files
- **Problem:** Rules are only `E,F,W,I`. Missing `B` (bugbear), `UP` (would flag `utcnow`, implicit Optional),
  `S` (security), `SIM`, `N`, `PTH`, `RUF`, `ARG`. `x: str = None` annotations are wrong. Docstring styles
  are inconsistent (reST vs Google vs none). No `py.typed`, no mypy/pyright.
- **Fix:** Enable those rule sets and fix findings; add `mypy` or `pyright` (strict for new modules); add
  `pre-commit` config (ruff, ruff-format, end-of-file, mixed-line-ending).
- **Done when:** `ruff check .` and the type checker are clean in CI.

### [ ] P2-6 README gaps and inaccuracies `[code]`
- **Where:** `README.md`
- **Problem:** Documents two overlapping "System Dependencies" sections; omits mandatory Pi setup (enable I2C,
  SPI, serial/UART for the PMS5003, and the microphone overlay for noise); does not document the MQTT payload,
  units, topics, QoS/retain behaviour, `--log_file`, or the `log_file`/`pid_file` config keys; says CLI-only
  works (it doesn't, P0-1); suggests `curl | bash` installer without comment; links an external Medium
  article for read-only FS. No troubleshooting section, no example payload, no uninstall steps.
- **Fix:** Rewrite with: hardware/OS prerequisites, single deps section, full config reference table,
  example JSON payload, troubleshooting (I2C not found, PMS timeouts, no audio device), systemd instructions,
  security notes (P1-3).
- **Done when:** every CLI flag and config key in code appears in README (add a test that diffs argparse
  options against the README).

### [ ] P2-7 Metadata and housekeeping `[code]`
- **Where:** `pyproject.toml`, `.gitignore`, repo root
- **Problem:** Description says "aio library" but the code is a synchronous application. Classifier
  `Topic :: Software Development :: Build Tools` is wrong (use e.g. `Topic :: Home Automation`). `Download` URL
  points to an archive (`v_01.tar.gz`) that doesn't match version `0.0.2`. `.gitignore` contains an unrelated
  tool directory (`.antigravitycli/`). No `CHANGELOG`, no release/tag process, no `.gitattributes` to enforce
  LF (CRLF currently present in `colors.py` and the unit file), no `CONTRIBUTING`/`SECURITY`.
- **Fix:** Correct metadata; drop the stale Download URL; add `.gitattributes` (`* text=auto eol=lf`) and
  normalise files; add `CHANGELOG.md`; adopt tag-driven versioning.
- **Done when:** `twine check` is clean and `git ls-files --eol` shows no CRLF in tracked text files.

---

## P3: Cleanup and features

### [x] P3-1 Delete or integrate `colors.py` `[code]`
- **Where:** `colors.py`
- **Problem:** Not imported anywhere. It's LCD colour code from a Pimoroni example, with ~20 unused constants,
  an untyped function, CRLF endings, and a `randint` colour fallback that makes output non-deterministic.
- **Fix:** Delete it (preferred) or add the LCD feature properly with tests.
- **Done when:** the file is gone or has tests and a documented purpose.

### [x] P3-2 Rename `logging.py` `[code]`
- **Where:** `logging.py` and its imports
- **Problem:** A module named `logging` inside the package invites accidental shadowing of the stdlib module
  (for example when running `python src/enviroplussensorstomqtt/main.py` directly, or with odd `sys.path`).
- **Fix:** Rename to `log_setup.py`/`logsetup.py`; update imports.
- **Done when:** no module in the package is named like a stdlib module.

### [ ] P3-3 Missing sensor: LTR559 light/proximity `[code]`
- **Where:** `sensor.py`
- **Problem:** The Enviro+ includes an LTR559 (lux, proximity) that is never read, though the board is the
  project's namesake. This is an incomplete feature relative to "Enviroplus sensors to MQTT".
- **Fix:** Add optional `lux`/`proximity` fields (feature-flagged in config, tolerant of absence).
- **Done when:** unit tests with a fake `ltr559`; README documents fields.

### [ ] P3-4 MQTT features
- **Where:** `sensor.py`, new `mqtt.py`
- **Problem:** Only one JSON blob is published, retained, to every topic, with no TLS, client ID, QoS setting,
  availability topic, or Home-Assistant-style discovery. Retain is hardcoded.
- **Fix (each optional, config-driven):** `tls` (CA/cert/key, `tls_insecure` off by default), `client_id`,
  `qos`, `retain`, per-metric subtopics, availability + LWT (ties to P1-7), MQTT discovery payloads.
- **Done when:** each option has unit tests against a fake client and a README section.

### [ ] P3-5 Observability
- **Problem:** No way to tell if the service is healthy except tailing logs.
- **Fix:** Publish a small status message (uptime, last-success timestamp, sensor errors count); optionally
  `sd_notify` watchdog (`WatchdogSec=`) so systemd restarts a hung process.
- **Done when:** watchdog heartbeat is tested with a fake notifier.

### [ ] P3-6 Release and distribution
- **Problem:** Not published to PyPI; install is "clone + make". No versioned releases.
- **Fix:** Add a tag-triggered GitHub Actions release (build, `twine check`, publish with trusted publishing),
  or document that the project is source-install only.
- **Done when:** a tagged release produces a verified artifact.

---

## Suggested order of attack

1. P0-1, P0-2, P0-3 (small, isolated, high-value, easy to test)
2. P1-9 + P1-10 (testability refactor) -- unlocks safe changes for everything else
3. P0-4, P0-5, P0-6, P1-7 (reliability: error handling, lifecycle, MQTT, shutdown)
4. P1-1 (remove daemonizer; supersedes P0-7), P1-2, P1-3
5. P1-4, P1-5, P1-6 (payload and measurement quality)
6. P1-8, then P2-* (service unit, packaging, CI, docs)
7. P3-* as desired

## Verification notes (how these findings were established)

- Cloned `main` at `b58a5a3`; `ruff check .` passes; `pytest` passes (1 test) after `pip install -e .[tests]`.
- Reproduced by execution: P0-1 (`FileNotFoundError: Configuration file 'config.yaml' not found.`),
  P0-3 (`FileNotFoundError` for `/var/log/enviroplussensorstomqtt/...log` with `-D`), P0-2 (root logger has
  `handlers: []` in default mode), P2-1 (built wheel contains `tests/test_basic.py`).
- Items tagged `[code]` come from reading the source and were not run against real hardware; `[hw]` items
  need a Raspberry Pi with an Enviro+ to confirm behaviour.
