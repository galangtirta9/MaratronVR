#include "maratron_device.h"
#include <cstdio>

MaratronDevice::MaratronDevice(UdpReceiver *receiver)
    : m_receiver(receiver) {}

MaratronDevice::~MaratronDevice() { Deactivate(); }

vr::EVRInitError MaratronDevice::Activate(vr::TrackedDeviceIndex_t unObjectId) {
    m_unObjectId = unObjectId;
    m_ulPropertyContainer = vr::VRProperties()->TrackedDeviceToPropertyContainer(m_unObjectId);

    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_ControllerType_String, "maratron_treadmill");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_RegisteredDeviceType_String, "maratron/maratron_treadmillMRTN001");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_ModelNumber_String, "Maratron Treadmill v1");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_ManufacturerName_String, "Maratron");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_SerialNumber_String, "MRTN001");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_TrackingSystemName_String, "lighthouse");
    vr::VRProperties()->SetInt32Property(m_ulPropertyContainer, vr::Prop_DeviceClass_Int32, vr::TrackedDeviceClass_Controller);
    vr::VRProperties()->SetInt32Property(m_ulPropertyContainer, vr::Prop_ControllerRoleHint_Int32, vr::TrackedControllerRole_Treadmill);
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_RenderModelName_String, "vr_controller_vive_1_5");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_InputProfilePath_String, "{maratron}/input/maratron_profile.json");
    vr::VRProperties()->SetStringProperty(m_ulPropertyContainer, vr::Prop_NamedIconPathDeviceReady_String, "{maratron}/resources/icon.svg");

    vr::VRProperties()->SetInt32Property(m_ulPropertyContainer, vr::Prop_Axis0Type_Int32, vr::k_eControllerAxis_Joystick);

    vr::EVRInputError err;

    err = vr::VRDriverInput()->CreateScalarComponent(
        m_ulPropertyContainer, "/input/joystick_left/x", &m_compX,
        vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided);
    std::fprintf(stderr, "[maratron] CreateScalarComponent joystick_left/x handle=%llu err=%d\n",
                 (unsigned long long)m_compX, err);

    err = vr::VRDriverInput()->CreateScalarComponent(
        m_ulPropertyContainer, "/input/joystick_left/y", &m_compY,
        vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided);
    std::fprintf(stderr, "[maratron] CreateScalarComponent joystick_left/y handle=%llu err=%d\n",
                 (unsigned long long)m_compY, err);

    err = vr::VRDriverInput()->CreateBooleanComponent(m_ulPropertyContainer, "/input/joystick_left/click", &m_compJoystickClick);
    std::fprintf(stderr, "[maratron] CreateBooleanComponent joystick_left/click handle=%llu err=%d\n",
                 (unsigned long long)m_compJoystickClick, err);

    err = vr::VRDriverInput()->CreateScalarComponent(
        m_ulPropertyContainer, "/input/trigger/value", &m_compTrigger,
        vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided);
    std::fprintf(stderr, "[maratron] CreateScalarComponent trigger handle=%llu err=%d\n",
                 (unsigned long long)m_compTrigger, err);

    err = vr::VRDriverInput()->CreateBooleanComponent(m_ulPropertyContainer, "/input/grip/click", &m_compSprint);
    std::fprintf(stderr, "[maratron] CreateBooleanComponent grip handle=%llu err=%d\n",
                 (unsigned long long)m_compSprint, err);

    err = vr::VRDriverInput()->CreateHapticComponent(m_ulPropertyContainer, "/output/haptic", &m_compHaptic);
    std::fprintf(stderr, "[maratron] CreateHapticComponent handle=%llu err=%d\n",
                 (unsigned long long)m_compHaptic, err);

    std::fprintf(stderr, "[maratron] Device activated successfully\n");
    return vr::VRInitError_None;
}

void MaratronDevice::Deactivate() {
    m_unObjectId = vr::k_unTrackedDeviceIndexInvalid;
}

void MaratronDevice::EnterStandby() {}
void *MaratronDevice::GetComponent(const char *) { return nullptr; }
void MaratronDevice::PowerOff() {}
void MaratronDevice::DebugRequest(const char *, char *, uint32_t) {}

vr::DriverPose_t MaratronDevice::GetPose() {
    vr::DriverPose_t pose{};
    pose.poseIsValid = true;
    pose.result = vr::TrackingResult_Running_OK;
    pose.deviceIsConnected = true;
    pose.qWorldFromDriverRotation = vr::HmdQuaternion_t{1,0,0,0};
    pose.qDriverFromHeadRotation = vr::HmdQuaternion_t{1,0,0,0};
    pose.qRotation = vr::HmdQuaternion_t{1,0,0,0};
    pose.vecPosition[0] = 0.0f;
    pose.vecPosition[1] = 0.0f;
    pose.vecPosition[2] = 0.0f;
    return pose;
}

void MaratronDevice::RunFrame() {
    if (m_receiver == nullptr) return;
    if (m_unObjectId == vr::k_unTrackedDeviceIndexInvalid) return;

    float x = m_receiver->move_x();
    float y = m_receiver->move_y();
    bool sprint = m_receiver->sprint();

    if (m_compX != vr::k_ulInvalidInputComponentHandle) {
        vr::EVRInputError e = vr::VRDriverInput()->UpdateScalarComponent(m_compX, x, 0);
        if (e != vr::VRInputError_None)
            std::fprintf(stderr, "[maratron] UpdateScalarComponent x FAILED err=%d\n", e);
    }

    if (m_compY != vr::k_ulInvalidInputComponentHandle) {
        vr::EVRInputError e = vr::VRDriverInput()->UpdateScalarComponent(m_compY, y, 0);
        if (e != vr::VRInputError_None)
            std::fprintf(stderr, "[maratron] UpdateScalarComponent y FAILED err=%d\n", e);
    }

    if (m_compSprint != vr::k_ulInvalidInputComponentHandle) {
        vr::VRDriverInput()->UpdateBooleanComponent(m_compSprint, sprint, 0);
    }

    if (m_compJoystickClick != vr::k_ulInvalidInputComponentHandle) {
        vr::VRDriverInput()->UpdateBooleanComponent(m_compJoystickClick, sprint, 0);
    }

    vr::VRServerDriverHost()->TrackedDevicePoseUpdated(
        m_unObjectId, GetPose(), sizeof(vr::DriverPose_t));
}