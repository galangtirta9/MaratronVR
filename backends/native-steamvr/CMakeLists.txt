cmake_minimum_required(VERSION 3.10)
project(driver_maratron VERSION 1.0.0)

include_directories(OpenVR/headers)

set(TARGET_NAME driver_maratron)

add_library(${TARGET_NAME} MODULE
  driver_main.cpp
  maratron_server.cpp
  maratron_server.h
  maratron_device.cpp
  maratron_device.h
  udp_receiver.cpp
  udp_receiver.h
  watchdog.cpp
  watchdog.h
)

SET_TARGET_PROPERTIES(${TARGET_NAME} PROPERTIES PREFIX "")

target_link_libraries(${TARGET_NAME}
  ${CMAKE_DL_LIBS}
  pthread
)

if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(PREFIX "win")
else()
    set(PREFIX "linux")
endif()

if(CMAKE_SIZEOF_VOID_P STREQUAL "8")
    set(ARCH 64)
else()
    set(ARCH 64)
endif()

install(TARGETS ${TARGET_NAME}
    RUNTIME DESTINATION drivers/maratron/bin/${PREFIX}${ARCH}
    LIBRARY DESTINATION drivers/maratron/bin/${PREFIX}${ARCH}
)

install(FILES driver.vrdrivermanifest DESTINATION drivers/maratron)
install(FILES resources/settings/default.vrsettings DESTINATION drivers/maratron/resources/settings)
install(FILES resources/input/maratron_profile.json DESTINATION drivers/maratron/resources/input)
install(FILES resources/input/legacy_bindings_vive_controller.json DESTINATION drivers/maratron/resources/input)
install(FILES resources/icon.svg DESTINATION drivers/maratron/resources)
