"""Systemd watchdog and notification protocol implementation."""

import logging
import os
import socket

LOGGER = logging.getLogger(__name__)


def notify(state: str) -> bool:
    """Send state notification string to systemd notify socket if NOTIFY_SOCKET is set.

    Args:
        state: Protocol message string, e.g., 'READY=1', 'WATCHDOG=1', 'STOPPING=1'.

    Returns:
        True if successfully sent, False otherwise.
    """
    socket_path = os.environ.get("NOTIFY_SOCKET")
    if not socket_path:
        return False

    if socket_path.startswith("@"):
        # Abstract socket namespace
        socket_path = "\0" + socket_path[1:]

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.sendto(state.encode("utf-8"), socket_path)
            return True
        finally:
            sock.close()
    except Exception as exc:
        LOGGER.debug("Failed to send notification %r to %s: %s", state, socket_path, exc)
        return False


def notify_ready() -> bool:
    """Notify systemd that the service has finished initialization and is ready."""
    return notify("READY=1")


def notify_watchdog() -> bool:
    """Send watchdog ping to systemd to keep watchdog timer refreshed."""
    return notify("WATCHDOG=1")


def notify_stopping() -> bool:
    """Notify systemd that the service is initiating a graceful shutdown."""
    return notify("STOPPING=1")
