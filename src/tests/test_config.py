"""Tests for configuration parsing."""

import pytest

from enviroplussensorstomqtt.config import get_default_config, parse_config


def test_parse_config_none_returns_defaults():
    """Test parse_config(None) returns defaults."""
    cfg = parse_config(None)
    defaults = get_default_config()
    assert cfg["debug"] == defaults["debug"]
    assert cfg["port"] == defaults["port"]
    assert cfg["log_file"] == defaults["log_file"]


def test_parse_config_valid_file(tmp_path):
    """Test parse_config with a valid YAML file."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("host: '10.0.0.1'\nport: 1883\ntopics: ['sensors/a']\n")

    cfg = parse_config(str(config_file))
    assert cfg["host"] == "10.0.0.1"
    assert cfg["port"] == 1883
    assert cfg["topics"] == ["sensors/a"]
    assert cfg["debug"] is False


def test_parse_config_missing_file_raises():
    """Test parse_config with missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_config("/nonexistent_path/config.yaml")
