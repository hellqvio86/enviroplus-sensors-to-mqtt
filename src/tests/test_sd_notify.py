"""Tests for systemd sd_notify implementation in enviroplussensorstomqtt."""

import os
from unittest.mock import MagicMock, patch

from enviroplussensorstomqtt.sd_notify import notify, notify_ready, notify_stopping, notify_watchdog


def test_notify_no_socket():
    with patch.dict(os.environ, {}, clear=True):
        assert notify("READY=1") is False


def test_notify_socket_send():
    mock_sock = MagicMock()
    with (
        patch.dict(os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify"}),
        patch("socket.socket", return_value=mock_sock),
    ):
        assert notify("READY=1") is True
        mock_sock.sendto.assert_called_once_with(b"READY=1", "/run/systemd/notify")
        mock_sock.close.assert_called_once()


def test_notify_abstract_socket():
    mock_sock = MagicMock()
    with (
        patch.dict(os.environ, {"NOTIFY_SOCKET": "@/run/systemd/notify"}),
        patch("socket.socket", return_value=mock_sock),
    ):
        assert notify("WATCHDOG=1") is True
        mock_sock.sendto.assert_called_once_with(b"WATCHDOG=1", "\0/run/systemd/notify")


def test_notify_helpers():
    mock_sock = MagicMock()
    with (
        patch.dict(os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify"}),
        patch("socket.socket", return_value=mock_sock),
    ):
        assert notify_ready() is True
        assert notify_watchdog() is True
        assert notify_stopping() is True

        calls = [call.args[0] for call in mock_sock.sendto.call_args_list]
        assert b"READY=1" in calls
        assert b"WATCHDOG=1" in calls
        assert b"STOPPING=1" in calls


def test_notify_socket_error():
    mock_sock = MagicMock()
    mock_sock.sendto.side_effect = OSError("Connection refused")
    with (
        patch.dict(os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify"}),
        patch("socket.socket", return_value=mock_sock),
    ):
        assert notify("READY=1") is False
