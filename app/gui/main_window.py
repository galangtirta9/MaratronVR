import copy

from PyQt6 import QtWidgets

from app.backends.uinput_backend import BUTTON_MAP
from app.core.calibration import CalibrationWorker
from app.core.device_scan import scan_pointer_devices
from app.core.driver_install import install_maratron_driver, uninstall_maratron_driver
from app.core.profiles import (
    DEFAULT_PROFILE,
    OUTPUT_STEAMVR,
    OUTPUT_UINPUT,
    load_data,
    make_profile_config,
    save_data,
)
from app.core.treadmill_reader import TreadmillWorker
from app.gui.curve_widget import CurveEditor


OUTPUT_LABELS = {
    OUTPUT_UINPUT: "UInput Gamepad",
    OUTPUT_STEAMVR: "SteamVR Driver",
}

STEAMVR_BUTTONS = {
    "Grip": "grip",
    "Trackpad click": "trackpad",
    "Application menu": "application_menu",
    "Trigger": "trigger",
    "Disabled": "disabled",
}


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.data = load_data()
        self.worker = None
        self.calibrator = None
        self.devices = []

        self.setWindowTitle("Maratron Treadmill")
        self.resize(580, 820)

        self.controller_label = QtWidgets.QLabel("Controller: Maratron Treadmill")

        self.output_mode_combo = QtWidgets.QComboBox()
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_UINPUT], OUTPUT_UINPUT)
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_STEAMVR], OUTPUT_STEAMVR)

        self.device_combo = QtWidgets.QComboBox()
        self.refresh_devices_button = QtWidgets.QPushButton("Refresh devices")

        self.profile_combo = QtWidgets.QComboBox()
        self.new_profile_button = QtWidgets.QPushButton("New")
        self.duplicate_profile_button = QtWidgets.QPushButton("Duplicate")
        self.delete_profile_button = QtWidgets.QPushButton("Delete")

        self.axis_combo = QtWidgets.QComboBox()
        self.axis_combo.addItems(["REL_Y", "REL_X"])

        self.omnidirectional_check = QtWidgets.QCheckBox("Omnidirectional / use REL_X + REL_Y")
        self.invert_check = QtWidgets.QCheckBox("Invert Y axis")

        self.deadzone_spin = QtWidgets.QSpinBox()
        self.deadzone_spin.setRange(0, 50)

        self.smoothing_spin = QtWidgets.QDoubleSpinBox()
        self.smoothing_spin.setRange(0.01, 1.0)
        self.smoothing_spin.setSingleStep(0.01)

        self.max_speed_spin = QtWidgets.QDoubleSpinBox()
        self.max_speed_spin.setRange(1.0, 200.0)
        self.max_speed_spin.setSingleStep(1.0)

        self.poll_spin = QtWidgets.QSpinBox()
        self.poll_spin.setRange(1, 50)

        self.auto_sprint_check = QtWidgets.QCheckBox("Auto sprint at max speed")

        self.sprint_threshold_spin = QtWidgets.QDoubleSpinBox()
        self.sprint_threshold_spin.setRange(0.1, 1.0)
        self.sprint_threshold_spin.setSingleStep(0.01)

        self.sprint_button_combo = QtWidgets.QComboBox()
        self.sprint_button_combo.addItems(BUTTON_MAP.keys())

        self.steamvr_sprint_button_combo = QtWidgets.QComboBox()
        for label, value in STEAMVR_BUTTONS.items():
            self.steamvr_sprint_button_combo.addItem(label, value)

        self.stride_spin = QtWidgets.QDoubleSpinBox()
        self.stride_spin.setRange(0.20, 1.50)
        self.stride_spin.setSingleStep(0.01)
        self.stride_spin.setSuffix(" m")

        self.weight_spin = QtWidgets.QDoubleSpinBox()
        self.weight_spin.setRange(20.0, 200.0)
        self.weight_spin.setSingleStep(0.5)
        self.weight_spin.setSuffix(" kg")

        self.calorie_factor_spin = QtWidgets.QDoubleSpinBox()
        self.calorie_factor_spin.setRange(0.1, 2.0)
        self.calorie_factor_spin.setSingleStep(0.05)

        self.curve_editor = CurveEditor()

        self.raw_label = QtWidgets.QLabel("Raw: 0")
        self.filtered_label = QtWidgets.QLabel("Filtered: 0")
        self.output_label = QtWidgets.QLabel("Joystick: 0")
        self.movement_label = QtWidgets.QLabel("Movement: x=0.00 y=0.00")
        self.sprint_label = QtWidgets.QLabel("Sprint: OFF")
        self.steps_label = QtWidgets.QLabel("Steps: 0")
        self.distance_label = QtWidgets.QLabel("Distance: 0 m")
        self.calories_label = QtWidgets.QLabel("Calories: 0 kcal")
        self.status_label = QtWidgets.QLabel("Stopped")

        self.speed_bar = QtWidgets.QProgressBar()
        self.speed_bar.setRange(0, 100)

        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.save_button = QtWidgets.QPushButton("Save")
        self.calibrate_button = QtWidgets.QPushButton("Auto calibrate")
        self.reset_health_button = QtWidgets.QPushButton("Reset health stats")
        self.install_driver_button = QtWidgets.QPushButton("Install SteamVR driver")
        self.uninstall_driver_button = QtWidgets.QPushButton("Uninstall SteamVR driver")

        self.build_layout()
        self.connect_signals()

        self.refresh_devices()
        self.refresh_profiles()
        self.load_profile_to_ui()

    def build_layout(self):
        profile_buttons = QtWidgets.QHBoxLayout()
        profile_buttons.addWidget(self.profile_combo)
        profile_buttons.addWidget(self.new_profile_button)
        profile_buttons.addWidget(self.duplicate_profile_button)
        profile_buttons.addWidget(self.delete_profile_button)

        device_layout = QtWidgets.QHBoxLayout()
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.refresh_devices_button)

        form = QtWidgets.QFormLayout()
        form.addRow("", self.controller_label)
        form.addRow("Output Mode", self.output_mode_combo)
        form.addRow("Treadmill mouse", device_layout)
        form.addRow("Profile", profile_buttons)
        form.addRow("Input axis", self.axis_combo)
        form.addRow("", self.omnidirectional_check)
        form.addRow("", self.invert_check)
        form.addRow("Deadzone", self.deadzone_spin)
        form.addRow("Smoothing", self.smoothing_spin)
        form.addRow("Max raw speed", self.max_speed_spin)
        form.addRow("Poll interval ms", self.poll_spin)
        form.addRow("", self.auto_sprint_check)
        form.addRow("Sprint threshold", self.sprint_threshold_spin)
        form.addRow("UInput sprint button", self.sprint_button_combo)
        form.addRow("SteamVR sprint button", self.steamvr_sprint_button_combo)
        form.addRow("Stride length", self.stride_spin)
        form.addRow("Weight", self.weight_spin)
        form.addRow("Calorie factor", self.calorie_factor_spin)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.calibrate_button)
        buttons.addWidget(self.save_button)

        steamvr_driver_buttons = QtWidgets.QHBoxLayout()
        steamvr_driver_buttons.addWidget(self.install_driver_button)
        steamvr_driver_buttons.addWidget(self.uninstall_driver_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(QtWidgets.QLabel("Response curve: left-click/add/drag, right-click/delete point"))
        layout.addWidget(self.curve_editor)
        layout.addWidget(self.speed_bar)
        layout.addWidget(self.raw_label)
        layout.addWidget(self.filtered_label)
        layout.addWidget(self.output_label)
        layout.addWidget(self.movement_label)
        layout.addWidget(self.sprint_label)
        layout.addWidget(self.steps_label)
        layout.addWidget(self.distance_label)
        layout.addWidget(self.calories_label)
        layout.addWidget(self.reset_health_button)
        layout.addWidget(self.status_label)
        layout.addLayout(steamvr_driver_buttons)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def connect_signals(self):
        self.refresh_devices_button.clicked.connect(self.refresh_devices)
        self.profile_combo.currentTextChanged.connect(self.on_profile_selected)
        self.new_profile_button.clicked.connect(self.new_profile)
        self.duplicate_profile_button.clicked.connect(self.duplicate_profile)
        self.delete_profile_button.clicked.connect(self.delete_profile)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.save_button.clicked.connect(self.save)
        self.calibrate_button.clicked.connect(self.auto_calibrate)
        self.reset_health_button.clicked.connect(self.reset_health)
        self.install_driver_button.clicked.connect(self.install_steamvr_driver)
        self.uninstall_driver_button.clicked.connect(self.uninstall_steamvr_driver)
        self.curve_editor.pointsChanged.connect(self.on_curve_changed)
        self.device_combo.currentIndexChanged.connect(self.on_config_changed)

        widgets = [
            self.output_mode_combo,
            self.axis_combo,
            self.omnidirectional_check,
            self.invert_check,
            self.deadzone_spin,
            self.smoothing_spin,
            self.max_speed_spin,
            self.poll_spin,
            self.auto_sprint_check,
            self.sprint_threshold_spin,
            self.sprint_button_combo,
            self.steamvr_sprint_button_combo,
            self.stride_spin,
            self.weight_spin,
            self.calorie_factor_spin,
        ]

        for widget in widgets:
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.on_config_changed)
            if hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self.on_config_changed)
            if hasattr(widget, "currentIndexChanged"):
                widget.currentIndexChanged.connect(self.on_config_changed)
            if hasattr(widget, "stateChanged"):
                widget.stateChanged.connect(self.on_config_changed)

        self.omnidirectional_check.stateChanged.connect(self.update_axis_controls)

    def current_profile_name(self):
        return self.profile_combo.currentText() or self.data["active_profile"]

    def current_profile(self):
        return self.data["profiles"][self.current_profile_name()]

    def refresh_profiles(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.data["profiles"].keys())
        self.profile_combo.setCurrentText(self.data["active_profile"])
        self.profile_combo.blockSignals(False)

    def refresh_devices(self):
        selected = self.data.get("selected_device_path", "")
        self.devices = scan_pointer_devices()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for dev in self.devices:
            self.device_combo.addItem(dev["label"], dev["path"])
        if selected:
            index = self.device_combo.findData(selected)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
        self.device_combo.blockSignals(False)

    def load_profile_to_ui(self):
        profile = self.data["profiles"][self.data["active_profile"]]
        health = profile.get("health", {})

        self.output_mode_combo.setCurrentIndex(self.output_mode_combo.findData(self.data.get("output_mode", OUTPUT_UINPUT)))
        self.axis_combo.setCurrentText(profile.get("axis", "REL_Y"))
        self.omnidirectional_check.setChecked(bool(profile.get("omnidirectional", False)))
        self.invert_check.setChecked(bool(profile.get("invert", True)))
        self.deadzone_spin.setValue(int(profile.get("deadzone", 2)))
        self.smoothing_spin.setValue(float(profile.get("smoothing", 0.25)))
        self.max_speed_spin.setValue(float(profile.get("max_raw_speed", 20.0)))
        self.poll_spin.setValue(int(profile.get("poll_interval_ms", 8)))
        self.auto_sprint_check.setChecked(bool(profile.get("auto_sprint", True)))
        self.sprint_threshold_spin.setValue(float(profile.get("sprint_threshold", 0.92)))
        self.sprint_button_combo.setCurrentText(profile.get("sprint_button", "BTN_THUMBL / L3"))
        self._set_combo_data(self.steamvr_sprint_button_combo, profile.get("steamvr_sprint_button", "grip"))
        self.stride_spin.setValue(float(health.get("stride_length_m", 0.72)))
        self.weight_spin.setValue(float(health.get("user_weight_kg", 55.0)))
        self.calorie_factor_spin.setValue(float(health.get("calorie_factor", 0.75)))
        self.curve_editor.set_points(profile.get("curve_points", DEFAULT_PROFILE["curve_points"]))
        self.update_axis_controls()

    def read_ui_to_profile(self):
        if self.device_combo.currentIndex() >= 0:
            self.data["selected_device_path"] = self.device_combo.currentData()

        self.data["output_mode"] = self.output_mode_combo.currentData() or OUTPUT_UINPUT
        name = self.current_profile_name()
        profile = self.data["profiles"][name]
        profile["axis"] = self.axis_combo.currentText()
        profile["omnidirectional"] = self.omnidirectional_check.isChecked()
        profile["invert"] = self.invert_check.isChecked()
        profile["deadzone"] = self.deadzone_spin.value()
        profile["smoothing"] = self.smoothing_spin.value()
        profile["max_raw_speed"] = self.max_speed_spin.value()
        profile["poll_interval_ms"] = self.poll_spin.value()
        profile["auto_sprint"] = self.auto_sprint_check.isChecked()
        profile["sprint_threshold"] = self.sprint_threshold_spin.value()
        profile["sprint_button"] = self.sprint_button_combo.currentText()
        profile["steamvr_sprint_button"] = self.steamvr_sprint_button_combo.currentData()
        profile["curve_points"] = self.curve_editor.get_points()
        profile["health"] = {
            "stride_length_m": self.stride_spin.value(),
            "user_weight_kg": self.weight_spin.value(),
            "calorie_factor": self.calorie_factor_spin.value(),
        }
        self.data["active_profile"] = name
        return profile

    def on_curve_changed(self, points):
        self.on_config_changed()

    def on_config_changed(self):
        if not self.profile_combo.currentText():
            return

        self.update_axis_controls()
        self.read_ui_to_profile()
        if self.worker is not None:
            self.worker.update_config(make_profile_config(self.data))

    def update_axis_controls(self):
        self.axis_combo.setEnabled(not self.omnidirectional_check.isChecked())

    def on_profile_selected(self, name):
        if not name:
            return
        self.data["active_profile"] = name
        self.load_profile_to_ui()
        self.on_config_changed()

    def new_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New profile", "Profile name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.data["profiles"]:
            QtWidgets.QMessageBox.warning(self, "Profile exists", "That profile already exists.")
            return

        self.data["profiles"][name] = copy.deepcopy(DEFAULT_PROFILE)
        self.data["active_profile"] = name
        self.refresh_profiles()
        self.load_profile_to_ui()
        self.save()

    def duplicate_profile(self):
        current = self.current_profile_name()
        name, ok = QtWidgets.QInputDialog.getText(self, "Duplicate profile", "New profile name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.data["profiles"]:
            QtWidgets.QMessageBox.warning(self, "Profile exists", "That profile already exists.")
            return

        self.data["profiles"][name] = copy.deepcopy(self.data["profiles"][current])
        self.data["active_profile"] = name
        self.refresh_profiles()
        self.load_profile_to_ui()
        self.save()

    def delete_profile(self):
        if len(self.data["profiles"]) <= 1:
            QtWidgets.QMessageBox.warning(self, "Cannot delete", "Keep at least one profile.")
            return

        name = self.current_profile_name()
        answer = QtWidgets.QMessageBox.question(self, "Delete profile", f"Delete profile '{name}'?")
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        del self.data["profiles"][name]
        self.data["active_profile"] = list(self.data["profiles"].keys())[0]
        self.refresh_profiles()
        self.load_profile_to_ui()
        self.save()

    def save(self):
        self.read_ui_to_profile()
        save_data(self.data)
        self.status_label.setText("Saved profiles.json")

    def start(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.save()
        self.worker = TreadmillWorker(make_profile_config(self.data))
        self.worker.telemetry.connect(self.update_telemetry)
        self.worker.status.connect(self.status_label.setText)
        self.worker.failed.connect(self.show_error)
        self.worker.start()

    def stop(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(1500)
            self.worker = None

    def auto_calibrate(self):
        self.stop()

        if self.device_combo.currentIndex() < 0:
            QtWidgets.QMessageBox.warning(self, "No device", "Select a treadmill mouse first.")
            return

        self.calibrator = CalibrationWorker(self.device_combo.currentData(), axis=self.axis_combo.currentText(), seconds=4)
        self.calibrator.status.connect(self.status_label.setText)
        self.calibrator.failed.connect(self.show_error)
        self.calibrator.done.connect(self.apply_calibration)
        self.calibrator.start()

    def apply_calibration(self, result):
        self.deadzone_spin.setValue(int(result["deadzone"]))
        self.max_speed_spin.setValue(float(result["max_raw_speed"]))
        self.status_label.setText(f"Calibration done: deadzone={result['deadzone']}, samples={result['sample_count']}")
        self.save()

    def reset_health(self):
        if self.worker is not None:
            self.worker.reset_health()

        self.steps_label.setText("Steps: 0")
        self.distance_label.setText("Distance: 0 m")
        self.calories_label.setText("Calories: 0 kcal")

    def install_steamvr_driver(self):
        try:
            install_maratron_driver()
        except Exception as exc:
            self.show_error(f"Failed to install SteamVR driver:\n{exc}")
            return

        self.status_label.setText("SteamVR driver installed. Restart SteamVR if it is already running.")

    def uninstall_steamvr_driver(self):
        try:
            uninstall_maratron_driver()
        except Exception as exc:
            self.show_error(f"Failed to uninstall SteamVR driver:\n{exc}")
            return

        self.status_label.setText("SteamVR driver uninstalled. Restart SteamVR if it is already running.")

    def show_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Maratron error", message)

    def update_telemetry(self, data):
        self.raw_label.setText(f"Raw: {data['raw']}")
        self.filtered_label.setText(f"Filtered: {data['filtered']:.2f}")
        self.output_label.setText(f"Joystick: {data['joy']}")
        self.movement_label.setText(f"Movement: x={data['move_x']:.2f} y={data['move_y']:.2f}")
        self.sprint_label.setText(f"Sprint: {'ON' if data['sprint'] else 'OFF'}")
        self.speed_bar.setValue(int(data["curved"] * 100))
        self.steps_label.setText(f"Steps: {data['steps']}")
        self.distance_label.setText(f"Distance: {data['distance_m']:.1f} m")
        self.calories_label.setText(f"Calories: {data['calories']:.1f} kcal")

    def closeEvent(self, event):
        self.stop()
        self.save()
        if self.output_mode_combo.currentData() == OUTPUT_UINPUT:
            try:
                uninstall_maratron_driver()
            except Exception:
                pass
        super().closeEvent(event)

    @staticmethod
    def _set_combo_data(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
