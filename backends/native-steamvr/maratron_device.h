#ifndef MARATRON_DEVICE_H
#define MARATRON_DEVICE_H

#include <openvr_driver.h>
#include "udp_receiver.h"

class MaratronDevice : public vr::ITrackedDeviceServerDriver {
public:
    MaratronDevice(UdpReceiver *receiver);
    ~MaratronDevice();

    virtual vr::EVRInitError Activate(vr::TrackedDeviceIndex_t unObjectId) override;
    virtual void Deactivate() override;
    virtual void EnterStandby() override;
    virtual void *GetComponent(const char *pchComponentNameAndVersion) override;
    virtual void PowerOff();
    virtual void DebugRequest(const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize) override;
    virtual vr::DriverPose_t GetPose() override;

    void RunFrame();

    std::string GetSerialNumber() const { return "MRTN001"; }

private:
    vr::TrackedDeviceIndex_t m_unObjectId = vr::k_unTrackedDeviceIndexInvalid;
    vr::PropertyContainerHandle_t m_ulPropertyContainer = vr::k_ulInvalidPropertyContainer;
    vr::VRInputComponentHandle_t m_compX = vr::k_ulInvalidInputComponentHandle;
    vr::VRInputComponentHandle_t m_compY = vr::k_ulInvalidInputComponentHandle;
    vr::VRInputComponentHandle_t m_compJoystickClick = vr::k_ulInvalidInputComponentHandle;
    vr::VRInputComponentHandle_t m_compTrigger = vr::k_ulInvalidInputComponentHandle;
    vr::VRInputComponentHandle_t m_compSprint = vr::k_ulInvalidInputComponentHandle;
    vr::VRInputComponentHandle_t m_compHaptic = vr::k_ulInvalidInputComponentHandle;
    UdpReceiver *m_receiver;
};

#endif