import copy
import datetime as dt
import webbrowser
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

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
from app.core.strava_client import build_authorization_url, exchange_code, upload_activity
from app.core.treadmill_reader import TreadmillWorker
from app.gui.curve_widget import CurveEditor
from app.gui.treadmill_widget import TreadmillWidget


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

DPI_PRESETS = [800, 1000, 1200, 1600, 2000, 2400, 3200, 4000, 4800, 6400, 8000]
CUSTOM_DPI_VALUE = "custom"


class CollapsibleSection(QtWidgets.QWidget):
    """A clickable header that toggles visibility of its content panel."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._collapsed = True
        self._content = QtWidgets.QWidget()
        self._content.setVisible(False)

        self._header = QtWidgets.QPushButton(f"\u25b8 {title}")
        self._header.setObjectName("section_header")
        self._header.setStyleSheet(
            "QPushButton#section_header {"
            "  background-color: #1a1a1a; border: 1px solid #2a2a2a;"
            "  border-radius: 6px; padding: 8px 12px; font-size: 13px;"
            "  font-weight: 600; text-align: left; color: #b0b0b0;"
            "}"
            "QPushButton#section_header:hover { border-color: #4a4a4a; }"
        )
        self._header.clicked.connect(self._toggle)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self._header)
        vbox.addWidget(self._content)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        arrow = "\u25be" if not self._collapsed else "\u25b8"
        base = self._header.text().lstrip("\u25b8\u25be ")
        self._header.setText(f"{arrow} {base}")

    def content(self):
        return self._content


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.data = load_data()
        self.worker = None
        self.calibrator = None
        self.devices = []
        self.session_start_time = None
        self.last_telemetry = None
        self.last_session = None
        self.session_elapsed_seconds = 0

        self.setWindowTitle("MaratronVR Controller Settings")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 640)

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

        # --- Settings section widgets ---
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

        # --- Calibration & Health section widgets ---
        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(80.0, 230.0)
        self.height_spin.setSingleStep(0.5)
        self.height_spin.setSuffix(" cm")

        self.stride_estimate_label = QtWidgets.QLabel("Estimated stride: 0.72 m")

        self.weight_spin = QtWidgets.QDoubleSpinBox()
        self.weight_spin.setRange(20.0, 200.0)
        self.weight_spin.setSingleStep(0.5)
        self.weight_spin.setSuffix(" kg")

        self.age_spin = QtWidgets.QSpinBox()
        self.age_spin.setRange(1, 120)

        self.gender_combo = QtWidgets.QComboBox()
        self.gender_combo.addItems(["unspecified", "female", "male"])

        self.mouse_dpi_combo = QtWidgets.QComboBox()
        for dpi in DPI_PRESETS:
            self.mouse_dpi_combo.addItem(f"{dpi} DPI", dpi)
        self.mouse_dpi_combo.addItem("Custom", CUSTOM_DPI_VALUE)

        self.custom_dpi_spin = QtWidgets.QDoubleSpinBox()
        self.custom_dpi_spin.setRange(1.0, 30000.0)
        self.custom_dpi_spin.setSingleStep(100.0)
        self.custom_dpi_spin.setSuffix(" DPI")

        self.polling_rate_spin = QtWidgets.QDoubleSpinBox()
        self.polling_rate_spin.setRange(1.0, 8000.0)
        self.polling_rate_spin.setSingleStep(125.0)
        self.polling_rate_spin.setSuffix(" Hz")

        self.incline_spin = QtWidgets.QDoubleSpinBox()
        self.incline_spin.setRange(0.0, 25.0)
        self.incline_spin.setSingleStep(0.5)
        self.incline_spin.setSuffix("\u00b0")

        self.curve_editor = CurveEditor()

        # --- Telemetry labels ---
        self.raw_label = QtWidgets.QLabel("Raw: 0")
        self.filtered_label = QtWidgets.QLabel("Filtered: 0")
        self.output_label = QtWidgets.QLabel("Joystick: 0")
        self.movement_label = QtWidgets.QLabel("Movement: x=0.00 y=0.00")
        self.sprint_label = QtWidgets.QLabel("Sprint: OFF")
        self.sprint_state_label = QtWidgets.QLabel("Sprint: OFF")
        self.session_state_label = QtWidgets.QLabel("Ready")
        self.selected_profile_label = QtWidgets.QLabel("Profile: Default")
        self.duration_label = QtWidgets.QLabel("Duration: 00:00:00")
        self.sensor_status_label = QtWidgets.QLabel("Sensor: Not Selected")
        self.joystick_status_label = QtWidgets.QLabel("Virtual Joystick: Idle")
        self.steamvr_status_label = QtWidgets.QLabel("SteamVR: Idle")
        self.strava_status_label = QtWidgets.QLabel("Strava: Not Connected")
        self.last_session_label = QtWidgets.QLabel("No completed session yet")
        self.total_stats_label = QtWidgets.QLabel("Totals will appear after sessions")
        self.treadmill_visual = TreadmillWidget()
        self.steps_label = QtWidgets.QLabel("Steps: 0")
        self.speed_label = QtWidgets.QLabel("Speed: 0.00 km/h")
        self.distance_label = QtWidgets.QLabel("Distance: 0 m")
        self.calories_label = QtWidgets.QLabel("Calories: 0 kcal")
        self.met_label = QtWidgets.QLabel("MET: 0.00")
        self.status_label = QtWidgets.QLabel("Stopped")
        self.clock_label = QtWidgets.QLabel()
        self.clock_timer = QtCore.QTimer(self)
        self.session_timer = QtCore.QTimer(self)

        self.speed_bar = QtWidgets.QProgressBar()
        self.speed_bar.setRange(0, 100)
        self.menu_button = QtWidgets.QPushButton("Settings")
        self.menu_button.setObjectName("menu_button")

        # --- Action buttons ---
        self.start_button = QtWidgets.QPushButton("  Start")
        self.start_button.setObjectName("start_button")
        self.stop_button = QtWidgets.QPushButton("  Stop")
        self.stop_button.setObjectName("stop_button")
        self.save_button = QtWidgets.QPushButton("Save")
        self.calibrate_button = QtWidgets.QPushButton("Auto calibrate")
        self.reset_health_button = QtWidgets.QPushButton("Reset health stats")
        self.install_driver_button = QtWidgets.QPushButton("Install SteamVR driver")
        self.install_driver_button.setObjectName("install_driver_button")
        self.uninstall_driver_button = QtWidgets.QPushButton("Uninstall SteamVR driver")

        # --- Strava widgets ---
        self.strava_client_id_edit = QtWidgets.QLineEdit()
        self.strava_client_secret_edit = QtWidgets.QLineEdit()
        self.strava_client_secret_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.strava_code_edit = QtWidgets.QLineEdit()
        self.strava_authorize_button = QtWidgets.QPushButton("Authorize Strava")
        self.strava_authorize_button.setObjectName("strava_authorize_button")
        self.strava_exchange_button = QtWidgets.QPushButton("Save Strava code")
        self.strava_upload_button = QtWidgets.QPushButton("Upload last session")
        self.strava_upload_button.setObjectName("strava_upload_button")

        self.build_layout()
        self.connect_signals()
        self.update_clock()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(30_000)
        self.session_timer.timeout.connect(self.update_session_duration)

        self.refresh_devices()
        self.refresh_profiles()
        self.load_profile_to_ui()

    def build_layout(self):
        self.controller_label.setText("MARATRON")
        self.controller_label.setObjectName("app_title")
        self.status_label.setObjectName("status_badge")
        self.clock_label.setObjectName("top_hint")
        self.session_state_label.setObjectName("hero_state")

        profile_row = QtWidgets.QHBoxLayout()
        profile_row.setSpacing(12)
        profile_row.addWidget(self.profile_combo, 1)
        profile_row.addWidget(self.new_profile_button)
        profile_row.addWidget(self.duplicate_profile_button)
        profile_row.addWidget(self.delete_profile_button)

        device_row = QtWidgets.QHBoxLayout()
        device_row.setSpacing(12)
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.refresh_devices_button)

        settings_form = QtWidgets.QFormLayout()
        settings_form.setSpacing(14)
        settings_form.addRow("Input axis", self.axis_combo)
        settings_form.addRow("", self.omnidirectional_check)
        settings_form.addRow("", self.invert_check)
        settings_form.addRow("Deadzone", self.deadzone_spin)
        settings_form.addRow("Smoothing", self.smoothing_spin)
        settings_form.addRow("Max raw speed", self.max_speed_spin)
        settings_form.addRow("Poll interval ms", self.poll_spin)

        sprint_form = QtWidgets.QFormLayout()
        sprint_form.setSpacing(14)
        sprint_form.addRow("", self.auto_sprint_check)
        sprint_form.addRow("Sprint threshold", self.sprint_threshold_spin)
        sprint_form.addRow("UInput sprint button", self.sprint_button_combo)
        sprint_form.addRow("SteamVR sprint button", self.steamvr_sprint_button_combo)

        health_form = QtWidgets.QFormLayout()
        health_form.setSpacing(14)
        health_form.addRow("Height", self.height_spin)
        health_form.addRow("", self.stride_estimate_label)
        health_form.addRow("Weight", self.weight_spin)
        health_form.addRow("Age", self.age_spin)
        health_form.addRow("Gender", self.gender_combo)
        health_form.addRow("Mouse DPI preset", self.mouse_dpi_combo)
        health_form.addRow("Custom DPI", self.custom_dpi_spin)
        health_form.addRow("Sensor polling rate", self.polling_rate_spin)
        health_form.addRow("Incline", self.incline_spin)

        strava_form = QtWidgets.QFormLayout()
        strava_form.setSpacing(14)
        strava_form.addRow("Strava client ID", self.strava_client_id_edit)
        strava_form.addRow("Strava client secret", self.strava_client_secret_edit)
        strava_form.addRow("Strava auth code", self.strava_code_edit)
        strava_buttons = QtWidgets.QHBoxLayout()
        strava_buttons.setSpacing(12)
        strava_buttons.addWidget(self.strava_authorize_button)
        strava_buttons.addWidget(self.strava_exchange_button)
        strava_buttons.addWidget(self.strava_upload_button)

        steamvr_driver_row = QtWidgets.QHBoxLayout()
        steamvr_driver_row.setSpacing(12)
        steamvr_driver_row.addWidget(self.install_driver_button)
        steamvr_driver_row.addWidget(self.uninstall_driver_button)

        dashboard = self._make_page()
        dashboard_layout = dashboard.widget().layout()
        dashboard_layout.setContentsMargins(92, 28, 92, 38)
        dashboard_layout.setSpacing(18)

        hero_row = QtWidgets.QHBoxLayout()
        hero_row.setSpacing(22)
        visual_card = self._card("TREADMILL", "Live speed and output are shown directly in the treadmill visual.")
        visual_card.setObjectName("dashboard_visual_card")
        visual_card.layout().addWidget(self.treadmill_visual, 1)
        hero_row.addWidget(visual_card, 7)

        action_card = self._card("SESSION", "Ready in two seconds: choose profile and start.")
        action_card.setObjectName("dashboard_action_card")
        action_card.layout().addWidget(self.session_state_label)
        action_card.layout().addWidget(self.selected_profile_label)
        action_card.layout().addSpacing(8)
        self.start_button.setText("Start Session")
        self.stop_button.setText("Stop Session")
        action_card.layout().addWidget(self.start_button)
        action_card.layout().addWidget(self.stop_button)
        action_card.layout().addStretch(1)
        hero_row.addWidget(action_card, 4)
        dashboard_layout.addLayout(hero_row)

        stat_grid = QtWidgets.QGridLayout()
        stat_grid.setHorizontalSpacing(14)
        stat_grid.setVerticalSpacing(14)
        for index, widget in enumerate([self.speed_label, self.distance_label, self.calories_label, self.duration_label]):
            stat_grid.addWidget(self._stat_tile(widget), 0, index)
        dashboard_layout.addLayout(stat_grid)

        status_grid = QtWidgets.QGridLayout()
        status_grid.setHorizontalSpacing(14)
        status_grid.setVerticalSpacing(14)
        for index, widget in enumerate([self.sensor_status_label, self.joystick_status_label, self.steamvr_status_label, self.strava_status_label]):
            status_grid.addWidget(self._status_tile(widget), index // 2, index % 2)
        dashboard_layout.addLayout(status_grid)
        dashboard_layout.addStretch(1)

        calibration = self._make_page()
        calibration_layout = calibration.widget().layout()
        calibration_layout.addWidget(self._section_title("Calibrate your treadmill like a console setup wizard"))
        cal_card = self._card("CALIBRATION", "A guided flow for sensor selection and treadmill tuning.")
        cal_sensor = QtWidgets.QLabel("Sensor selection lives in Menu → Input Device. Run Auto calibrate when the sensor is ready.")
        cal_sensor.setObjectName("hint_label")
        cal_sensor.setWordWrap(True)
        cal_card.layout().addWidget(cal_sensor)
        for text in [
            "1  Select sensor mouse",
            "2  Walk slowly for 5 seconds",
            "3  Walk normally for 5 seconds",
            "4  Run for 5 seconds",
            "5  Test virtual joystick output",
            "6  Save calibration",
        ]:
            cal_card.layout().addWidget(self._step_label(text))
        cal_buttons = QtWidgets.QHBoxLayout()
        cal_buttons.setSpacing(12)
        cal_buttons.addWidget(self.calibrate_button)
        cal_buttons.addWidget(self.reset_health_button)
        cal_card.layout().addLayout(cal_buttons)
        calibration_layout.addWidget(cal_card)
        calibration_layout.addStretch(1)

        profiles = self._make_page()
        profiles_layout = profiles.widget().layout()
        profiles_layout.addWidget(self._section_title("Choose a game profile"))
        active_profile_card = self._card("ACTIVE PROFILE", "Profiles hold tuning for different games, surfaces, and walking styles.")
        active_profile_card.layout().addLayout(profile_row)
        profiles_layout.addWidget(active_profile_card)
        game_grid = QtWidgets.QGridLayout()
        game_grid.setHorizontalSpacing(14)
        game_grid.setVerticalSpacing(14)
        for index, name in enumerate(["BoneLab", "Half-Life: Alyx", "Skyrim VR", "Custom"]):
            game_grid.addWidget(self._profile_tile(name), index // 2, index % 2)
        profiles_layout.addLayout(game_grid)
        profiles_layout.addStretch(1)

        stats = self._make_page()
        stats_layout = stats.widget().layout()
        stats_layout.addWidget(self._section_title("Workout summary and Strava sync"))
        last_card = self._card("LAST SESSION", "Completed sessions can be uploaded to Strava.")
        last_card.layout().addWidget(self.last_session_label)
        last_card.layout().addWidget(self.total_stats_label)
        stats_layout.addWidget(last_card)
        strava_status_card = self._card("STRAVA STATUS", "Authorize once, then upload after each session.")
        strava_status_card.layout().addWidget(self.strava_status_label)
        strava_status_card.layout().addLayout(strava_buttons)
        stats_layout.addWidget(strava_status_card)
        stats_layout.addStretch(1)

        menu_page = QtWidgets.QWidget()
        menu_layout = QtWidgets.QHBoxLayout(menu_page)
        menu_layout.setContentsMargins(0, 10, 0, 0)
        menu_layout.setSpacing(28)
        menu_sidebar = QtWidgets.QFrame()
        menu_sidebar.setObjectName("menu_sidebar")
        menu_sidebar_layout = QtWidgets.QVBoxLayout(menu_sidebar)
        menu_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        menu_sidebar_layout.setSpacing(4)
        self.menu_list = QtWidgets.QListWidget()
        self.menu_list.setObjectName("menu_list")
        menu_entries = [
            ("⚙", "System"),
            ("🖱", "Input Device"),
            ("🎮", "Virtual Joystick"),
            ("🏃", "Movement"),
            ("💨", "Sprint"),
            ("👤", "Body & Sensor"),
            ("🥽", "SteamVR"),
            ("📊", "Strava"),
            ("🔧", "Developer"),
        ]
        for icon, label in menu_entries:
            self.menu_list.addItem(f"{icon}  {label}")
        self.menu_list.setCurrentRow(0)
        menu_sidebar_layout.addWidget(self.menu_list)
        menu_layout.addWidget(menu_sidebar, 2)
        self.menu_stack = QtWidgets.QStackedWidget()
        self.menu_stack.setObjectName("menu_stack")
        menu_layout.addWidget(self.menu_stack, 7)

        def menu_card_page(title, *cards):
            page = self._make_page()
            layout = page.widget().layout()
            layout.setContentsMargins(18, 8, 18, 18)
            layout.addWidget(self._section_title(title))
            for card in cards:
                layout.addWidget(card)
            layout.addStretch(1)
            return page

        system_card = self._card("SYSTEM", "General application controls.")
        system_save = QtWidgets.QPushButton("Save Profile")
        system_save.clicked.connect(self.save)
        system_card.layout().addWidget(system_save)
        input_card = self._card("INPUT DEVICE", "Sensor and output backend selection.")
        input_form = QtWidgets.QFormLayout()
        input_form.addRow("Output mode", self.output_mode_combo)
        input_card.layout().addLayout(input_form)
        input_card.layout().addLayout(device_row)
        virtual_card = self._card("VIRTUAL JOYSTICK", "Current backend state and session output.")
        virtual_card.layout().addWidget(self._status_tile(self.joystick_status_label))
        movement_card = self._card("MOVEMENT TUNING", "Advanced movement response values.")
        movement_card.layout().addLayout(settings_form)
        curve_card = self._card("RESPONSE CURVE", "Fine tune low-speed precision and high-speed ramp-up.")
        curve_hint = QtWidgets.QLabel("Left-click to add/drag points. Right-click to delete a point.")
        curve_hint.setObjectName("hint_label")
        curve_card.layout().addWidget(curve_hint)
        curve_card.layout().addWidget(self.curve_editor)
        sprint_card = self._card("SPRINT SETTINGS", "Map high-speed movement to an action.")
        sprint_card.layout().addLayout(sprint_form)
        sprint_card.layout().addWidget(self._stat_tile(self.sprint_state_label))
        body_card = self._card("BODY & SENSOR", "Health estimate inputs and sensor calibration details.")
        body_card.layout().addLayout(health_form)
        steamvr_card = self._card("STEAMVR", "Install or remove the native SteamVR driver.")
        steamvr_card.layout().addLayout(steamvr_driver_row)
        steamvr_note = QtWidgets.QLabel("Restart SteamVR after changing driver installation state.")
        steamvr_note.setObjectName("hint_label")
        steamvr_card.layout().addWidget(steamvr_note)
        strava_settings_card = self._card("STRAVA", "OAuth credentials and authorization code.")
        strava_settings_card.layout().addLayout(strava_form)
        strava_hint = QtWidgets.QLabel("Authorize and upload from the Stats screen after a session.")
        strava_hint.setObjectName("hint_label")
        strava_settings_card.layout().addWidget(strava_hint)
        diagnostics_card = self._card("DEVELOPER DIAGNOSTICS", "Raw values are kept here so the dashboard stays clean.")
        diag_grid = QtWidgets.QGridLayout()
        for index, widget in enumerate([self.raw_label, self.filtered_label, self.output_label, self.movement_label, self.steps_label, self.met_label]):
            diag_grid.addWidget(self._stat_tile(widget), index // 2, index % 2)
        diagnostics_card.layout().addLayout(diag_grid)

        for page in [
            menu_card_page("System", system_card),
            menu_card_page("Input Device", input_card),
            menu_card_page("Virtual Joystick", virtual_card),
            menu_card_page("Movement", movement_card, curve_card),
            menu_card_page("Sprint", sprint_card),
            menu_card_page("Body & Sensor", body_card),
            menu_card_page("SteamVR", steamvr_card),
            menu_card_page("Strava", strava_settings_card),
            menu_card_page("Developer", diagnostics_card),
        ]:
            self.menu_stack.addWidget(page)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("main_tabs")
        self.tabs.setUsesScrollButtons(False)
        for label, page in [("DASHBOARD", dashboard), ("CALIBRATION", calibration), ("PROFILES", profiles), ("STATS", stats)]:
            self.tabs.addTab(page, label)

        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(16)
        header.addWidget(self.controller_label)
        header.addStretch(1)
        globe = QtWidgets.QLabel("◉")
        globe.setObjectName("top_hint")
        header.addWidget(globe)
        header.addWidget(self.clock_label)
        header.addWidget(self.status_label)

        self.content_stack = QtWidgets.QStackedWidget()
        self.content_stack.addWidget(self.tabs)
        self.content_stack.addWidget(menu_page)

        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(16)
        footer.addWidget(self.menu_button)
        footer.addStretch(1)
        footer.addWidget(self.save_button)

        shell = QtWidgets.QVBoxLayout()
        shell.setContentsMargins(44, 14, 44, 18)
        shell.setSpacing(10)
        shell.addLayout(header)
        shell.addWidget(self.content_stack, 1)
        shell.addLayout(footer)
        self.setLayout(shell)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Tab"), self, activated=self.next_tab)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Backtab"), self, activated=self.previous_tab)
        QtGui.QShortcut(QtGui.QKeySequence("F5"), self, activated=self.refresh_devices)
        QtGui.QShortcut(QtGui.QKeySequence("Escape"), self, activated=self.close_menu)
        self.menu_button.clicked.connect(self.open_menu)
        self.menu_list.currentRowChanged.connect(self.menu_stack.setCurrentIndex)

    def _make_page(self):
        page_content = QtWidgets.QWidget()
        page_layout = QtWidgets.QVBoxLayout(page_content)
        page_layout.setContentsMargins(96, 28, 96, 34)
        page_layout.setSpacing(22)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(page_content)
        return scroll

    def _card(self, title, subtitle=None):
        card = QtWidgets.QFrame()
        card.setObjectName("command_card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(14)
        label = QtWidgets.QLabel(title)
        label.setObjectName("card_title")
        layout.addWidget(label)
        if subtitle:
            sublabel = QtWidgets.QLabel(subtitle)
            sublabel.setObjectName("card_subtitle")
            sublabel.setWordWrap(True)
            layout.addWidget(sublabel)
        return card

    def _stat_tile(self, label):
        tile = QtWidgets.QFrame()
        tile.setObjectName("stat_tile")
        layout = QtWidgets.QVBoxLayout(tile)
        layout.setContentsMargins(18, 14, 18, 14)
        label.setParent(tile)
        layout.addWidget(label)
        return tile

    def _section_title(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("section_title")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        return label

    def _small_caps(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("small_caps")
        return label

    def update_clock(self):
        self.clock_label.setText(dt.datetime.now().strftime("%-I:%M %p"))

    def next_tab(self):
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count())

    def previous_tab(self):
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count())

    def open_menu(self):
        self.content_stack.setCurrentIndex(1)

    def close_menu(self):
        self.content_stack.setCurrentIndex(0)

    def _status_tile(self, label):
        tile = QtWidgets.QFrame()
        tile.setObjectName("status_tile")
        layout = QtWidgets.QVBoxLayout(tile)
        layout.setContentsMargins(18, 14, 18, 14)
        label.setParent(tile)
        layout.addWidget(label)
        return tile

    def _step_label(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("step_label")
        return label

    def _profile_tile(self, name):
        tile = QtWidgets.QFrame()
        tile.setObjectName("profile_tile")
        layout = QtWidgets.QVBoxLayout(tile)
        layout.setContentsMargins(22, 18, 22, 18)
        title = QtWidgets.QLabel(name)
        title.setObjectName("profile_title")
        desc = QtWidgets.QLabel("Game profile preset")
        desc.setObjectName("card_subtitle")
        active = QtWidgets.QLabel("ACTIVE" if name == self.current_profile_name() else "AVAILABLE")
        active.setObjectName("small_caps")
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch(1)
        layout.addWidget(active)
        return tile

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
        self.strava_authorize_button.clicked.connect(self.authorize_strava)
        self.strava_exchange_button.clicked.connect(self.exchange_strava_code)
        self.strava_upload_button.clicked.connect(self.upload_last_session_to_strava)
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
            self.height_spin,
            self.weight_spin,
            self.age_spin,
            self.gender_combo,
            self.mouse_dpi_combo,
            self.custom_dpi_spin,
            self.polling_rate_spin,
            self.incline_spin,
            self.strava_client_id_edit,
            self.strava_client_secret_edit,
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
        self.height_spin.valueChanged.connect(self.update_stride_estimate)
        self.mouse_dpi_combo.currentIndexChanged.connect(self.update_dpi_controls)

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
        self.sensor_status_label.setText("Sensor: Connected" if self.devices else "Sensor: Not Found")

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
        height_cm = float(health.get("height_cm", self._height_from_stride(float(health.get("stride_length_m", 0.72)))))
        self.height_spin.setValue(height_cm)
        self.weight_spin.setValue(float(health.get("user_weight_kg", 55.0)))
        self.age_spin.setValue(int(health.get("age_years", 30)))
        self.gender_combo.setCurrentText(health.get("gender", "unspecified"))
        self._set_dpi_value(float(health.get("mouse_dpi", 1600.0)))
        self.polling_rate_spin.setValue(float(health.get("polling_rate_hz", 1000.0)))
        self.incline_spin.setValue(float(health.get("incline_degrees", health.get("incline_percentage", 0.0))))
        self.curve_editor.set_points(profile.get("curve_points", DEFAULT_PROFILE["curve_points"]))
        strava = self.data.get("strava", {})
        self.strava_client_id_edit.setText(strava.get("client_id", ""))
        self.strava_client_secret_edit.setText(strava.get("client_secret", ""))
        self.update_axis_controls()
        self.update_stride_estimate()
        self.update_dpi_controls()
        self.selected_profile_label.setText(f"Profile: {self.data['active_profile']}")
        self.strava_status_label.setText("Strava: Connected" if self.data.get("strava", {}).get("access_token") else "Strava: Not Connected")

    def read_ui_to_profile(self):
        if self.device_combo.currentIndex() >= 0:
            self.data["selected_device_path"] = self.device_combo.currentData()

        self.data["output_mode"] = self.output_mode_combo.currentData() or OUTPUT_UINPUT
        self.data.setdefault("strava", {})
        self.data["strava"]["client_id"] = self.strava_client_id_edit.text().strip()
        self.data["strava"]["client_secret"] = self.strava_client_secret_edit.text().strip()
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
        height_cm = self.height_spin.value()
        existing_health = profile.get("health", {})
        profile["health"] = {
            "height_cm": height_cm,
            "stride_length_m": self._stride_from_height(height_cm),
            "user_weight_kg": self.weight_spin.value(),
            "age_years": self.age_spin.value(),
            "gender": self.gender_combo.currentText(),
            "mouse_dpi": self._current_dpi_value(),
            "polling_rate_hz": self.polling_rate_spin.value(),
            "incline_degrees": self.incline_spin.value(),
            "manual_friction_multiplier": existing_health.get("manual_friction_multiplier", 1.0),
            "calorie_factor": existing_health.get("calorie_factor", 1.0),
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

    def update_stride_estimate(self):
        self.stride_estimate_label.setText(f"Estimated stride: {self._stride_from_height(self.height_spin.value()):.2f} m")

    def update_dpi_controls(self):
        self.custom_dpi_spin.setEnabled(self.mouse_dpi_combo.currentData() == CUSTOM_DPI_VALUE)

    def _current_dpi_value(self):
        value = self.mouse_dpi_combo.currentData()
        if value == CUSTOM_DPI_VALUE:
            return self.custom_dpi_spin.value()
        return float(value or 1600.0)

    def _set_dpi_value(self, dpi):
        int_dpi = int(round(dpi))
        index = self.mouse_dpi_combo.findData(int_dpi)
        if index >= 0:
            self.mouse_dpi_combo.setCurrentIndex(index)
        else:
            custom_index = self.mouse_dpi_combo.findData(CUSTOM_DPI_VALUE)
            if custom_index >= 0:
                self.mouse_dpi_combo.setCurrentIndex(custom_index)
        self.custom_dpi_spin.setValue(float(dpi))

    @staticmethod
    def _stride_from_height(height_cm):
        return max(0.1, float(height_cm) * 0.415 / 100.0)

    @staticmethod
    def _height_from_stride(stride_length_m):
        return max(80.0, min(230.0, float(stride_length_m) * 100.0 / 0.415))

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
        self.session_start_time = dt.datetime.now().replace(microsecond=0)
        self.session_elapsed_seconds = 0
        self.session_state_label.setText("Session Running")
        self.joystick_status_label.setText("Virtual Joystick: Active")
        self.session_timer.start(1000)
        self.last_telemetry = None
        self.last_session = None
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
            self.session_timer.stop()
            self.session_state_label.setText("Ready")
            self.treadmill_visual.set_output_percent(0)
            self.joystick_status_label.setText("Virtual Joystick: Idle")
            self.treadmill_visual.set_speed(0.0)
            self.treadmill_visual.set_output_percent(0)
            self._finalize_session()

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
        self.speed_label.setText("Speed: 0.00 km/h")
        self.distance_label.setText("Distance: 0 m")
        self.calories_label.setText("Calories: 0 kcal")
        self.met_label.setText("MET: 0.00")

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

    def authorize_strava(self):
        self.read_ui_to_profile()
        try:
            url = build_authorization_url(self.data.get("strava", {}).get("client_id", ""))
        except Exception as exc:
            self.show_error(str(exc))
            return

        webbrowser.open(url)
        self.status_label.setText("Opened Strava authorization page. Paste the returned code here.")

    def exchange_strava_code(self):
        self.read_ui_to_profile()
        strava = self.data.setdefault("strava", {})
        try:
            token = exchange_code(
                strava.get("client_id", ""),
                strava.get("client_secret", ""),
                self.strava_code_edit.text(),
            )
        except Exception as exc:
            self.show_error(f"Failed to authorize Strava:\n{exc}")
            return

        strava.update(
            {
                "access_token": token.get("access_token", ""),
                "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")),
                "expires_at": token.get("expires_at", 0),
            }
        )
        self.strava_code_edit.clear()
        save_data(self.data)
        self.status_label.setText("Strava authorization saved.")

    def upload_last_session_to_strava(self):
        if not self.last_session:
            self.show_error("No completed treadmill session to upload yet.")
            return

        self.read_ui_to_profile()
        strava = self.data.setdefault("strava", {})
        try:
            result, token = upload_activity(strava, self.last_session)
        except Exception as exc:
            self.show_error(f"Failed to upload to Strava:\n{exc}")
            return

        if token:
            strava.update(
                {
                    "access_token": token.get("access_token", strava.get("access_token", "")),
                    "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")),
                    "expires_at": token.get("expires_at", strava.get("expires_at", 0)),
                }
            )
            save_data(self.data)

        self.status_label.setText(f"Uploaded to Strava: activity #{result.get('id', 'created')}")

    def show_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Maratron error", message)

    def update_telemetry(self, data):
        self.last_telemetry = dict(data)
        self.raw_label.setText(f"Raw: {data['raw']}")
        self.filtered_label.setText(f"Filtered: {data['filtered']:.2f}")
        self.output_label.setText(f"Joystick: {data['joy']}")
        self.movement_label.setText(f"Movement: x={data['move_x']:.2f} y={data['move_y']:.2f}")
        self.sprint_label.setText(f"Sprint: {'ON' if data['sprint'] else 'OFF'}")
        self.sprint_state_label.setText(f"Sprint: {'ON' if data['sprint'] else 'OFF'}")
        self.speed_bar.setValue(int(data["curved"] * 100))
        self.treadmill_visual.set_output_percent(int(data.get("curved", 0.0) * 100))
        self.treadmill_visual.set_speed(data.get("speed_kmh", 0.0))
        self.treadmill_visual.set_output_percent(int(data.get("curved", 0.0) * 100))
        self.steps_label.setText(f"Steps: {data['steps']}")
        self.speed_label.setText(f"Speed: {data.get('speed_kmh', 0.0):.2f} km/h")
        self.distance_label.setText(f"Distance: {data['distance_m']:.1f} m")
        self.calories_label.setText(f"Calories: {data['calories']:.1f} kcal")
        self.met_label.setText(f"MET: {data.get('met', 0.0):.2f}")
        if data.get("speed_kmh", 0.0) >= 8.0:
            self.session_state_label.setText("Running")
        elif data.get("speed_kmh", 0.0) > 0.2:
            self.session_state_label.setText("Walking")

    def update_session_duration(self):
        if self.session_start_time is None:
            return
        self.session_elapsed_seconds = max(0, int((dt.datetime.now().replace(microsecond=0) - self.session_start_time).total_seconds()))
        hours, rem = divmod(self.session_elapsed_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        self.duration_label.setText(f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _finalize_session(self):
        if self.session_start_time is None or self.last_telemetry is None:
            self.session_start_time = None
            return

        ended = dt.datetime.now().replace(microsecond=0)
        elapsed = max(1, int((ended - self.session_start_time).total_seconds()))
        distance_m = float(self.last_telemetry.get("distance_m", 0.0))
        average_speed_kmh = (distance_m / elapsed) * 3.6 if elapsed > 0 else 0.0
        threshold_kmh = float(self.data.get("strava", {}).get("auto_detect_run_kmh", 8.0) or 8.0)
        activity_type = "Run" if average_speed_kmh >= threshold_kmh else "Walk"
        self.last_session = {
            "name": "Maratron Treadmill Session",
            "activity_type": activity_type,
            "start_date_local": self.session_start_time.isoformat(),
            "elapsed_time": elapsed,
            "distance_m": distance_m,
            "calories": float(self.last_telemetry.get("calories", 0.0)),
            "average_speed_kmh": average_speed_kmh,
            "description": "Manual treadmill session recorded by MaratronVR.",
        }
        self.session_start_time = None
        summary = f"{activity_type} • {distance_m:.1f} m • {average_speed_kmh:.2f} km/h • {elapsed}s"
        self.last_session_label.setText(summary)
        self.total_stats_label.setText(f"Last calories: {self.last_session['calories']:.1f} kcal")
        self.status_label.setText(f"Session ready for Strava: {activity_type}, {distance_m:.1f} m, {average_speed_kmh:.2f} km/h")

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

    @staticmethod
    def run():
        """Entry point: display the window with the dark theme loaded."""
        import sys
        app = QtWidgets.QApplication(sys.argv)
        style_path = Path(__file__).resolve().parent / "style.qss"
        if style_path.exists():
            with open(style_path) as f:
                app.setStyleSheet(f.read())
        window = MainWindow()
        window.show()
        sys.exit(app.exec())