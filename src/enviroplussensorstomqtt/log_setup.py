"""Logging setup module."""

import logging
import logging.handlers


def setup_logger(
    *,
    debug: bool = False,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure root logger with console and optional rotating file handler."""
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s"
    )

    # Always attach a console handler so stdout/stderr (and systemd journald) captures logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)

    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(log_file, "a", maxBytes=3 * 10**6, backupCount=10)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Failed to initialize log file '%s': %s. Continuing with console logging.", log_file, exc)

    return root
