from app.core.profiles import OUTPUT_STEAMVR, OUTPUT_UINPUT

from .steamvr_client import SteamVRClient
from .uinput_backend import UInputBackend


def create_backend(output_mode):
    if output_mode == OUTPUT_STEAMVR:
        return SteamVRClient()
    if output_mode == OUTPUT_UINPUT:
        return UInputBackend()
    raise ValueError(f"Unsupported output mode: {output_mode}")