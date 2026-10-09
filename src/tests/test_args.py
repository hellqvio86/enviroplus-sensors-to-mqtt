"""Tests for args parsing and configuration resolution."""

import pytest

from enviroplussensorstomqtt.args import args_handler


def test_args_handler_cli_only_without_config_file(monkeypatch, tmp_path):
    """Test CLI-only arguments work when no config.yaml exists (P0-1)."""
    # Change cwd to empty directory so no config.yaml exists
    monkeypatch.chdir(tmp_path)

    cli_args = [
        "--host", "mqtt.example.local",
        "--username", "user1",
        "--password", "secret",
        "--port", "1884",
        "--topics", "sensors/env, sensors/all",
    ]
    config = args_handler(cli_args)

    assert config["host"] == "mqtt.example.local"
    assert config["username"] == "user1"
    assert config["password"] == "secret"
    assert config["port"] == 1884
    assert config["topics"] == ["sensors/env", "sensors/all"]
    assert config["debug"] is False
    assert config["log_file"] is None


def test_args_handler_explicit_missing_config_file_raises(monkeypatch, tmp_path):
    """Test specifying a nonexistent --config_file raises FileNotFoundError (P0-1)."""
    monkeypatch.chdir(tmp_path)
    cli_args = ["--config_file", str(tmp_path / "nonexistent.yaml")]

    with pytest.raises(FileNotFoundError, match="nonexistent.yaml"):
        args_handler(cli_args)


def test_args_handler_debug_redacts_password(capsys, monkeypatch, tmp_path):
    """Test that debug dump does not print cleartext password."""
    monkeypatch.chdir(tmp_path)
    cli_args = [
        "--host", "localhost",
        "--password", "supersecretpassword",
        "-D",
    ]
    config = args_handler(cli_args)
    captured = capsys.readouterr()

    assert config["password"] == "supersecretpassword"
    assert "supersecretpassword" not in captured.out
    assert "***" in captured.out
