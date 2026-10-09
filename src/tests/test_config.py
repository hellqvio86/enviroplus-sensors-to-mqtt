"""Tests for configuration parsing and validation."""

import pytest

from enviroplussensorstomqtt.config import AppConfig, get_default_config, parse_config, validate_config


def test_parse_config_none_returns_defaults():
    """Test parse_config(None) returns defaults."""
    cfg = parse_config(None)
    defaults = get_default_config()
    assert cfg["debug"] == defaults["debug"]
    assert cfg["port"] == defaults["port"]
    assert cfg["log_file"] == defaults["log_file"]
    assert cfg["interval"] == 60.0
    assert cfg["measurements"] == 3
    assert cfg["temperature_offset"] == 0.0


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


@pytest.mark.parametrize(
    "topics_input, expected_topics",
    [
        (["sensors/enviro"], ["sensors/enviro"]),
        ("sensors/enviro, sensors/all", ["sensors/enviro", "sensors/all"]),
    ],
)
def test_validate_config_valid(topics_input, expected_topics):
    """Test valid configs create an AppConfig dataclass."""
    raw = {
        "host": "mqtt.local",
        "topics": topics_input,
        "port": 1883,
        "username": "user",
        "password": "pwd",
        "interval": 30,
        "measurements": 5,
        "temperature_offset": 2.5,
    }
    app_cfg = validate_config(raw)
    assert isinstance(app_cfg, AppConfig)
    assert app_cfg.host == "mqtt.local"
    assert app_cfg.topics == expected_topics
    assert app_cfg.port == 1883
    assert app_cfg.temperature_offset == 2.5


def test_validate_config_anonymous_broker_works():
    """Test anonymous broker (no username/password) is valid."""
    raw = {
        "host": "broker.hivemq.com",
        "topics": ["open/topic"],
    }
    app_cfg = validate_config(raw)
    assert app_cfg.username is None
    assert app_cfg.password is None


@pytest.mark.parametrize(
    "invalid_cfg, match_msg",
    [
        ({"host": "", "topics": ["a"]}, "'host' must be a non-empty string"),
        ({"host": "   ", "topics": ["a"]}, "'host' must be a non-empty string"),
        ({"host": "broker", "topics": []}, "'topics' must be a non-empty list"),
        ({"host": "broker", "topics": [""]}, "must be non-empty strings"),
        ({"host": "broker", "topics": ["a"], "port": 0}, "between 1 and 65535"),
        ({"host": "broker", "topics": ["a"], "port": 70000}, "between 1 and 65535"),
        ({"host": "broker", "topics": ["a"], "port": "invalid"}, "'port' must be an integer"),
        ({"host": "broker", "topics": ["a"], "interval": -5}, "'interval' must be a positive number"),
        ({"host": "broker", "topics": ["a"], "measurements": 0}, "'measurements' must be a positive integer"),
    ],
)
def test_validate_config_failures(invalid_cfg, match_msg):
    """Test invalid configurations fail fast with clear errors."""
    with pytest.raises(ValueError, match=match_msg):
        validate_config(invalid_cfg)
