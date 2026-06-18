#include "maratron_server.h"

#include <cstdio>

vr::EVRInitError MaratronServer::Init(vr::IVRDriverContext *pDriverContext) {
    VR_INIT_SERVER_DRIVER_CONTEXT(pDriverContext);
    std::fprintf(stderr, "[maratron] Init\n");

    // Start UDP receiver on default port 9001
    m_receiver.start(9001);

    // Create and register the device
    m_device = new MaratronDevice(&m_receiver);
    std::fprintf(stderr, "[maratron] Registering device sn=%s\n",
                 m_device->GetSerialNumber().c_str());

    bool added = vr::VRServerDriverHost()->TrackedDeviceAdded(
        m_device->GetSerialNumber().c_str(),
        vr::TrackedDeviceClass_Controller,
        m_device);

    std::fprintf(stderr, "[maratron] TrackedDeviceAdded returned %d (1=accepted)\n", added);

    return vr::VRInitError_None;
}

void MaratronServer::Cleanup() {
    std::fprintf(stderr, "[maratron] Cleanup\n");
    m_receiver.stop();
    delete m_device;
    m_device = nullptr;
}

void MaratronServer::RunFrame() {
    if (m_device) {
        m_device->RunFrame();
    }
}