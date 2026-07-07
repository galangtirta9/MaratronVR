from app.core.curve import apply_curve, normalize_curve_points


class MovementProcessor:
    """Pure business logic: processes raw mouse motion into joystick output.

    Extracted from TreadmillWorker._process_motion so movement math is
    testable without Qt, evdev, or threading.
    """

    def __init__(self, config):
        self.config = dict(config)
        self.filtered = 0.0
        self.filtered_x = 0.0
        self.filtered_y = 0.0

    def update_config(self, config):
        self.config = dict(config)

    def process(self, raw_x, raw_y, health_tracker):
        smoothing = max(0.01, min(1.0, float(self.config.get("smoothing", 0.25))))
        self.filtered_x = (self.filtered_x * (1.0 - smoothing)) + (raw_x * smoothing)
        self.filtered_y = (self.filtered_y * (1.0 - smoothing)) + (raw_y * smoothing)
        self.filtered = self.filtered_y

        max_raw_speed = max(1.0, float(self.config.get("max_raw_speed", 20.0)))
        points = normalize_curve_points(self.config.get("curve_points", []))

        move_x, normalized_x, curved_x = self._process_axis(
            self.filtered_x, max_raw_speed, points, invert=False
        )
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

        sensitivity = max(0.1, min(3.0, float(self.config.get("sensitivity", 1.0))))
        move_x = max(-1.0, min(1.0, move_x * sensitivity))
        move_y = max(-1.0, min(1.0, move_y * sensitivity))

        movement = {
            "move_x": move_x,
            "move_y": move_y,
            "sprint": sprint_active,
            "speed": curved,
        }
        health = health_tracker.update(normalized, self.config, raw_x=raw_x, raw_y=raw_y)

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