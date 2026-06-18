from evdev import InputDevice, ecodes as e, list_devices


def device_supports_pointer_motion(device):
    rel = device.capabilities().get(e.EV_REL, [])
    codes = []

    for item in rel:
        codes.append(item[0] if isinstance(item, tuple) else item)

    return e.REL_X in codes or e.REL_Y in codes


def scan_pointer_devices():
    devices = []

    for path in list_devices():
        try:
            dev = InputDevice(path)
            if not device_supports_pointer_motion(dev):
                continue

            rel_names = []
            for item in dev.capabilities().get(e.EV_REL, []):
                code = item[0] if isinstance(item, tuple) else item
                if code == e.REL_X:
                    rel_names.append("REL_X")
                elif code == e.REL_Y:
                    rel_names.append("REL_Y")

            devices.append({
                "path": path,
                "name": dev.name,
                "phys": dev.phys or "",
                "uniq": dev.uniq or "",
                "rel_axes": rel_names,
                "label": f"{dev.name}  ({path})",
            })
        except Exception:
            continue

    devices.sort(key=lambda d: (d["name"].lower(), d["path"]))
    return devices