#ifndef MARATRON_WATCHDOG_H
#define MARATRON_WATCHDOG_H

#include <openvr_driver.h>

class MaratronWatchdog : public vr::IVRWatchdogProvider {
public:
    virtual vr::EVRInitError Init(vr::IVRDriverContext *pDriverContext) override;
    virtual void Cleanup() override;
};

#endif