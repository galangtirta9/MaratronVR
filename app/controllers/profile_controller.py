import copy

from PyQt6 import QtCore, QtWidgets

from app.core.profiles import (
    DEFAULT_PROFILE,
    OUTPUT_UINPUT,
    make_profile_config,
    save_data,
)
from app.gui.confirm_modal import ConfirmModal

CUSTOM_DPI_VALUE = "custom"


class ProfileController:
    """Coordinates profile CRUD, UI ↔ data sync, and config propagation."""

    def __init__(
        self,
        data,
        profile_combo,
        new_profile_button,
        duplicate_profile_button,
        delete_profile_button,
        # Movement
        axis_combo,
        omnidirectional_check,
        invert_check,
        deadzone_spin,
        smoothing_spin,
        max_speed_spin,
        poll_spin,
        curve_editor,
        # Sprint
        auto_sprint_check,
        sprint_threshold_spin,
        sprint_button_combo,
        steamvr_sprint_button_combo,
        # Body
        height_spin,
        stride_estimate_label,
        weight_spin,
        age_spin,
        gender_combo,
        mouse_dpi_combo,
        custom_dpi_spin,
        polling_rate_spin,
        incline_spin,
        # Output / device
        output_mode_combo,
        device_combo,
        # Strava
        strava_client_id_edit,
        strava_client_secret_edit,
        strava_status_label,
        # Sensitivity
        sensitivity_slider,
        sensitivity_label,
        # UI state
        selected_profile_label,
        refresh_profiles_callback,
        load_profile_to_ui_callback,
        render_tiles_callback,
        update_header_callback,
        show_toast_callback,
        on_config_changed_callback,
    ):
        self._data = data
        self._profile_combo = profile_combo
        self._new_profile_button = new_profile_button
        self._duplicate_profile_button = duplicate_profile_button
        self._delete_profile_button = delete_profile_button

        self._axis_combo = axis_combo
        self._omnidirectional_check = omnidirectional_check
        self._invert_check = invert_check
        self._deadzone_spin = deadzone_spin
        self._smoothing_spin = smoothing_spin
        self._max_speed_spin = max_speed_spin
        self._poll_spin = poll_spin
        self._curve_editor = curve_editor

        self._auto_sprint_check = auto_sprint_check
        self._sprint_threshold_spin = sprint_threshold_spin
        self._sprint_button_combo = sprint_button_combo
        self._steamvr_sprint_button_combo = steamvr_sprint_button_combo

        self._height_spin = height_spin
        self._stride_estimate_label = stride_estimate_label
        self._weight_spin = weight_spin
        self._age_spin = age_spin
        self._gender_combo = gender_combo
        self._mouse_dpi_combo = mouse_dpi_combo
        self._custom_dpi_spin = custom_dpi_spin
        self._polling_rate_spin = polling_rate_spin
        self._incline_spin = incline_spin

        self._output_mode_combo = output_mode_combo
        self._device_combo = device_combo
        self._strava_client_id_edit = strava_client_id_edit
        self._strava_client_secret_edit = strava_client_secret_edit
        self._strava_status_label = strava_status_label

        self._sensitivity_slider = sensitivity_slider
        self._sensitivity_label = sensitivity_label
        self._selected_profile_label = selected_profile_label

        self._refresh_profiles = refresh_profiles_callback
        self._load_to_ui = load_profile_to_ui_callback
        self._render_tiles = render_tiles_callback
        self._update_header = update_header_callback
        self._show_toast = show_toast_callback
        self._on_config_changed = on_config_changed_callback

    # --- Public API ---

    def current_profile_name(self):
        return self._profile_combo.currentText() or self._data["active_profile"]

    def load_profile_to_ui(self):
        profile = self._data["profiles"][self._data["active_profile"]]
        health = profile.get("health", {})
        self._output_mode_combo.setCurrentIndex(
            self._output_mode_combo.findData(self._data.get("output_mode", OUTPUT_UINPUT))
        )
        self._axis_combo.setCurrentText(profile.get("axis", "REL_Y"))
        self._omnidirectional_check.setChecked(bool(profile.get("omnidirectional", False)))
        self._invert_check.setChecked(bool(profile.get("invert", True)))
        self._deadzone_spin.setValue(int(profile.get("deadzone", 2)))
        self._smoothing_spin.setValue(float(profile.get("smoothing", 0.25)))
        self._max_speed_spin.setValue(float(profile.get("max_raw_speed", 20.0)))
        self._poll_spin.setValue(int(profile.get("poll_interval_ms", 8)))
        self._auto_sprint_check.setChecked(bool(profile.get("auto_sprint", True)))
        self._sprint_threshold_spin.setValue(float(profile.get("sprint_threshold", 0.92)))
        self._sprint_button_combo.setCurrentText(profile.get("sprint_button", "BTN_THUMBL / L3"))
        self._set_combo_data(
            self._steamvr_sprint_button_combo,
            profile.get("steamvr_sprint_button", "grip"),
        )
        hc = float(health.get(
            "height_cm",
            self._height_from_stride(float(health.get("stride_length_m", 0.72))),
        ))
        self._height_spin.setValue(hc)
        self._weight_spin.setValue(float(health.get("user_weight_kg", 55.0)))
        self._age_spin.setValue(int(health.get("age_years", 30)))
        self._gender_combo.setCurrentText(health.get("gender", "unspecified"))
        self._set_dpi_value(float(health.get("mouse_dpi", 1600.0)))
        self._polling_rate_spin.setValue(float(health.get("polling_rate_hz", 1000.0)))
        self._incline_spin.setValue(float(health.get("incline_degrees", health.get("incline_percentage", 0.0))))
        self._curve_editor.set_points(profile.get("curve_points", DEFAULT_PROFILE["curve_points"]))
        strava = self._data.get("strava", {})
        self._strava_client_id_edit.setText(strava.get("client_id", ""))
        self._strava_client_secret_edit.setText(strava.get("client_secret", ""))
        sens = float(profile.get("sensitivity", 1.0))
        self._sensitivity_slider.setValue(int(sens * 100))
        self._sensitivity_label.setText(f"Sensitivity: {sens:.2f}x")
        self._selected_profile_label.setText(f"Profile: {self._data['active_profile']}")
        self._strava_status_label.setText(
            "Strava: Connected"
            if self._data.get("strava", {}).get("access_token")
            else "Strava: Not Connected"
        )

    def read_ui_to_profile(self):
        if self._device_combo.currentIndex() >= 0:
            self._data["selected_device_path"] = self._device_combo.currentData()
        self._data["output_mode"] = self._output_mode_combo.currentData() or OUTPUT_UINPUT
        self._data.setdefault("strava", {})
        self._data["strava"]["client_id"] = self._strava_client_id_edit.text().strip()
        self._data["strava"]["client_secret"] = self._strava_client_secret_edit.text().strip()
        name = self.current_profile_name()
        profile = self._data["profiles"][name]
        profile["axis"] = self._axis_combo.currentText()
        profile["omnidirectional"] = self._omnidirectional_check.isChecked()
        profile["invert"] = self._invert_check.isChecked()
        profile["deadzone"] = self._deadzone_spin.value()
        profile["smoothing"] = self._smoothing_spin.value()
        profile["max_raw_speed"] = self._max_speed_spin.value()
        profile["poll_interval_ms"] = self._poll_spin.value()
        profile["auto_sprint"] = self._auto_sprint_check.isChecked()
        profile["sprint_threshold"] = self._sprint_threshold_spin.value()
        profile["sensitivity"] = self._sensitivity_slider.value() / 100.0
        profile["sprint_button"] = self._sprint_button_combo.currentText()
        profile["steamvr_sprint_button"] = self._steamvr_sprint_button_combo.currentData()
        profile["curve_points"] = self._curve_editor.get_points()
        hc = self._height_spin.value()
        ex = profile.get("health", {})
        profile["health"] = {
            "height_cm": hc,
            "stride_length_m": self._stride_from_height(hc),
            "user_weight_kg": self._weight_spin.value(),
            "age_years": self._age_spin.value(),
            "gender": self._gender_combo.currentText(),
            "mouse_dpi": self._current_dpi_value(),
            "polling_rate_hz": self._polling_rate_spin.value(),
            "incline_degrees": self._incline_spin.value(),
            "manual_friction_multiplier": ex.get("manual_friction_multiplier", 1.0),
            "calorie_factor": ex.get("calorie_factor", 1.0),
        }
        self._data["active_profile"] = name
        return profile

    def on_profile_selected(self, name):
        if not name:
            return
        self._data["active_profile"] = name
        self._load_to_ui()
        self._update_header()
        self._render_tiles()
        self._on_config_changed()

    def new_profile(self, parent_widget):
        name, ok = QtWidgets.QInputDialog.getText(parent_widget, "New profile", "Name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self._data["profiles"]:
            QtWidgets.QMessageBox.warning(parent_widget, "Exists", "That profile already exists.")
            return
        self._data["profiles"][name] = copy.deepcopy(DEFAULT_PROFILE)
        self._data["active_profile"] = name
        self._refresh_profiles()
        self._load_to_ui()
        self._render_tiles()
        self._show_toast(f"Profile '{name}' created")

    def duplicate_profile(self, parent_widget):
        cur = self.current_profile_name()
        name, ok = QtWidgets.QInputDialog.getText(parent_widget, "Duplicate", "New name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self._data["profiles"]:
            QtWidgets.QMessageBox.warning(parent_widget, "Exists", "That profile already exists.")
            return
        self._data["profiles"][name] = copy.deepcopy(self._data["profiles"][cur])
        self._data["active_profile"] = name
        self._refresh_profiles()
        self._load_to_ui()
        self._render_tiles()
        self._show_toast(f"Profile '{name}' duplicated from '{cur}'")

    def delete_profile(self, parent_widget):
        if len(self._data["profiles"]) <= 1:
            QtWidgets.QMessageBox.warning(parent_widget, "Cannot delete", "Keep at least one profile.")
            return
        name = self.current_profile_name()
        modal = ConfirmModal(
            parent_widget,
            "Delete Profile",
            f"Delete profile '{name}'? This action cannot be undone.",
            confirm_text="Delete",
            cancel_text="Cancel",
            destructive=True,
        )
        if modal.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        del self._data["profiles"][name]
        self._data["active_profile"] = list(self._data["profiles"].keys())[0]
        self._refresh_profiles()
        self._load_to_ui()
        self._render_tiles()
        self._show_toast(f"Profile '{name}' deleted")

    def save(self):
        self.read_ui_to_profile()
        save_data(self._data)
        self._show_toast("Profile saved")

    def make_config(self):
        return make_profile_config(self._data)

    # --- DPI / stride helpers ---

    def _current_dpi_value(self):
        v = self._mouse_dpi_combo.currentData()
        return self._custom_dpi_spin.value() if v == CUSTOM_DPI_VALUE else float(v or 1600.0)

    def _set_dpi_value(self, dpi):
        idpi = int(round(dpi))
        idx = self._mouse_dpi_combo.findData(idpi)
        if idx >= 0:
            self._mouse_dpi_combo.setCurrentIndex(idx)
        else:
            ci = self._mouse_dpi_combo.findData(CUSTOM_DPI_VALUE)
            if ci >= 0:
                self._mouse_dpi_combo.setCurrentIndex(ci)
        self._custom_dpi_spin.setValue(float(dpi))

    @staticmethod
    def _stride_from_height(h):
        return max(0.1, float(h) * 0.415 / 100.0)

    @staticmethod
    def _height_from_stride(s):
        return max(80.0, min(230.0, float(s) * 100.0 / 0.415))

    @staticmethod
    def _set_combo_data(c, v):
        i = c.findData(v)
        if i >= 0:
            c.setCurrentIndex(i)