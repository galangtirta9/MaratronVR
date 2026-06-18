# Maratron Cline Rules

## Project Identity

Maratron is a Linux-first VR treadmill locomotion project.

It converts real treadmill belt movement, detected by an optical mouse, into virtual movement input for games.

The app must support two output modes:

1. **UInput Gamepad Mode**

   * Python backend.
   * Uses evdev/uinput.
   * Already proven to work with Steam.
   * Intended for Skyrim VR, Half-Life Alyx, Fallout VR, and games that accept gamepad movement.

2. **SteamVR Driver Mode**

   * C++ backend.
   * Based on `r57zone/OpenVR-driver-for-DIY`.
   * Intended for games that require VR controller thumbstick locomotion, such as Boneworks or Bonelab.

## Core Rule

Do not duplicate treadmill logic per backend.

The shared core must produce neutral movement data:

```json
{
  "move_y": 0.0,
  "sprint": false,
  "speed": 0.0
}
```

Backends only decide how to output that data.

## Current Working Features

Preserve these features from the existing Python prototype:

* Mouse device detection through evdev.
* Human-readable mouse dropdown.
* Fixed controller name: `Maratron Treadmill`.
* UInput virtual controller.
* Response curve editor.
* Auto sprint threshold.
* Profiles, default profile: `Alyx`.
* Auto calibration.
* Health stats:

  * steps,
  * distance,
  * calories estimate.

Do not break working UInput mode while adding SteamVR mode.

## Recommended Structure

```text
Maratron/
├─ app/
│  ├─ main.py
│  ├─ core/
│  │  ├─ treadmill_reader.py
│  │  ├─ curve.py
│  │  ├─ calibration.py
│  │  ├─ profiles.py
│  │  └─ health.py
│  ├─ gui/
│  │  ├─ main_window.py
│  │  └─ curve_widget.py
│  └─ backends/
│     ├─ uinput_backend.py
│     └─ steamvr_client.py
├─ backends/
│  └─ steamvr/
│     └─ OpenVR-driver-for-DIY fork
├─ assets/
│  ├─ icon.png
│  └─ logo.png
├─ docs/
└─ .clinerules.md
```

## Python Rules

Use Python for:

* GUI.
* Mouse reading.
* Calibration.
* Profiles.
* Curve processing.
* Health stats.
* UInput backend.
* Sending movement data to SteamVR backend.

Prefer PyQt6 for GUI.

Avoid overengineering. Keep the app runnable from source.

## SteamVR Rules

Use C++ only for the SteamVR driver/backend.

Do not attempt to rewrite the full Python app in C++.

The first SteamVR goal is minimal:

* receive `move_y`,
* receive `sprint`,
* apply forward/back movement or thumbstick-like locomotion,
* test in SteamVR.

Use localhost UDP or a simple socket for communication:

```json
{
  "move_y": 0.75,
  "sprint": true
}
```

Do not focus on logos, icons, or render models until movement works.

## Backend Selection

The GUI must include:

```text
Output Mode:
[ UInput Gamepad ]
[ SteamVR Driver ]
```

When UInput mode is selected:

* Create virtual Linux controller named `Maratron Treadmill`.

When SteamVR mode is selected:

* Do not create uinput device.
* Send movement data to the SteamVR backend.

## Branding

The app name is Maratron.

The controller/device name should be:

```text
Maratron Treadmill
```

Do not expose an option to rename it in the normal GUI.

SteamVR branding/icon can be changed later after the SteamVR backend works.

## Safety

This software controls in-game locomotion from a real treadmill.

Always provide:

* Stop button.
* Reset output to zero on stop.
* Sprint release on stop.
* No movement output when input device is missing.
* Deadzone to prevent drift.
* Calibration before use.

## Development Priority

1. Keep UInput mode working.
2. Refactor into clean core/backend architecture.
3. Add backend selector.
4. Add dummy SteamVR output logger.
5. Clone and build OpenVR-driver-for-DIY.
6. Connect Python to SteamVR driver.
7. Test basic movement.
8. Polish branding and SteamVR icon later.
