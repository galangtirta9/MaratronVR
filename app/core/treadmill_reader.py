import select
import time

from evdev import InputDevice, ecodes as e
from PyQt6 import QtCore

from app.backends.factory import create_backend
from app.core.curve import apply_curve, normalize_curve_points
from app.core.health import HealthTracker

AXIS_MAP = {
    "REL_X": e.REL_X,
    "REL_Y": e.REL_Y,
}


class TreadmillWorker(QtCore.QThread):
    telemetry = QtCore.pyqtSignal(dict)
    status = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = dict(config)
        self.running = False
        self.mouse = None
        self.backend = None
        self.filtered = 0.0
        self.filtered_x = 0.0
        self.filtered_y = 0.0
        self.health = HealthTracker()

    def update_config(self, config):
        self.config = dict(config)
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
                movement, telemetry = self._process_motion(raw_x, raw_y)

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

    def _process_motion(self, raw_x, raw_y):
        smoothing = max(0.01, min(1.0, float(self.config.get("smoothing", 0.25))))
        self.filtered_x = (self.filtered_x * (1.0 - smoothing)) + (raw_x * smoothing)
        self.filtered_y = (self.filtered_y * (1.0 - smoothing)) + (raw_y * smoothing)
        self.filtered = self.filtered_y

        max_raw_speed = max(1.0, float(self.config.get("max_raw_speed", 20.0)))
        points = normalize_curve_points(self.config.get("curve_points", []))

        move_x, normalized_x, curved_x = self._process_axis(self.filtered_x, max_raw_speed, points, invert=False)
        move_y, normalized_y, curved_y = self._process_axis(
            self.filtered_y,
            max_raw_speed,
            points,
            invert=bool(self.config.get("invert", True)),
        )

        normalized = max(normalized_x, normalized_y)
        curved = max(curved_x, curved_y)

        sprint_threshold = float(self.config.get("sprint_threshold", 0.92))
        sprint_active = (
            bool(self.config.get("auto_sprint", True))
            and curved >= sprint_threshold
            and (abs(move_x) > 0.0 or abs(move_y) > 0.0)
        )

        movement = {
            "move_x": move_x,
            "move_y": move_y,
            "sprint": sprint_active,
            "speed": curved,
        }
        health = self.health.update(normalized, self.config, raw_x=raw_x, raw_y=raw_y)

        telemetry = {
            "raw": raw_y,
            "raw_x": raw_x,
            "raw_y": raw_y,
            "filtered": self.filtered,
            "filtered_x": self.filtered_x,
            "filtered_y": self.filtered_y,
            "normalized": normalized,
            "curved": curved,
            "joy": int(move_y * 32767),
            "move_x": movement["move_x"],
            "move_y": movement["move_y"],
            "sprint": sprint_active,
            **health,
        }
        return movement, telemetry

    @staticmethod
    def _process_axis(filtered, max_raw_speed, points, invert=False):
        normalized = min(1.0, abs(filtered) / max_raw_speed)
        curved = apply_curve(normalized, points)
        sign = -1 if filtered < 0 else 1
        move = curved * sign
        if invert:
            move = -move
        return max(-1.0, min(1.0, move)), normalized, curved

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