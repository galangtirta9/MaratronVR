#include "watchdog.h"
#include <chrono>
#include <thread>

vr::EVRInitError MaratronWatchdog::Init(vr::IVRDriverContext *pDriverContext) {
    VR_INIT_WATCHDOG_DRIVER_CONTEXT(pDriverContext);
    // No-op watchdog — we don't need to prevent SteamVR from sleeping
    return vr::VRInitError_None;
}

void MaratronWatchdog::Cleanup() {
}