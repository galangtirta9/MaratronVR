#include <openvr_driver.h>
#include <cstring>
#include "maratron_server.h"
#include "watchdog.h"

#if defined(_WIN32)
#define HMD_DLL_EXPORT extern "C" __declspec(dllexport)
#elif defined(__GNUC__) || defined(COMPILER_GCC) || defined(__APPLE__)
#define HMD_DLL_EXPORT extern "C" __attribute__((visibility("default")))
#else
#error "Unsupported Platform."
#endif

static MaratronServer   g_server;
static MaratronWatchdog g_watchdog;

HMD_DLL_EXPORT void *HmdDriverFactory(const char *pInterfaceName, int *pReturnCode) {
    if (0 == strcmp(vr::IServerTrackedDeviceProvider_Version, pInterfaceName)) {
        return &g_server;
    }
    if (0 == strcmp(vr::IVRWatchdogProvider_Version, pInterfaceName)) {
        return &g_watchdog;
    }
    if (pReturnCode) *pReturnCode = vr::VRInitError_Init_InterfaceNotFound;
    return nullptr;
}
