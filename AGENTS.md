# AGENTS.md

Guidance for AI coding agents working in this repository. Humans: see `README.md`.
Open work items live in `todo.md` (prioritised, with acceptance criteria). Start there.

## What this project is

`enviroplussensorstomqtt` is a small Python service that runs on a Raspberry Pi with a
Pimoroni **Enviro+** board (and optional PMS5003 particle sensor). Once per cycle (~60 s) it
reads sensors, takes the median of a few samples, and publishes **one JSON object** to one or
more MQTT topics (retained).

- Sensors: BME280 (temperature, humidity, pressure), MEMS microphone (noise profile),
  MICS6814 (gas: oxidising, reducing, NH3), PMS5003 (PM1, PM2.5, PM10).
- Runs as a long-lived process, normally under systemd.
- Status: alpha (`0.0.x`). Interfaces (CLI flags, config keys, JSON payload) are not yet
  stable, but treat them as public until `todo.md` says otherwise. Do not rename keys casually.

## Repository layout

```
src/enviroplussensorstomqtt/
  main.py        entry point `main()`; the forever-loop (read -> publish -> sleep)
  args.py        argparse + config-file resolution + CLI overrides  -> returns a plain dict
  config.py      YAML loading and defaults
  sensor.py      hardware reads + MQTT publish (currently one big function)
  logging.py     logger setup (NOTE: name shadows stdlib `logging` for relative imports only)
  daemonizer.py  hand-rolled double-fork daemon + pidfile (legacy; see todo.md)
  colors.py      unused LCD colour helpers (dead code; see todo.md)
src/tests/       pytest tests (currently one import smoke test)
systemd/         unit file installed by `make install-service`
Makefile         install / test / clean / install-service
pyproject.toml   setuptools build, ruff config, console script `enviroplussensorstomqtt`
uv.lock          lockfile (the Makefile does NOT currently install from it)
.github/         CI (`make test` on Python 3.11) and Dependabot (uv ecosystem)
```

## Commands

Always run these before declaring a task done:

```bash
make install            # creates .venv (uv, --system-site-packages) and installs -e .[tests] + ruff
make test               # = uv run ruff check . && uv run pytest src/tests/
```

Faster inner loop once installed:

```bash
uv run ruff check .
uv run ruff check . --fix       # import sorting etc.
uv run pytest src/tests/ -q
```

Run the app (needs a Pi with the hardware; will fail elsewhere):

```bash
uv run enviroplussensorstomqtt --config_file ./config.yaml -D
```

Requires Python >= 3.11 and `paho-mqtt` >= 2.0 (code uses `mqtt.CallbackAPIVersion.VERSION2`).

## Environment constraints you must respect

- **No hardware in the sandbox.** Never write tests or scripts that touch `/dev/i2c-*`,
  serial ports, GPIO, or the microphone. Fake or mock `SMBus`, `BME280`, `gas`, `Noise`,
  `PMS5003`, and the MQTT client. Importing the package works on a dev machine only because
  the Pimoroni libs happen to install on Linux; do not rely on that for new code paths.
- **No network/broker in tests.** Use a fake MQTT client object, not a real broker.
- **Raspberry Pi targets** may run Raspberry Pi OS Bookworm (Python 3.11) with
  `--system-site-packages` venvs and piwheels. Do not add dependencies that need a compiler
  or heavy native libs without a strong reason (this is a Pi Zero-class workload).
- The service currently runs as **root** under systemd. Do not add code that assumes root, and
  do not widen privileges.

## Code conventions

- Formatting/lint: `ruff`, line length 120, rules `E,F,W,I`, target `py311`. Keep
  `ruff check .` clean. Do not disable rules to get green; fix the code.
- Add type hints to new/changed functions. Prefer `str | None` over `x: str = None`.
- Use `logging` via a module-level `LOGGER = logging.getLogger(__name__)`. Use lazy
  formatting (`LOGGER.info("x %s", y)`) in new code. Never use `print` for operational output.
- Keep functions small and pure where possible: separate *reading hardware*, *building the
  payload*, and *publishing*. This is the main testability goal (see `todo.md`).
- Use timezone-aware datetimes (`datetime.now(datetime.UTC)`), not `utcnow()`.
- Match the surrounding docstring style in files you edit; add a short docstring to every
  new public function.
- Commit messages: Conventional Commits (`fix:`, `feat:`, `chore:`, `test:`, `docs:`,
  `refactor:`), one logical change per commit.

## Things that will bite you

1. **Secrets.** Never log, print, or echo the MQTT password or the full config dict. Do not
   add example configs containing real credentials. Prefer env vars / file-based secrets in new code.
2. **Payload compatibility.** The JSON keys (`temperature`, `humidity`, `pressure`, `noise_*`,
   `gas_*`, `pm1`, `pm25`, `pm10`, `time_utc`, `unit_of_*`) are consumed downstream. Changing,
   renaming, or removing a key is a breaking change: call it out explicitly and update the README.
3. **Blocking loop.** Sensor reads use `sleep(1)` between samples; one cycle takes tens of
   seconds. Do not introduce unbounded retries that can starve the 60 s cadence.
4. **Resource lifetime.** Hardware handles and the MQTT client are currently created every
   cycle. Any change here must ensure handles are closed/released; do not add new per-cycle
   allocations that are never freed.
5. **Daemon mode is legacy.** `--daemon`/`daemonizer.py` duplicates what systemd does and has
   known bugs. Do not extend it; fix or remove it only as described in `todo.md`.
6. **Do not edit `uv.lock` by hand.** Use `uv lock` / `uv add` / `uv remove`.
7. **CRLF.** `colors.py` and the systemd unit contain CRLF line endings. Do not produce
   mixed line endings; normalise whole files when touching them.
8. Test files live in `src/tests/` and currently get packaged into the wheel (see `todo.md`).
   If you move tests, update the Makefile and CI paths together.

## Working agreement for agents

- Pick the highest-priority unchecked item in `todo.md` unless told otherwise. Do one item
  per change set. Tick its checkbox and note the commit in the same PR.
- Every bug fix needs a regression test that fails before and passes after.
- Do not make drive-by refactors outside the item's scope; add a new item to `todo.md` instead.
- If a task needs real hardware to verify, say so in the PR description and list exactly what a
  human must check on a Pi. Do not claim hardware behaviour you could not observe.
- If an instruction here conflicts with an explicit user request, follow the user and flag the conflict.

## Definition of done

- [ ] `make test` passes (ruff + pytest) from a clean `make clean && make install`
- [ ] New/changed behaviour has unit tests that run without hardware or network
- [ ] No secrets in logs, tests, fixtures, or docs
- [ ] README / `todo.md` updated if CLI flags, config keys, payload, or install steps changed
- [ ] No new unpinned or undeclared dependencies
