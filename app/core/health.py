import time
import math


class HealthTracker:
    def __init__(self):
        self.steps = 0
        self.distance_m = 0.0
        self.calories = 0.0
        self.speed_kmh = 0.0
        self.last_distance_update = time.time()

    def reset(self):
        self.steps = 0
        self.distance_m = 0.0
        self.calories = 0.0
        self.speed_kmh = 0.0
        self.last_distance_update = time.time()

    def update(self, normalized_speed, config, raw_x=0, raw_y=0):
        now = time.time()
        dt = now - self.last_distance_update
        self.last_distance_update = now

        health = config.get("health", {})
        stride_length_m = max(0.1, float(health.get("stride_length_m", 0.72)))
        weight_kg = max(20.0, float(health.get("user_weight_kg", 55.0)))
        calorie_factor = max(0.1, float(health.get("calorie_factor", 1.0)))
        mouse_dpi = max(1.0, float(health.get("mouse_dpi", 1600.0)))
        incline_degrees = max(0.0, float(health.get("incline_degrees", health.get("incline_percentage", 0.0))))
        manual_friction_multiplier = max(0.1, float(health.get("manual_friction_multiplier", 1.0)))

        counts = math.hypot(float(raw_x), float(raw_y))
        meters_per_count = 0.0254 / mouse_dpi
        segment_distance_m = counts * meters_per_count

        self.distance_m += segment_distance_m
        self.speed_kmh = (segment_distance_m / dt) * 3.6 if dt > 0 else 0.0

        speed_mps = self.speed_kmh / 3.6
        walking_met = self._walking_met(speed_mps, incline_degrees)
        adjusted_met = walking_met * manual_friction_multiplier * calorie_factor
        self.calories += (adjusted_met * 3.5 * weight_kg / 200.0) * (dt / 60.0)

        self.steps = max(self.steps, int(self.distance_m / stride_length_m))

        return {
            "steps": self.steps,
            "distance_m": self.distance_m,
            "calories": self.calories,
            "speed_kmh": self.speed_kmh,
            "segment_distance_m": segment_distance_m,
            "met": adjusted_met,
        }

    @staticmethod
    def _walking_met(speed_mps, incline_degrees):
        speed_m_min = max(0.0, speed_mps) * 60.0
        grade = math.tan(math.radians(max(0.0, incline_degrees)))

        if speed_m_min <= 0.0:
            return 1.0

        vo2_ml_kg_min = 3.5 + (0.1 * speed_m_min) + (1.8 * speed_m_min * grade)
        return max(1.0, vo2_ml_kg_min / 3.5)