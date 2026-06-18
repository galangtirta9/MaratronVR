from evdev import AbsInfo, UInput, ecodes as e

from .base import MovementBackend


BUTTON_MAP = {
    "Disabled": None,
    "BTN_THUMBL / L3": e.BTN_THUMBL,
    "BTN_THUMBR / R3": e.BTN_THUMBR,
    "BTN_TL / LB": e.BTN_TL,
    "BTN_TR / RB": e.BTN_TR,
    "BTN_SOUTH / A": e.BTN_SOUTH,
    "BTN_EAST / B": e.BTN_EAST,
    "BTN_WEST / X": e.BTN_WEST,
    "BTN_NORTH / Y": e.BTN_NORTH,
}


def abs_axis(min_value=-32768, max_value=32767):
    return AbsInfo(
        value=0,
        min=min_value,
        max=max_value,
        fuzz=0,
        flat=0,
        resolution=0,
    )


class UInputBackend(MovementBackend):
    def __init__(self):
        self.pad = None
        self.config = {}
        self.sprint_on = False

    def start(self, config):
        self.config = dict(config)
        self.pad = self._create_gamepad()

    def send_movement(self, movement):
        if self.pad is None:
            return

        joy_x = self._to_abs(movement.get("move_x", 0.0))
        joy_y = self._to_abs(movement.get("move_y", 0.0))

        self.pad.write(e.EV_ABS, e.ABS_X, joy_x)
        self.pad.write(e.EV_ABS, e.ABS_Y, joy_y)
        self.pad.syn()

        self._emit_sprint(bool(movement.get("sprint", False)))

    def stop(self):
        try:
            self._emit_sprint(False)
            if self.pad is not None:
                self.pad.write(e.EV_ABS, e.ABS_X, 0)
                self.pad.write(e.EV_ABS, e.ABS_Y, 0)
                self.pad.syn()
                self.pad.close()
        finally:
            self.pad = None
            self.sprint_on = False

    def _create_gamepad(self):
        sprint_code = BUTTON_MAP.get(self.config.get("sprint_button"))
        keys = [
            e.BTN_SOUTH,
            e.BTN_EAST,
            e.BTN_WEST,
            e.BTN_NORTH,
            e.BTN_TL,
            e.BTN_TR,
            e.BTN_SELECT,
            e.BTN_START,
            e.BTN_THUMBL,
            e.BTN_THUMBR,
        ]

        if sprint_code and sprint_code not in keys:
            keys.append(sprint_code)

        capabilities = {
            e.EV_KEY: keys,
            e.EV_ABS: {
                e.ABS_X: abs_axis(),
                e.ABS_Y: abs_axis(),
                e.ABS_RX: abs_axis(),
                e.ABS_RY: abs_axis(),
            },
        }

        name = self.config.get("controller_name", "Maratron Treadmill")
        return UInput(capabilities, name=name, version=0x3)

    def _emit_sprint(self, enabled):
        button_code = BUTTON_MAP.get(self.config.get("sprint_button", "BTN_THUMBL / L3"))

        if button_code is None or self.pad is None:
            self.sprint_on = False
            return

        if enabled != self.sprint_on:
            self.pad.write(e.EV_KEY, button_code, 1 if enabled else 0)
            self.pad.syn()
            self.sprint_on = enabled

    @staticmethod
    def _to_abs(value):
        value = max(-1.0, min(1.0, float(value)))
        return max(-32768, min(32767, int(value * 32767)))