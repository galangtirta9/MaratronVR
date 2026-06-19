from app.core.profiles import OUTPUT_HIDMAESTRO, OUTPUT_STEAMVR, OUTPUT_UINPUT

from .hidmaestro_backend import HIDMaestroBackend
from .steamvr_client import SteamVRClient
from .uinput_backend import UInputBackend


def create_backend(output_mode):
    if output_mode == OUTPUT_STEAMVR:
        return SteamVRClient()
    if output_mode == OUTPUT_UINPUT:
        return UInputBackend()
    if output_mode == OUTPUT_HIDMAESTRO:
        return HIDMaestroBackend()
    raise ValueError(f"Unsupported output mode: {output_mode}")
