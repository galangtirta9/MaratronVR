import time


class HealthTracker:
    def __init__(self):
        self.steps = 0
        self.distance_m = 0.0
        self.calories = 0.0
        self.last_distance_update = time.time()

    def reset(self):
        self.steps = 0
        self.distance_m = 0.0
        self.calories = 0.0
        self.last_distance_update = time.time()

    def update(self, normalized_speed, config):
        now = time.time()
        dt = now - self.last_distance_update
        self.last_distance_update = now

        health = config.get("health", {})
        stride_length_m = max(0.1, float(health.get("stride_length_m", 0.72)))
        weight_kg = max(20.0, float(health.get("user_weight_kg", 55.0)))
        calorie_factor = max(0.1, float(health.get("calorie_factor", 0.75)))

        speed_mps = normalized_speed * 1.6
        self.distance_m += speed_mps * dt
        self.steps = max(self.steps, int(self.distance_m / stride_length_m))
        self.calories = weight_kg * (self.distance_m / 1000.0) * calorie_factor

        return {
            "steps": self.steps,
            "distance_m": self.distance_m,
            "calories": self.calories,
        }