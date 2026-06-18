import json
import logging
import socket

from .base import MovementBackend

LOGGER = logging.getLogger(__name__)


class SteamVRClient(MovementBackend):
    def __init__(self):
        self.sock = None
        self.addr = ("127.0.0.1", 9001)
        self.sprint_button = "grip"

    def start(self, config):
        steamvr = config.get("steamvr", {})
        host = steamvr.get("host", "127.0.0.1")
        port = int(steamvr.get("port", 9001))

        self.addr = (host, port)
        self.sprint_button = config.get("steamvr_sprint_button", "grip")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        LOGGER.info("SteamVR UDP backend started: %s:%s", host, port)

    def send_movement(self, movement):
        if self.sock is None:
            return

        payload = {
            "move_x": round(float(movement.get("move_x", 0.0)), 4),
            "move_y": round(float(movement.get("move_y", 0.0)), 4),
            "sprint": bool(movement.get("sprint", False)),
            "speed": round(float(movement.get("speed", 0.0)), 4),
            "sprint_button": self.sprint_button,
        }
        self.sock.sendto(json.dumps(payload).encode("utf-8"), self.addr)
        LOGGER.debug("SteamVR movement sent: %s", payload)

    def stop(self):
        if self.sock is not None:
            self.send_movement({"move_x": 0.0, "move_y": 0.0, "sprint": False, "speed": 0.0})
            self.sock.close()
            self.sock = None
            LOGGER.info("SteamVR UDP backend stopped")