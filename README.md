# MaratronVR

**Turn any optical mouse treadmill into a VR locomotion controller.**

MaratronVR reads mouse movement from a manual/non-motorized treadmill, applies smoothing and response curves, and outputs it as a virtual gamepad — works with flat games (Linux UInput) and VR games (native SteamVR driver). Health metrics (distance, speed, calories) are tracked with optional Strava upload.

## Quick Start

### Linux

```bash
pip install PyQt6 evdev

# Run the GUI
python -m app
```

#### SteamVR driver (optional, for VR games)

```bash
cd backends/native-steamvr
cmake -B build && cmake --build build
cmake --install build --prefix ~/.local/share/Steam/steamapps/common/SteamVR
# Restart SteamVR
```

Or from the app menu: click **Install SteamVR Driver**.

### Windows (experimental)

```powershell
pip install PyQt6 evdev

# Build the C# bridge (requires .NET 8 SDK)
cd backends/MaratronBridge
dotnet build -c Release

# Start bridge first (run as admin on first launch for driver install)
.\bin\Release\net8.0\MaratronBridge.exe

# Run the GUI
python -m app
```

Select **HIDMaestro (Windows)** as output mode. The virtual controller will appear as "Maratron Treadmill" in games.

## Features

### Output Modes
| Mode | Platform | Use case |
|---|---|---|
| **UInput Gamepad** | Linux | Native Linux gamepad (no VR needed) |
| **SteamVR Driver** | Linux | SteamVR games — appears as a separate treadmill controller |
| **HIDMaestro (Windows)** | Windows | Windows gamepad via HIDMaestro virtual controller |

### Core
- Optical mouse sensor via `evdev` (Linux) or raw input (Windows — planned)
- Configurable deadzone, smoothing, and max speed
- Response curve editor with draggable spline points
- Omnidirectional mode (reads both REL_X and REL_Y)
- Sprint detection (auto or button mapping)

### Health & Fitness
- DPI-based distance calculation with calibration multiplier
- Real-time speed (km/h)
- MET-based calorie calculation with incline (degrees)
- Steps from height-derived stride length
- Strava OAuth2 integration with automatic activity type detection

### Configuration
- Per-game profiles (Alyx, Skyrim VR, etc.)
- DPI presets for common OEM mouse sensors
- JSON-based profile persistence

## Project Structure

```
app/
├── backends/           # Output backends (UInput, SteamVR, HIDMaestro)
├── core/               # Business logic (health, curves, calibration)
├── gui/                # PyQt6 UI (dashboard, settings, curve editor)
└── main.py             # Entry point

backends/
├── native-steamvr/     # C++ SteamVR driver source
└── MaratronBridge/     # C# HIDMaestro bridge for Windows

assets/
├── icon.svg            # App icon
└── icons/              # Settings sidebar icons
```

## Prerequisites

### Linux
- Python 3.10+
- `pip install PyQt6 evdev`
- For SteamVR driver: `cmake`, `g++`, SteamVR installed via Steam
- Optional: `psutil` for RAM/CPU info in System settings

### Windows
- Python 3.10+
- .NET 8 SDK (for building the C# bridge)
- `pip install PyQt6 evdev`
- HIDMaestro driver (auto-installed on first launch — admin required)

## Development

This project is in active development. See `docs/handoff.json` for the full architectural overview, confirmed working features, and pending tasks.

### Recent milestones
- ✅ UInput gamepad backend
- ✅ Native SteamVR driver (UDP pipeline)
- ✅ Omnidirectional movement mode
- ✅ Health tracking (DPI distance, MET calories, Strava upload)
- ✅ Dark Steam Big Picture-inspired UI theme
- ✅ Pill tab navigation, collapsible settings
- ✅ Windows port structure (HIDMaestro bridge + Python backend)

### Up next
- Figma-based UI redesign
- Multi-stage calibration wizard
- Windows port testing and release
- Custom SteamVR render model and icons

## License

MIT