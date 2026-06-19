import json
import logging
import socket

from .base import MovementBackend

LOGGER = logging.getLogger(__name__)


class HIDMaestroBackend(MovementBackend):
    """Sends movement data via UDP to MaratronBridge.exe (Windows only)."""

    def __init__(self):
        self.sock = None
        self.addr = ("127.0.0.1", 9003)

    def start(self, config):
        host = config.get("hidmaestro_host", "127.0.0.1")
        port = int(config.get("hidmaestro_port", 9003))
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        LOGGER.info("HIDMaestro backend started: %s:%s", host, port)

    def send_movement(self, movement):
        if self.sock is None:
            return

        payload = {
            "move_x": round(float(movement.get("move_x", 0.0)), 4),
            "move_y": round(float(movement.get("move_y", 0.0)), 4),
            "sprint": bool(movement.get("sprint", False)),
        }
        self.sock.sendto(json.dumps(payload).encode("utf-8"), self.addr)
        LOGGER.debug("HIDMaestro movement sent: %s", payload)

    def stop(self):
        if self.sock is not None:
            # Send a zero frame so the controller goes to neutral
            self.send_movement({"move_x": 0.0, "move_y": 0.0, "sprint": False})
            self.sock.close()
            self.sock = None
            LOGGER.info("HIDMaestro backend stopped")