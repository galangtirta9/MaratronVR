import select
import time

from evdev import InputDevice, ecodes as e
from PyQt6 import QtCore

from app.core.treadmill_reader import AXIS_MAP


class CalibrationWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(dict)
    status = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, device_path, axis="REL_Y", seconds=4):
        super().__init__()
        self.device_path = device_path
        self.axis = axis
        self.seconds = seconds
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        try:
            if not self.device_path:
                raise RuntimeError("No treadmill mouse selected.")

            mouse = InputDevice(self.device_path)
            axis_code = AXIS_MAP.get(self.axis, e.REL_Y)
            samples = []
            start = time.time()

            self.status.emit("Calibrating... keep the treadmill still.")

            while self.running and (time.time() - start) < self.seconds:
                readable, _, _ = select.select([mouse], [], [], 0.02)
                if readable:
                    for event in mouse.read():
                        if event.type == e.EV_REL and event.code == axis_code:
                            samples.append(abs(event.value))

            mouse.close()
            self.done.emit(self._result(samples))
        except Exception as exc:
            self.failed.emit(str(exc))

    @staticmethod
    def _result(samples):
        if not samples:
            return {
                "deadzone": 2,
                "max_raw_speed": 20.0,
                "sample_count": 0,
                "max_noise": 0,
            }

        max_noise = max(samples)
        return {
            "deadzone": max(2, int(max_noise) + 2),
            "max_raw_speed": 20.0,
            "sample_count": len(samples),
            "max_noise": max_noise,
            "avg_noise": sum(samples) / len(samples),
        }