import select
import time

from evdev import InputDevice, ecodes as e
from PyQt6 import QtCore

from app.backends.factory import create_backend
from app.core.health import HealthTracker
from app.services.movement_processor import MovementProcessor

AXIS_MAP = {
    "REL_X": e.REL_X,
    "REL_Y": e.REL_Y,
}


class TreadmillWorker(QtCore.QThread):
    """QThread that reads treadmill mouse events and emits telemetry.

    Business logic (movement math) is delegated to MovementProcessor
    so it can be tested without evdev, Qt, or threading.
    """

    telemetry = QtCore.pyqtSignal(dict)
    status = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = dict(config)
        self.running = False
        self.mouse = None
        self.backend = None
        self.health = HealthTracker()
        self.processor = MovementProcessor(config)

    def update_config(self, config):
        self.config = dict(config)
        self.processor.update_config(config)
        if self.backend is not None:
            self.backend.config = dict(config)

    def stop(self):
        self.running = False

    def reset_health(self):
        self.health.reset()

    def run(self):
        try:
            self.running = True
            device_path = self.config.get("mouse_device", "")
            if not device_path:
                raise RuntimeError("No treadmill mouse selected.")

            self.mouse = InputDevice(device_path)
            self.backend = create_backend(self.config.get("output_mode", "uinput"))
            self.backend.start(self.config)
            self.status.emit(self._running_status())

            while self.running:
                raw_x, raw_y = self._read_raw_motion()
                movement, telemetry = self.processor.process(raw_x, raw_y, self.health)

                self.backend.send_movement(movement)
                self.telemetry.emit(telemetry)

                time.sleep(self._poll_interval())
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self._shutdown()

    def _read_raw_motion(self):
        raw_x = 0
        raw_y = 0
        readable, _, _ = select.select([self.mouse], [], [], self._poll_interval())

        if readable:
            axis_code = AXIS_MAP.get(self.config.get("axis", "REL_Y"), e.REL_Y)
            for event in self.mouse.read():
                if event.type != e.EV_REL:
                    continue
                if self.config.get("omnidirectional", False):
                    if event.code == e.REL_X:
                        raw_x += event.value
                    elif event.code == e.REL_Y:
                        raw_y += event.value
                elif event.code == axis_code:
                    raw_y += event.value

        deadzone = int(self.config.get("deadzone", 2))
        raw_x = 0 if abs(raw_x) <= deadzone else raw_x
        raw_y = 0 if abs(raw_y) <= deadzone else raw_y
        return raw_x, raw_y

    def _shutdown(self):
        try:
            if self.backend is not None:
                self.backend.stop()
        except Exception:
            pass

        try:
            if self.mouse is not None:
                self.mouse.close()
        except Exception:
            pass

        self.backend = None
        self.mouse = None
        self.status.emit("Stopped")

    def _running_status(self):
        mode = self.config.get("output_mode", "uinput")
        if mode == "steamvr":
            return f"Running: SteamVR UDP / {self.mouse.name}"
        return f"Running: Maratron Treadmill / {self.mouse.name}"

    def _poll_interval(self):
        return max(1, int(self.config.get("poll_interval_ms", 8))) / 1000.0
