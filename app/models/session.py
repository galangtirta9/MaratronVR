import dataclasses
import datetime as dt


@dataclasses.dataclass
class Session:
    name: str
    activity_type: str
    start_date_local: str
    elapsed_time: int
    distance_m: float
    calories: float
    average_speed_kmh: float
    description: str

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: data.get(k) for k in cls._fields()})

    def to_dict(self):
        return dataclasses.asdict(self)

    @staticmethod
    def _fields():
        return [
            "name", "activity_type", "start_date_local",
            "elapsed_time", "distance_m", "calories",
            "average_speed_kmh", "description",
        ]


def build_session_from_telemetry(
    session_start_time, last_telemetry, auto_detect_run_kmh=8.0
):
    """Create a Session from raw timing/telemetry data. Pure function."""
    if session_start_time is None or last_telemetry is None:
        return None

    ended = dt.datetime.now().replace(microsecond=0)
    elapsed = max(1, int((ended - session_start_time).total_seconds()))
    dm = float(last_telemetry.get("distance_m", 0.0))
    avg_speed = (dm / elapsed) * 3.6 if elapsed > 0 else 0.0
    atype = "Run" if avg_speed >= auto_detect_run_kmh else "Walk"

    return Session(
        name="Maratron Session",
        activity_type=atype,
        start_date_local=session_start_time.isoformat(),
        elapsed_time=elapsed,
        distance_m=dm,
        calories=float(last_telemetry.get("calories", 0.0)),
        average_speed_kmh=avg_speed,
        description="Manual treadmill session by MaratronVR.",
    )