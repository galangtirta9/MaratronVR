import datetime as dt


class SessionService:
    """Coordinates session lifecycle: start, stop, duration, finalization.

    Extracted from MainWindow._finalize_session so session aggregation
    is testable without Qt.
    """

    @staticmethod
    def finalize(data, session_start_time, last_telemetry):
        """Build a session record and append it to data["sessions"].

        Returns (session_dict, human_summary_line) or (None, None) if
        input is incomplete.
        """
        if session_start_time is None or last_telemetry is None:
            return None

        ended = dt.datetime.now().replace(microsecond=0)
        elapsed = max(1, int((ended - session_start_time).total_seconds()))
        dm = float(last_telemetry.get("distance_m", 0.0))
        avg = (dm / elapsed) * 3.6 if elapsed > 0 else 0.0
        thr = float(data.get("strava", {}).get("auto_detect_run_kmh", 8.0) or 8.0)
        activity_type = "Run" if avg >= thr else "Walk"

        session = {
            "name": "Maratron Session",
            "activity_type": activity_type,
            "start_date_local": session_start_time.isoformat(),
            "elapsed_time": elapsed,
            "distance_m": dm,
            "calories": float(last_telemetry.get("calories", 0.0)),
            "average_speed_kmh": avg,
            "description": "Manual treadmill session by MaratronVR.",
        }
        data.setdefault("sessions", [])
        data["sessions"].append(dict(session))

        summary = (
            f"{activity_type}  {dm:.1f}m  {avg:.2f}km/h  {elapsed}s"
        )
        strava_summary = (
            f"Strava ready: {activity_type}, {dm:.1f}m, {avg:.2f}km/h"
        )
        return session, summary, strava_summary