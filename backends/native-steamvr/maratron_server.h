#ifndef MARATRON_SERVER_H
#define MARATRON_SERVER_H

#include <openvr_driver.h>
#include "udp_receiver.h"
#include "maratron_device.h"

class MaratronServer : public vr::IServerTrackedDeviceProvider {
public:
    virtual vr::EVRInitError Init(vr::IVRDriverContext *pDriverContext) override;
    virtual void Cleanup() override;
    virtual const char *const *GetInterfaceVersions() override { return vr::k_InterfaceVersions; }
    virtual void RunFrame() override;
    virtual bool ShouldBlockStandbyMode() override { return false; }
    virtual void EnterStandby() override {}
    virtual void LeaveStandby() override {}

private:
    UdpReceiver m_receiver;
    MaratronDevice *m_device = nullptr;
};

#endif