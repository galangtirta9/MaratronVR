import copy
import json
from pathlib import Path

CONTROLLER_NAME = "Maratron Treadmill"
OUTPUT_UINPUT = "uinput"
OUTPUT_STEAMVR = "steamvr"

APP_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = APP_DIR / "profiles.json"
LEGACY_PROFILE_PATH = APP_DIR.parent / "core" / "uinput" / "profiles.json"

DEFAULT_PROFILE = {
    "axis": "REL_Y",
    "omnidirectional": False,
    "invert": True,
    "deadzone": 2,
    "smoothing": 0.25,
    "max_raw_speed": 20.0,
    "poll_interval_ms": 8,
    "auto_sprint": True,
    "sprint_threshold": 0.92,
    "sprint_button": "BTN_THUMBL / L3",
    "steamvr_sprint_button": "grip",
    "curve_points": [
        [0.0, 0.0],
        [0.25, 0.12],
        [0.50, 0.25],
        [0.75, 0.55],
        [1.0, 1.0],
    ],
    "health": {
        "stride_length_m": 0.72,
        "user_weight_kg": 55.0,
        "calorie_factor": 0.75,
    },
}

DEFAULT_DATA = {
    "active_profile": "Alyx",
    "profiles": {"Alyx": copy.deepcopy(DEFAULT_PROFILE)},
    "selected_device_path": "",
    "output_mode": OUTPUT_UINPUT,
    "steamvr": {"host": "127.0.0.1", "port": 9001},
}


def load_data():
    if not PROFILE_PATH.exists():
        source = LEGACY_PROFILE_PATH if LEGACY_PROFILE_PATH.exists() else None
        data = _read_json(source) if source else copy.deepcopy(DEFAULT_DATA)
        data = normalize_data(data)
        save_data(data)
        return data

    return normalize_data(_read_json(PROFILE_PATH))


def save_data(data):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PROFILE_PATH.open("w", encoding="utf-8") as file:
        json.dump(normalize_data(data), file, indent=2)


def normalize_data(data):
    data = copy.deepcopy(data)

    data.setdefault("profiles", {})
    if not data["profiles"]:
        data["profiles"]["Alyx"] = copy.deepcopy(DEFAULT_PROFILE)

    if data.get("active_profile") not in data["profiles"]:
        data["active_profile"] = list(data["profiles"].keys())[0]

    data.setdefault("selected_device_path", "")
    data.setdefault("output_mode", OUTPUT_UINPUT)
    data.setdefault("steamvr", {})
    data["steamvr"].setdefault("host", "127.0.0.1")
    data["steamvr"].setdefault("port", 9001)

    for name, profile in list(data["profiles"].items()):
        merged = copy.deepcopy(DEFAULT_PROFILE)
        merged.update(profile)
        merged["health"] = {
            **DEFAULT_PROFILE["health"],
            **profile.get("health", {}),
        }
        data["profiles"][name] = merged

    return data


def get_active_profile(data):
    return data["profiles"][data["active_profile"]]


def make_profile_config(data):
    normalized = normalize_data(data)
    profile = copy.deepcopy(get_active_profile(normalized))
    profile["mouse_device"] = normalized.get("selected_device_path", "")
    profile["controller_name"] = CONTROLLER_NAME
    profile["output_mode"] = normalized.get("output_mode", OUTPUT_UINPUT)
    profile["steamvr"] = normalized.get("steamvr", {"host": "127.0.0.1", "port": 9001})
    return profile


def _read_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)