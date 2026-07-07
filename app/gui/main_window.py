import datetime as dt
import platform
import webbrowser
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from app.backends.uinput_backend import BUTTON_MAP
from app.controllers.navigation_controller import NavigationController
from app.controllers.profile_controller import ProfileController
from app.core.calibration import CalibrationWorker
from app.core.device_scan import scan_pointer_devices
from app.core.driver_install import (
    install_maratron_driver,
    uninstall_maratron_driver,
)
from app.core.profiles import (
    OUTPUT_HIDMAESTRO,
    OUTPUT_STEAMVR,
    OUTPUT_UINPUT,
    load_data,
    make_profile_config,
    save_data,
)
from app.core.strava_client import (
    build_authorization_url,
    exchange_code,
    upload_activity,
)
from app.core.treadmill_reader import TreadmillWorker
from app.gui.curve_widget import CurveEditor
from app.gui.stats_chart_widget import StatsChartWidget
from app.gui.toast import ToastNotification
from app.gui.treadmill_widget import TreadmillWidget
from app.core.constants import (
    CUSTOM_DPI_VALUE,
    DPI_PRESETS,
    RUN_SPEED_THRESHOLD_KMH,
    SENSITIVITY_DEFAULT,
    SENSITIVITY_MAX,
    SENSITIVITY_MIN,
    STRIDE_MULTIPLIER,
    THREAD_WAIT_TIMEOUT_MS,
    WALK_SPEED_THRESHOLD_KMH,
)
from app.core.logging import get_logger
from app.gui.pages.dashboard_page import DashboardPage
from app.services.session_service import SessionService
from app.gui.pages.calibration_page import CalibrationPage
from app.gui.pages.profiles_page import ProfilesPage
from app.gui.pages.stats_page import StatsPage
from app.gui.pages.settings_page import SettingsPage


OUTPUT_LABELS = {
    OUTPUT_UINPUT: "UInput Gamepad",
    OUTPUT_STEAMVR: "SteamVR Driver",
    OUTPUT_HIDMAESTRO: "HIDMaestro (Windows)",
}

STEAMVR_BUTTONS = {
    "Grip": "grip",
    "Trackpad click": "trackpad",
    "Application menu": "application_menu",
    "Trigger": "trigger",
    "Disabled": "disabled",
}
_log = get_logger(__name__)


class MainWindow(QtWidgets.QWidget):
    def __init__(self, data=None, profile_ctrl=None, nav=None):
        super().__init__()

        self.data = data if data is not None else load_data()
        self.profile_ctrl = profile_ctrl
        self.nav = nav
        self.worker = None
        self.calibrator = None
        self.devices = []
        self.session_start_time = None
        self.last_telemetry = None
        self.last_session = None
        self.session_elapsed_seconds = 0

        self.setWindowTitle("MaratronVR")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 640)

        self._create_widgets()
        # _build_shell(), _build_pages(), _wire_signals(), _finalize_init()
        # are called by build_app() in bootstrap.py after dependency injection.
        self._build_shell()
        self._build_pages()

    # ------------------------------------------------------------------
    # Widget creation (all widgets created here, shared with pages)
    # ------------------------------------------------------------------

    def _create_widgets(self):
        # Header
        self.controller_label = QtWidgets.QLabel("MARATRON")
        self.controller_label.setObjectName("app_title")
        self.profile_avatar_label = QtWidgets.QLabel("M")
        self.profile_avatar_label.setObjectName("profile_avatar")
        self.profile_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.profile_avatar_label.setFixedSize(38, 34)
        self.session_status_pill = QtWidgets.QLabel("")
        self.session_status_pill.setObjectName("session_status_pill")
        self.session_status_pill.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.session_status_pill.setFixedSize(10, 10)

        # Output / device
        self.output_mode_combo = QtWidgets.QComboBox()
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_UINPUT], OUTPUT_UINPUT)
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_STEAMVR], OUTPUT_STEAMVR)
        self.output_mode_combo.addItem(OUTPUT_LABELS.get(OUTPUT_HIDMAESTRO, "HIDMaestro (Windows)"), OUTPUT_HIDMAESTRO)
        self.device_combo = QtWidgets.QComboBox()
        self.refresh_devices_button = QtWidgets.QPushButton("Refresh")

        # Profiles
        self.profile_combo = QtWidgets.QComboBox()
        self.new_profile_button = QtWidgets.QPushButton("New")
        self.duplicate_profile_button = QtWidgets.QPushButton("Dup")
        self.delete_profile_button = QtWidgets.QPushButton("Del")

        # Movement
        self.axis_combo = QtWidgets.QComboBox(); self.axis_combo.addItems(["REL_Y", "REL_X"])
        self.omnidirectional_check = QtWidgets.QCheckBox("Omnidirectional / use REL_X + REL_Y")
        self.invert_check = QtWidgets.QCheckBox("Invert Y axis")
        self.deadzone_spin = QtWidgets.QSpinBox(); self.deadzone_spin.setRange(0, 50)
        self.smoothing_spin = QtWidgets.QDoubleSpinBox(); self.smoothing_spin.setRange(0.01, 1.0); self.smoothing_spin.setSingleStep(0.01)
        self.max_speed_spin = QtWidgets.QDoubleSpinBox(); self.max_speed_spin.setRange(1.0, 200.0); self.max_speed_spin.setSingleStep(1.0)
        self.poll_spin = QtWidgets.QSpinBox(); self.poll_spin.setRange(1, 50)
        self.curve_editor = CurveEditor()

        # Sprint
        self.auto_sprint_check = QtWidgets.QCheckBox("Auto sprint at max speed")
        self.sprint_threshold_spin = QtWidgets.QDoubleSpinBox(); self.sprint_threshold_spin.setRange(0.1, 1.0); self.sprint_threshold_spin.setSingleStep(0.01)
        self.sprint_button_combo = QtWidgets.QComboBox(); self.sprint_button_combo.addItems(BUTTON_MAP.keys())
        self.steamvr_sprint_button_combo = QtWidgets.QComboBox()
        for label, value in STEAMVR_BUTTONS.items():
            self.steamvr_sprint_button_combo.addItem(label, value)

        # Body & Sensor
        self.height_spin = QtWidgets.QDoubleSpinBox(); self.height_spin.setRange(80.0, 230.0); self.height_spin.setSingleStep(0.5); self.height_spin.setSuffix(" cm")
        self.stride_estimate_label = QtWidgets.QLabel("Estimated stride: 0.72 m")
        self.weight_spin = QtWidgets.QDoubleSpinBox(); self.weight_spin.setRange(20.0, 200.0); self.weight_spin.setSingleStep(0.5); self.weight_spin.setSuffix(" kg")
        self.age_spin = QtWidgets.QSpinBox(); self.age_spin.setRange(1, 120)
        self.gender_combo = QtWidgets.QComboBox(); self.gender_combo.addItems(["unspecified", "female", "male"])
        self.mouse_dpi_combo = QtWidgets.QComboBox()
        for dpi in DPI_PRESETS:
            self.mouse_dpi_combo.addItem(f"{dpi} DPI", dpi)
        self.mouse_dpi_combo.addItem("Custom", CUSTOM_DPI_VALUE)
        self.custom_dpi_spin = QtWidgets.QDoubleSpinBox(); self.custom_dpi_spin.setRange(1.0, 30000.0); self.custom_dpi_spin.setSingleStep(100.0); self.custom_dpi_spin.setSuffix(" DPI")
        self.polling_rate_spin = QtWidgets.QDoubleSpinBox(); self.polling_rate_spin.setRange(1.0, 8000.0); self.polling_rate_spin.setSingleStep(125.0); self.polling_rate_spin.setSuffix(" Hz")
        self.incline_spin = QtWidgets.QDoubleSpinBox(); self.incline_spin.setRange(0.0, 25.0); self.incline_spin.setSingleStep(0.5); self.incline_spin.setSuffix("\u00b0")

        # Telemetry labels
        self.raw_label = QtWidgets.QLabel("Raw: 0")
        self.filtered_label = QtWidgets.QLabel("Filtered: 0")
        self.output_label = QtWidgets.QLabel("Joy: 0")
        self.movement_label = QtWidgets.QLabel("Mv: x=0.00 y=0.00")
        self.sprint_label = QtWidgets.QLabel("Sprint: OFF")
        self.sprint_state_label = QtWidgets.QLabel("Sprint: OFF")
        self.session_state_label = QtWidgets.QLabel("Ready")
        self.selected_profile_label = QtWidgets.QLabel("Profile: Default")
        self.duration_label = QtWidgets.QLabel("00:00:00")
        self.sensor_status_label = QtWidgets.QLabel("Sensor: ---")
        self.joystick_status_label = QtWidgets.QLabel("Joystick: Idle")
        self.steamvr_status_label = QtWidgets.QLabel("SteamVR: Idle")
        self.strava_status_label = QtWidgets.QLabel("Strava: ---")
        self.last_session_label = QtWidgets.QLabel("No session yet")
        self.total_stats_label = QtWidgets.QLabel("")
        self.speed_label = QtWidgets.QLabel("Speed: 0.00 km/h")
        self.distance_label = QtWidgets.QLabel("Distance: 0 m")
        self.calories_label = QtWidgets.QLabel("Cal: 0 kcal")
        self.met_label = QtWidgets.QLabel("MET: 0.00")
        self.status_label = QtWidgets.QLabel("")
        self.clock_label = QtWidgets.QLabel()
        self.speed_bar = QtWidgets.QProgressBar(); self.speed_bar.setRange(0, 100)

        # Stats page widgets
        self.stats_total_distance = QtWidgets.QLabel("0.00 km")
        self.stats_total_time = QtWidgets.QLabel("0m")
        self.stats_total_calories = QtWidgets.QLabel("0 kcal")
        self.stats_session_count = QtWidgets.QLabel("0 sessions")
        self.stats_chart = StatsChartWidget()
        self.stats_sessions_list = QtWidgets.QVBoxLayout()
        self.stats_sessions_list.setSpacing(8)

        # Visual + buttons
        self.treadmill_visual = TreadmillWidget()
        self.steps_label = QtWidgets.QLabel("Steps: 0")
        self.sensitivity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(SENSITIVITY_MIN, SENSITIVITY_MAX)
        self.sensitivity_slider.setValue(SENSITIVITY_DEFAULT)
        self.sensitivity_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.sensitivity_slider.setTickInterval(20)
        self.sensitivity_label = QtWidgets.QLabel("Sensitivity: 1.00x")

        # System info
        self.sys_os = QtWidgets.QLabel(platform.system() + " " + platform.release())
        self.sys_arch = QtWidgets.QLabel(platform.machine())
        self.sys_python = QtWidgets.QLabel(f"Python {platform.python_version()}")
        try:
            import psutil
            mem = psutil.virtual_memory()
            self.sys_ram = QtWidgets.QLabel(f"RAM: {mem.total // (1024**3)} GB ({(mem.available // (1024**2))} MB free)")
            self.sys_cpu = QtWidgets.QLabel(f"CPU: {psutil.cpu_count(logical=True)} cores")
        except ImportError:
            self.sys_ram = QtWidgets.QLabel("RAM: install psutil for details")
            self.sys_cpu = QtWidgets.QLabel("CPU: install psutil for details")

        # Action buttons
        self.start_button = QtWidgets.QPushButton("Start"); self.start_button.setObjectName("start_button")
        self.stop_button = QtWidgets.QPushButton("Stop"); self.stop_button.setObjectName("stop_button")
        self.save_button = QtWidgets.QPushButton("Save")
        self.calibrate_button = QtWidgets.QPushButton("Auto calibrate")
        self.reset_health_button = QtWidgets.QPushButton("Reset health")
        self.install_driver_button = QtWidgets.QPushButton("Install"); self.install_driver_button.setObjectName("install_driver_button")
        self.uninstall_driver_button = QtWidgets.QPushButton("Uninstall")

        # Strava
        self.strava_client_id_edit = QtWidgets.QLineEdit()
        self.strava_client_secret_edit = QtWidgets.QLineEdit(); self.strava_client_secret_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.strava_code_edit = QtWidgets.QLineEdit()
        self.strava_authorize_button = QtWidgets.QPushButton("Auth"); self.strava_authorize_button.setObjectName("strava_authorize_button")
        self.strava_exchange_button = QtWidgets.QPushButton("Save")
        self.strava_upload_button = QtWidgets.QPushButton("Upload"); self.strava_upload_button.setObjectName("strava_upload_button")

        # Calibration labels
        self.cal_noise_label = QtWidgets.QLabel("Live noise: 0")
        self.cal_max_label = QtWidgets.QLabel("Max noise: \u2014")
        self.cal_count_label = QtWidgets.QLabel("Samples: 0")

        # Profile grid + empty state
        self.profiles_grid = QtWidgets.QGridLayout()
        self.profiles_grid.setHorizontalSpacing(16)
        self.profiles_grid.setVerticalSpacing(16)
        self.profiles_empty = self._build_empty_state_widget(
            "No profiles yet",
            "Create your first profile to get started \u2014 press New or use Ctrl+N.",
        )
        self.stats_empty = self._build_empty_state_widget(
            "No sessions yet",
            "Start a session from the Dashboard to see your history here.",
        )

        # Timers
        self.clock_timer = QtCore.QTimer(self)
        self.session_timer = QtCore.QTimer(self)

    # ------------------------------------------------------------------
    # Shell: header, content stack, footer
    # ------------------------------------------------------------------

    def _build_shell(self):
        self.header = QtWidgets.QFrame()
        self.header.setObjectName("steam_header")
        header_layout = QtWidgets.QVBoxLayout(self.header)
        header_layout.setContentsMargins(48, 12, 48, 14)
        header_layout.setSpacing(14)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)
        top_row.addWidget(self.controller_label)
        top_row.addStretch(1)
        top_row.addWidget(self.session_status_pill)
        top_row.addStretch(1)
        self.clock_label.setObjectName("header_clock")
        top_row.addWidget(self.clock_label)
        top_row.addWidget(self.profile_avatar_label)
        header_layout.addLayout(top_row)

        nav_row = QtWidgets.QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(0)
        self.previous_tab_keycap = QtWidgets.QLabel("Q")
        self.previous_tab_keycap.setObjectName("nav_keycap")
        self.previous_tab_keycap.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        nav_row.addWidget(self.previous_tab_keycap)
        nav_row.addStretch(1)
        self.tab_buttons = []
        for name in ["Dashboard", "Calibration", "Profiles", "Stats"]:
            btn = QtWidgets.QPushButton(name.upper())
            btn.setObjectName("nav_pill")
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self.switch_tab(n))
            nav_row.addWidget(btn)
            self.tab_buttons.append(btn)
        nav_row.addStretch(1)
        self.next_tab_keycap = QtWidgets.QLabel("E")
        self.next_tab_keycap.setObjectName("nav_keycap")
        self.next_tab_keycap.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        nav_row.addWidget(self.next_tab_keycap)
        self.tab_buttons[0].setChecked(True)
        header_layout.addLayout(nav_row)

        self.content_stack = QtWidgets.QStackedWidget()

        footer_frame = QtWidgets.QFrame()
        footer_frame.setObjectName("steam_footer")
        footer = QtWidgets.QHBoxLayout(footer_frame)
        footer.setContentsMargins(14, 6, 22, 6)
        footer.setSpacing(10)

        self.settings_toggle_btn = self._footer_shortcut_hint("Ctrl", "Settings", self.toggle_settings)
        self.settings_toggle_btn.setToolTip("Click or tap Ctrl to open Settings")
        footer.addWidget(self.settings_toggle_btn)
        footer.addStretch(1)
        footer.addWidget(self._footer_shortcut_hint("Backspace", "Back", self.go_back))
        footer.addSpacing(18)
        footer.addWidget(self._footer_shortcut_hint("Esc", "Escape", self.close_settings))

        shell = QtWidgets.QVBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self.header)
        shell.addWidget(self.content_stack, 1)
        shell.addWidget(footer_frame)
        self.setLayout(shell)

        QtGui.QShortcut(QtGui.QKeySequence("Escape"), self, activated=self.close_settings)
        QtGui.QShortcut(QtGui.QKeySequence("Backspace"), self, activated=self.go_back)
        QtGui.QShortcut(QtGui.QKeySequence("Q"), self, activated=lambda: self.cycle_tab(-1))
        QtGui.QShortcut(QtGui.QKeySequence("E"), self, activated=lambda: self.cycle_tab(1))
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self, activated=lambda: self.cycle_tab(-1))
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self, activated=lambda: self.cycle_tab(1))
        QtGui.QShortcut(QtGui.QKeySequence("1"), self, activated=lambda: self.switch_tab("Dashboard"))
        QtGui.QShortcut(QtGui.QKeySequence("2"), self, activated=lambda: self.switch_tab("Calibration"))
        QtGui.QShortcut(QtGui.QKeySequence("3"), self, activated=lambda: self.switch_tab("Profiles"))
        QtGui.QShortcut(QtGui.QKeySequence("4"), self, activated=lambda: self.switch_tab("Stats"))

    # ------------------------------------------------------------------
    # Pages (delegated to page classes)
    # ------------------------------------------------------------------

    def _build_pages(self):
        self.dashboard_page = DashboardPage(
            treadmill_visual=self.treadmill_visual,
            session_state_label=self.session_state_label,
            selected_profile_label=self.selected_profile_label,
            start_button=self.start_button,
            stop_button=self.stop_button,
            speed_label=self.speed_label,
            distance_label=self.distance_label,
            calories_label=self.calories_label,
            duration_label=self.duration_label,
            sensor_status_label=self.sensor_status_label,
            joystick_status_label=self.joystick_status_label,
            steamvr_status_label=self.steamvr_status_label,
            strava_status_label=self.strava_status_label,
            sensitivity_slider=self.sensitivity_slider,
            sensitivity_label=self.sensitivity_label,
        )
        self.calibration_page = CalibrationPage(
            calibrate_button=self.calibrate_button,
            reset_health_button=self.reset_health_button,
            cal_noise_label=self.cal_noise_label,
            cal_max_label=self.cal_max_label,
            cal_count_label=self.cal_count_label,
        )
        self.profiles_page = ProfilesPage(
            profile_combo=self.profile_combo,
            new_profile_button=self.new_profile_button,
            duplicate_profile_button=self.duplicate_profile_button,
            delete_profile_button=self.delete_profile_button,
            profiles_grid=self.profiles_grid,
            profiles_empty=self.profiles_empty,
        )
        self.stats_page = StatsPage(
            stats_total_distance=self.stats_total_distance,
            stats_total_time=self.stats_total_time,
            stats_total_calories=self.stats_total_calories,
            stats_session_count=self.stats_session_count,
            stats_chart=self.stats_chart,
            stats_sessions_list=self.stats_sessions_list,
            stats_empty=self.stats_empty,
            strava_status_label=self.strava_status_label,
            strava_authorize_button=self.strava_authorize_button,
            strava_exchange_button=self.strava_exchange_button,
            strava_upload_button=self.strava_upload_button,
            on_chart_metric_toggle=self._on_chart_metric_toggle,
        )
        self.settings_page = SettingsPage(
            sys_os=self.sys_os,
            sys_arch=self.sys_arch,
            sys_cpu=self.sys_cpu,
            sys_ram=self.sys_ram,
            sys_python=self.sys_python,
            output_mode_combo=self.output_mode_combo,
            device_combo=self.device_combo,
            refresh_devices_button=self.refresh_devices_button,
            axis_combo=self.axis_combo,
            omnidirectional_check=self.omnidirectional_check,
            invert_check=self.invert_check,
            deadzone_spin=self.deadzone_spin,
            smoothing_spin=self.smoothing_spin,
            max_speed_spin=self.max_speed_spin,
            poll_spin=self.poll_spin,
            auto_sprint_check=self.auto_sprint_check,
            sprint_threshold_spin=self.sprint_threshold_spin,
            sprint_button_combo=self.sprint_button_combo,
            steamvr_sprint_button_combo=self.steamvr_sprint_button_combo,
            height_spin=self.height_spin,
            stride_estimate_label=self.stride_estimate_label,
            weight_spin=self.weight_spin,
            age_spin=self.age_spin,
            gender_combo=self.gender_combo,
            mouse_dpi_combo=self.mouse_dpi_combo,
            custom_dpi_spin=self.custom_dpi_spin,
            polling_rate_spin=self.polling_rate_spin,
            incline_spin=self.incline_spin,
            curve_editor=self.curve_editor,
            install_driver_button=self.install_driver_button,
            uninstall_driver_button=self.uninstall_driver_button,
            strava_client_id_edit=self.strava_client_id_edit,
            strava_client_secret_edit=self.strava_client_secret_edit,
            strava_code_edit=self.strava_code_edit,
            raw_label=self.raw_label,
            filtered_label=self.filtered_label,
            output_label=self.output_label,
            movement_label=self.movement_label,
            steps_label=self.steps_label,
            met_label=self.met_label,
            save_callback=None,
        )

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.calibration_page)
        self.content_stack.addWidget(self.profiles_page)
        self.content_stack.addWidget(self.stats_page)
        self.content_stack.addWidget(self.settings_page)

        # Re-inject save_callback once profile_ctrl exists
        if hasattr(self, 'profile_ctrl') and self.profile_ctrl:
            self.settings_page.save_callback = self.profile_ctrl.save

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self):
        self.refresh_devices_button.clicked.connect(self.refresh_devices)
        self.profile_combo.currentTextChanged.connect(self.profile_ctrl.on_profile_selected)
        self.new_profile_button.clicked.connect(lambda: self.profile_ctrl.new_profile(self))
        self.duplicate_profile_button.clicked.connect(lambda: self.profile_ctrl.duplicate_profile(self))
        self.delete_profile_button.clicked.connect(lambda: self.profile_ctrl.delete_profile(self))
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.save_button.clicked.connect(self.profile_ctrl.save)
        self.calibrate_button.clicked.connect(self.auto_calibrate)
        self.reset_health_button.clicked.connect(self.reset_health)
        self.install_driver_button.clicked.connect(self.install_steamvr_driver)
        self.uninstall_driver_button.clicked.connect(self.uninstall_steamvr_driver)
        self.strava_authorize_button.clicked.connect(self.authorize_strava)
        self.strava_exchange_button.clicked.connect(self.exchange_strava_code)
        self.strava_upload_button.clicked.connect(self.upload_last_session_to_strava)
        self.curve_editor.pointsChanged.connect(lambda pts: self._on_config_changed())
        self.device_combo.currentIndexChanged.connect(lambda: self._on_config_changed())

        widgets = [
            self.output_mode_combo, self.axis_combo, self.omnidirectional_check,
            self.invert_check, self.deadzone_spin, self.smoothing_spin,
            self.max_speed_spin, self.poll_spin, self.auto_sprint_check,
            self.sprint_threshold_spin, self.sprint_button_combo,
            self.steamvr_sprint_button_combo, self.height_spin, self.weight_spin,
            self.age_spin, self.gender_combo, self.mouse_dpi_combo,
            self.custom_dpi_spin, self.polling_rate_spin, self.incline_spin,
            self.strava_client_id_edit, self.strava_client_secret_edit,
        ]
        for w in widgets:
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(lambda *a: self._on_config_changed())
            if hasattr(w, "currentTextChanged"):
                w.currentTextChanged.connect(lambda *a: self._on_config_changed())
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(lambda *a: self._on_config_changed())
            if hasattr(w, "stateChanged"):
                w.stateChanged.connect(lambda *a: self._on_config_changed())

        self.omnidirectional_check.stateChanged.connect(self.update_axis_controls)
        self.height_spin.valueChanged.connect(self.update_stride_estimate)
        self.mouse_dpi_combo.currentIndexChanged.connect(self.update_dpi_controls)
        self.sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        self.clock_timer.timeout.connect(self.update_clock)
        self.session_timer.timeout.connect(self.update_session_duration)

    def _finalize_init(self):
        self.update_clock()
        self.clock_timer.start(30_000)
        self.refresh_devices()
        self._refresh_profile_combo()
        self.profile_ctrl.load_profile_to_ui()
        self._on_profile_loaded()
        self._update_profile_header()
        self.update_session_status(False)

    # ------------------------------------------------------------------
    # Navigation (delegated to NavigationController)
    # ------------------------------------------------------------------

    def switch_tab(self, name):
        self.nav.switch_tab(name)

    def cycle_tab(self, direction):
        self.nav.cycle_tab(direction)

    def toggle_settings(self):
        self.nav.toggle_settings()

    def close_settings(self):
        self.nav.close_settings()

    def go_back(self):
        self.nav.go_back()

    def keyPressEvent(self, event):
        if self.nav.on_key_press(event):
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.nav.on_key_release(event):
            return
        super().keyReleaseEvent(event)

    # ------------------------------------------------------------------
    # Profile callbacks (thin delegates for ProfileController)
    # ------------------------------------------------------------------

    def _refresh_profile_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.data["profiles"].keys())
        self.profile_combo.setCurrentText(self.data["active_profile"])
        self.profile_combo.blockSignals(False)

    def _on_profile_loaded(self):
        self.update_axis_controls()
        self.update_stride_estimate()
        self.update_dpi_controls()

    def _update_profile_header(self):
        profile_name = self.profile_ctrl.current_profile_name()
        self.controller_label.setText(f"Profile: {profile_name}")
        initial = (profile_name.strip()[:1] or "M").upper()
        self.profile_avatar_label.setText(initial)

    def _toast(self, message):
        ToastNotification(self, message)

    def _on_config_changed(self):
        if not self.profile_combo.currentText():
            return
        self.update_axis_controls()
        self.profile_ctrl.read_ui_to_profile()
        if self.worker is not None:
            self.worker.update_config(make_profile_config(self.data))

    def _on_sensitivity_changed(self):
        val = self.sensitivity_slider.value() / 100.0
        self.sensitivity_label.setText(f"Sensitivity: {val:.2f}x")
        self._on_config_changed()

    def update_session_status(self, active):
        self.session_status_pill.setText("")
        self.session_status_pill.setProperty("status", "active" if active else "inactive")
        self.session_status_pill.style().unpolish(self.session_status_pill)
        self.session_status_pill.style().polish(self.session_status_pill)

    def refresh_devices(self):
        selected = self.data.get("selected_device_path", "")
        self.devices = scan_pointer_devices()
        self.sensor_status_label.setText("Sensor: Connected" if self.devices else "Sensor: Not Found")
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for dev in self.devices:
            self.device_combo.addItem(dev["label"], dev["path"])
        if selected:
            idx = self.device_combo.findData(selected)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        self.device_combo.blockSignals(False)

    def update_axis_controls(self):
        self.axis_combo.setEnabled(not self.omnidirectional_check.isChecked())

    def update_stride_estimate(self):
        h = self.height_spin.value()
        stride = max(0.1, float(h) * STRIDE_MULTIPLIER / 100.0)
        self.stride_estimate_label.setText(f"Estimated stride: {stride:.2f} m")

    def update_dpi_controls(self):
        self.custom_dpi_spin.setEnabled(self.mouse_dpi_combo.currentData() == CUSTOM_DPI_VALUE)

    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.profile_ctrl.save()
        self.session_start_time = dt.datetime.now().replace(microsecond=0)
        self.session_elapsed_seconds = 0
        self.session_state_label.setText("Running")
        self.update_session_status(True)
        self.joystick_status_label.setText("Joystick: Active")
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
            self.worker.wait(THREAD_WAIT_TIMEOUT_MS)
            self.worker = None
            self.session_timer.stop()
            self.session_state_label.setText("Ready")
            self.update_session_status(False)
            self.treadmill_visual.set_output_percent(0)
            self.joystick_status_label.setText("Joystick: Idle")
            self.treadmill_visual.set_speed(0.0)
            self.treadmill_visual.set_output_percent(0)
            self._finalize_session()

    def update_telemetry(self, data):
        self.last_telemetry = dict(data)
        self.raw_label.setText(f"Raw: {data['raw']}")
        self.filtered_label.setText(f"Filtered: {data['filtered']:.2f}")
        self.output_label.setText(f"Joy: {data['joy']}")
        self.movement_label.setText(f"Mv: x={data['move_x']:.2f} y={data['move_y']:.2f}")
        self.sprint_label.setText(f"Sprint: {'ON' if data['sprint'] else 'OFF'}")
        self.sprint_state_label.setText(f"Sprint: {'ON' if data['sprint'] else 'OFF'}")
        self.speed_bar.setValue(int(data["curved"] * 100))
        self.treadmill_visual.set_output_percent(int(data.get("curved", 0.0) * 100))
        self.treadmill_visual.set_speed(data.get("speed_kmh", 0.0))
        self.steps_label.setText(f"Steps: {data['steps']}")
        self.speed_label.setText(f"Speed: {data.get('speed_kmh', 0.0):.2f} km/h")
        self.distance_label.setText(f"Distance: {data['distance_m']:.1f} m")
        self.calories_label.setText(f"Cal: {data['calories']:.1f} kcal")
        self.met_label.setText(f"MET: {data.get('met', 0.0):.2f}")
        sk = data.get("speed_kmh", 0.0)
        if sk >= RUN_SPEED_THRESHOLD_KMH:
            self.session_state_label.setText("Running")
        elif sk > WALK_SPEED_THRESHOLD_KMH:
            self.session_state_label.setText("Walking")
        else:
            self.session_state_label.setText("Ready")

    def update_session_duration(self):
        if self.session_start_time is None:
            return
        self.session_elapsed_seconds = max(
            0, int((dt.datetime.now().replace(microsecond=0) - self.session_start_time).total_seconds())
        )
        h, r = divmod(self.session_elapsed_seconds, 3600)
        m, s = divmod(r, 60)
        self.duration_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _finalize_session(self):
        result = SessionService.finalize(self.data, self.session_start_time, self.last_telemetry)
        self.session_start_time = None
        if result is None:
            return
        self.last_session, session_summary, strava_summary = result
        save_data(self.data)
        self.last_session_label.setText(session_summary)
        self.total_stats_label.setText(f"Last cal: {self.last_session['calories']:.1f} kcal")
        self.status_label.setText(strava_summary)
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def auto_calibrate(self):
        self.stop()
        if self.device_combo.currentIndex() < 0:
            QtWidgets.QMessageBox.warning(self, "No device", "Select a treadmill mouse first.")
            return
        self.calibrator = CalibrationWorker(
            self.device_combo.currentData(),
            axis=self.axis_combo.currentText(),
            seconds=4,
        )
        self.calibrator.status.connect(self.status_label.setText)
        self.calibrator.failed.connect(self.show_error)
        self.calibrator.done.connect(self.apply_calibration)
        self.calibrator.start()

    def apply_calibration(self, result):
        self.deadzone_spin.setValue(int(result["deadzone"]))
        self.max_speed_spin.setValue(float(result["max_raw_speed"]))
        self.status_label.setText(
            f"Calibrated: dz={result['deadzone']}, samples={result['sample_count']}"
        )
        self.profile_ctrl.save()

    def reset_health(self):
        if self.worker is not None:
            self.worker.reset_health()
        for w in [self.steps_label, self.speed_label, self.distance_label,
                  self.calories_label, self.met_label]:
            w.setText(w.text().split(":")[0] + ": 0")

    # ------------------------------------------------------------------
    # SteamVR driver
    # ------------------------------------------------------------------

    def install_steamvr_driver(self):
        try:
            install_maratron_driver()
        except Exception as exc:
            self.show_error(f"Install failed:\n{exc}")
            return
        self.status_label.setText("SteamVR driver installed.")

    def uninstall_steamvr_driver(self):
        try:
            uninstall_maratron_driver()
        except Exception as exc:
            self.show_error(f"Uninstall failed:\n{exc}")
            return
        self.status_label.setText("SteamVR driver uninstalled.")

    # ------------------------------------------------------------------
    # Strava
    # ------------------------------------------------------------------

    def authorize_strava(self):
        self.profile_ctrl.read_ui_to_profile()
        try:
            url = build_authorization_url(self.data.get("strava", {}).get("client_id", ""))
        except Exception as exc:
            self.show_error(str(exc))
            return
        webbrowser.open(url)
        self.status_label.setText("Auth page opened.")

    def exchange_strava_code(self):
        self.profile_ctrl.read_ui_to_profile()
        strava = self.data.setdefault("strava", {})
        try:
            token = exchange_code(
                strava.get("client_id", ""),
                strava.get("client_secret", ""),
                self.strava_code_edit.text(),
            )
        except Exception as exc:
            self.show_error(f"Auth failed:\n{exc}")
            return
        strava.update({
            "access_token": token.get("access_token", ""),
            "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")),
            "expires_at": token.get("expires_at", 0),
        })
        self.strava_code_edit.clear()
        save_data(self.data)
        self.status_label.setText("Strava authorized.")

    def upload_last_session_to_strava(self):
        if not self.last_session:
            self.show_error("No session to upload.")
            return
        self.profile_ctrl.read_ui_to_profile()
        strava = self.data.setdefault("strava", {})
        try:
            result, token = upload_activity(strava, self.last_session)
        except Exception as exc:
            self.show_error(f"Upload failed:\n{exc}")
            return
        if token:
            strava.update({
                "access_token": token.get("access_token", strava.get("access_token", "")),
                "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")),
                "expires_at": token.get("expires_at", strava.get("expires_at", 0)),
            })
            save_data(self.data)
        self.status_label.setText(f"Uploaded: activity #{result.get('id', 'created')}")

    def show_error(self, msg):
        QtWidgets.QMessageBox.critical(self, "Maratron error", msg)

    # ------------------------------------------------------------------
    # Stats refresh
    # ------------------------------------------------------------------

    def _refresh_stats(self):
        sessions = self.data.get("sessions", [])
        has_sessions = len(sessions) > 0

        self.stats_empty.setVisible(not has_sessions)
        self.stats_chart.set_sessions(sessions)

        if has_sessions:
            total_dist = sum(s.get("distance_m", 0.0) for s in sessions)
            total_time = sum(s.get("elapsed_time", 0) for s in sessions)
            total_cal = sum(s.get("calories", 0.0) for s in sessions)
            self.stats_total_distance.setText(f"{total_dist / 1000.0:.2f} km")
            hrs = total_time // 3600
            mins = (total_time % 3600) // 60
            self.stats_total_time.setText(f"{hrs}h {mins}m" if hrs else f"{mins}m")
            self.stats_total_calories.setText(f"{total_cal:.0f} kcal")
            self.stats_session_count.setText(f"{len(sessions)} sessions")

            for i in reversed(range(self.stats_sessions_list.count())):
                widget = self.stats_sessions_list.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()

            for session in reversed(sessions[-20:]):
                row = self._build_session_row(session)
                self.stats_sessions_list.addWidget(row)
        else:
            self.stats_total_distance.setText("0.00 km")
            self.stats_total_time.setText("0m")
            self.stats_total_calories.setText("0 kcal")
            self.stats_session_count.setText("0 sessions")

    def _build_session_row(self, session):
        row = QtWidgets.QFrame()
        row.setObjectName("session_history_row")
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        at = session.get("activity_type", "Walk") or "Walk"
        dm = session.get("distance_m", 0.0)
        elapsed = session.get("elapsed_time", 0)
        cal = session.get("calories", 0.0)
        start = session.get("start_date_local", "")
        mins = elapsed // 60
        secs = elapsed % 60

        type_label = QtWidgets.QLabel(f"{at}")
        type_label.setObjectName("data_row_value")
        date_label = QtWidgets.QLabel(start[:16] if start else "")
        date_label.setObjectName("data_row_label")
        dist_label = QtWidgets.QLabel(f"{dm:.0f}m")
        dist_label.setObjectName("data_row_value")
        time_label = QtWidgets.QLabel(f"{mins}:{secs:02d}")
        time_label.setObjectName("data_row_value")
        cal_label = QtWidgets.QLabel(f"{cal:.0f} kcal")
        cal_label.setObjectName("data_row_value")

        layout.addWidget(type_label)
        layout.addWidget(date_label, 1)
        layout.addWidget(dist_label)
        layout.addWidget(time_label)
        layout.addWidget(cal_label)
        return row

    def _on_chart_metric_toggle(self, index):
        self.stats_chart.set_active_metric(index)
        if hasattr(self, 'stats_page') and self.stats_page:
            for i, btn in enumerate(self.stats_page.chart_toggle_buttons):
                btn.setChecked(i == index)

    # ------------------------------------------------------------------
    # Profile tile rendering
    # ------------------------------------------------------------------

    def _render_profile_tiles(self):
        for i in reversed(range(self.profiles_grid.count())):
            widget = self.profiles_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        profiles = self.data.get("profiles", {})
        has_profiles = len(profiles) > 0
        self.profiles_empty.setVisible(not has_profiles)

        if not has_profiles:
            return

        active_name = self.data.get("active_profile", "")
        names = list(profiles.keys())
        for idx, name in enumerate(names):
            tile = self._profile_tile(name, active=name == active_name)
            tile.mouseReleaseEvent = self._profile_tile_click_factory(name)
            self.profiles_grid.addWidget(tile, idx // 2, idx % 2)

    def _profile_tile(self, name, active=False):
        t = QtWidgets.QFrame()
        t.setObjectName("profile_tile")
        l = QtWidgets.QVBoxLayout(t)
        l.setContentsMargins(18, 14, 18, 14)
        title = QtWidgets.QLabel(name)
        title.setObjectName("profile_title")
        desc = QtWidgets.QLabel("Game profile")
        desc.setObjectName("card_subtitle")
        act = QtWidgets.QLabel("ACTIVE" if active else "AVAILABLE")
        act.setObjectName("small_caps")
        l.addWidget(title)
        l.addWidget(desc)
        l.addStretch(1)
        l.addWidget(act)
        return t

    def _profile_tile_click_factory(self, profile_name):
        def handler(event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.data["active_profile"] = profile_name
                self._refresh_profile_combo()
                self.profile_ctrl.load_profile_to_ui()
                self._on_profile_loaded()
                self._render_profile_tiles()
                self._update_profile_header()
                self._toast(f"Switched to {profile_name}")
        return handler

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def update_clock(self):
        self.clock_label.setText(dt.datetime.now().strftime("%-I:%M %p"))

    def closeEvent(self, event):
        self.stop()
        self.profile_ctrl.save()
        if self.output_mode_combo.currentData() == OUTPUT_UINPUT:
            try:
                uninstall_maratron_driver()
            except Exception:
                _log.exception("Failed to uninstall SteamVR driver on close")
        super().closeEvent(event)

    # --- Layout helpers ---

    @staticmethod
    def _footer_shortcut_hint(key, action, callback=None):
        hint = QtWidgets.QFrame()
        hint.setObjectName("footer_shortcut_button" if callback else "footer_shortcut_hint")
        hint.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        layout = QtWidgets.QHBoxLayout(hint)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        keycap = QtWidgets.QLabel(key)
        keycap.setObjectName("footer_keycap")
        keycap.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        label = QtWidgets.QLabel(action.upper())
        label.setObjectName("footer_action_label")

        layout.addWidget(keycap)
        layout.addWidget(label)

        if callback:
            hint.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

            def activate(event):
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    callback()
                    event.accept()
                else:
                    event.ignore()

            hint.mouseReleaseEvent = activate
            keycap.mouseReleaseEvent = activate
            label.mouseReleaseEvent = activate

        return hint

    @staticmethod
    def _build_empty_state_widget(title, body):
        frame = QtWidgets.QFrame()
        frame.setObjectName("empty_state")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon_label = QtWidgets.QLabel("\u2295")
        icon_label.setObjectName("empty_state_title")
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = icon_label.font()
        font.setPointSize(32)
        font.setBold(False)
        icon_label.setFont(font)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("empty_state_title")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)

        body_label = QtWidgets.QLabel(body)
        body_label.setObjectName("empty_state_body")
        body_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        body_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        return frame

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @staticmethod
    def run():
        import sys
        from app.bootstrap import build_app

        app = QtWidgets.QApplication(sys.argv)
        sp = Path(__file__).resolve().parent / "style.qss"
        if sp.exists():
            with open(sp) as f:
                app.setStyleSheet(f.read())
        w = build_app()
        w.show()
        sys.exit(app.exec())
