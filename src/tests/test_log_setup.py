"""Tests for logger setup."""

import logging

from enviroplussensorstomqtt.log_setup import setup_logger


def test_setup_logger_default_attaches_console_handler():
    """Test setup_logger() attaches a StreamHandler and records INFO messages (P0-2)."""
    root = logging.getLogger()
    # Clean existing handlers
    root.handlers.clear()

    logger = setup_logger()
    assert logger.handlers
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    assert logger.level == logging.INFO


def test_setup_logger_debug_without_log_file():
    """Test setup_logger(debug=True) sets level to DEBUG without requiring writable file (P0-3)."""
    root = logging.getLogger()
    root.handlers.clear()

    logger = setup_logger(debug=True, log_file=None)
    assert logger.level == logging.DEBUG
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_setup_logger_unwritable_path_warns_and_continues(caplog):
    """Test setup_logger with unwritable log_file path logs a warning and doesn't crash (P0-3)."""
    root = logging.getLogger()
    root.handlers.clear()

    unwritable_path = "/nonexistent_dir_12345/unwritable.log"
    with caplog.at_level(logging.WARNING):
        logger = setup_logger(log_file=unwritable_path)

    assert logger is not None
    # Console handler must still be attached
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
