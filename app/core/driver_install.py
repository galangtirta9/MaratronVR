import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEAMVR_ROOT = Path.home() / ".local/share/Steam/steamapps/common/SteamVR"
DRIVER_SOURCE = PROJECT_ROOT / "backends" / "native-steamvr"
DRIVER_BUILD = PROJECT_ROOT / "backends" / "native-steamvr-build"
DRIVER_INSTALL = STEAMVR_ROOT / "drivers" / "maratron"


def is_driver_installed():
    return DRIVER_INSTALL.exists()


def install_maratron_driver():
    if not DRIVER_SOURCE.exists():
        raise RuntimeError(f"SteamVR driver source not found: {DRIVER_SOURCE}")

    subprocess.run(
        ["cmake", "-S", str(DRIVER_SOURCE), "-B", str(DRIVER_BUILD)],
        check=True,
        cwd=PROJECT_ROOT,
    )
    subprocess.run(
        ["cmake", "--build", str(DRIVER_BUILD), f"-j{_cpu_count()}"],
        check=True,
        cwd=PROJECT_ROOT,
    )
    subprocess.run(
        ["cmake", "--install", str(DRIVER_BUILD), "--prefix", str(STEAMVR_ROOT)],
        check=True,
        cwd=PROJECT_ROOT,
    )


def uninstall_maratron_driver():
    if DRIVER_INSTALL.exists():
        shutil.rmtree(DRIVER_INSTALL)


def _cpu_count():
    try:
        return str(len(__import__("os").sched_getaffinity(0)))
    except Exception:
        return "1"