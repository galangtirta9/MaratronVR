import copy
import datetime as dt
import platform
import webbrowser
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from app.backends.uinput_backend import BUTTON_MAP
from app.core.calibration import CalibrationWorker
from app.core.device_scan import scan_pointer_devices
from app.core.driver_install import install_maratron_driver, uninstall_maratron_driver
from app.core.profiles import (
    DEFAULT_PROFILE,
    OUTPUT_HIDMAESTRO,
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
    OUTPUT_HIDMAESTRO: "HIDMaestro (Windows)",
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
        self._settings_open = False
        self._settings_history = []
        self._settings_history_blocked = False
        self._ctrl_pressed_for_settings = False

        self.setWindowTitle("MaratronVR")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 640)

        # --- All widgets ---
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

        self.output_mode_combo = QtWidgets.QComboBox()
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_UINPUT], OUTPUT_UINPUT)
        self.output_mode_combo.addItem(OUTPUT_LABELS[OUTPUT_STEAMVR], OUTPUT_STEAMVR)
        self.output_mode_combo.addItem(OUTPUT_LABELS.get(OUTPUT_HIDMAESTRO, "HIDMaestro (Windows)"), OUTPUT_HIDMAESTRO)

        self.device_combo = QtWidgets.QComboBox()
        self.refresh_devices_button = QtWidgets.QPushButton("Refresh")

        self.profile_combo = QtWidgets.QComboBox()
        self.new_profile_button = QtWidgets.QPushButton("New")
        self.duplicate_profile_button = QtWidgets.QPushButton("Dup")
        self.delete_profile_button = QtWidgets.QPushButton("Del")

        self.axis_combo = QtWidgets.QComboBox()
        self.axis_combo.addItems(["REL_Y", "REL_X"])
        self.omnidirectional_check = QtWidgets.QCheckBox("Omnidirectional / use REL_X + REL_Y")
        self.invert_check = QtWidgets.QCheckBox("Invert Y axis")
        self.deadzone_spin = QtWidgets.QSpinBox(); self.deadzone_spin.setRange(0, 50)
        self.smoothing_spin = QtWidgets.QDoubleSpinBox(); self.smoothing_spin.setRange(0.01, 1.0); self.smoothing_spin.setSingleStep(0.01)
        self.max_speed_spin = QtWidgets.QDoubleSpinBox(); self.max_speed_spin.setRange(1.0, 200.0); self.max_speed_spin.setSingleStep(1.0)
        self.poll_spin = QtWidgets.QSpinBox(); self.poll_spin.setRange(1, 50)
        self.auto_sprint_check = QtWidgets.QCheckBox("Auto sprint at max speed")
        self.sprint_threshold_spin = QtWidgets.QDoubleSpinBox(); self.sprint_threshold_spin.setRange(0.1, 1.0); self.sprint_threshold_spin.setSingleStep(0.01)
        self.sprint_button_combo = QtWidgets.QComboBox(); self.sprint_button_combo.addItems(BUTTON_MAP.keys())
        self.steamvr_sprint_button_combo = QtWidgets.QComboBox()
        for label, value in STEAMVR_BUTTONS.items():
            self.steamvr_sprint_button_combo.addItem(label, value)

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
        self.curve_editor = CurveEditor()

        # Telemetry
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
        self.treadmill_visual = TreadmillWidget()
        self.steps_label = QtWidgets.QLabel("Steps: 0")
        self.speed_label = QtWidgets.QLabel("Speed: 0.00 km/h")
        self.distance_label = QtWidgets.QLabel("Distance: 0 m")
        self.calories_label = QtWidgets.QLabel("Cal: 0 kcal")
        self.met_label = QtWidgets.QLabel("MET: 0.00")
        self.status_label = QtWidgets.QLabel("")
        self.clock_label = QtWidgets.QLabel()
        self.clock_timer = QtCore.QTimer(self)
        self.session_timer = QtCore.QTimer(self)
        self.speed_bar = QtWidgets.QProgressBar(); self.speed_bar.setRange(0, 100)

        # System info
        self.sys_os = QtWidgets.QLabel(platform.system() + " " + platform.release())
        self.sys_arch = QtWidgets.QLabel(platform.machine())
        self.sys_python = QtWidgets.QLabel(f"Python {platform.python_version()}")
        try:
            import psutil
            mem = psutil.virtual_memory()
            self.sys_ram = QtWidgets.QLabel(f"RAM: {mem.total // (1024**3)} GB ({(mem.available // (1024**2))} MB free)")
            cpu_count = psutil.cpu_count(logical=True)
            self.sys_cpu = QtWidgets.QLabel(f"CPU: {cpu_count} cores")
        except ImportError:
            self.sys_ram = QtWidgets.QLabel("RAM: install psutil for details")
            self.sys_cpu = QtWidgets.QLabel("CPU: install psutil for details")

        # Action buttons
        self.start_button = QtWidgets.QPushButton("Start"); self.start_button.setObjectName("start_button")
        self.stop_button = QtWidgets.QPushButton("Stop"); self.stop_button.setObjectName("stop_button")
        self.save_button = QtWidgets.QPushButton("Save")
        self.calibrate_button = QtWidgets.QPushButton("Auto calibrate")
        self.reset_health_button = QtWidgets.QPushButton("Reset health")
        self.install_driver_button = QtWidgets.QPushButton("Install")
        self.install_driver_button.setObjectName("install_driver_button")
        self.uninstall_driver_button = QtWidgets.QPushButton("Uninstall")

        self.strava_client_id_edit = QtWidgets.QLineEdit()
        self.strava_client_secret_edit = QtWidgets.QLineEdit()
        self.strava_client_secret_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.strava_code_edit = QtWidgets.QLineEdit()
        self.strava_authorize_button = QtWidgets.QPushButton("Auth"); self.strava_authorize_button.setObjectName("strava_authorize_button")
        self.strava_exchange_button = QtWidgets.QPushButton("Save")
        self.strava_upload_button = QtWidgets.QPushButton("Upload"); self.strava_upload_button.setObjectName("strava_upload_button")

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
        # --- Steam Input inspired top header (keyboard-only, no controller prompts) ---
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

        # --- Content pages ---
        self.content_stack = QtWidgets.QStackedWidget()
        self.content_stack.addWidget(self._build_dashboard())
        self.content_stack.addWidget(self._build_calibration())
        self.content_stack.addWidget(self._build_profiles())
        self.content_stack.addWidget(self._build_stats())
        # Tab 5: settings (hidden until toggled)
        self.settings_page = self._build_settings_page()
        self.content_stack.addWidget(self.settings_page)

        # --- Footer (Steam-style keyboard navigation, no logo/action saving) ---
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

        # --- Main layout ---
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
        self.update_profile_header()
        self.update_session_status(False)

    def _make_page(self):
        sc = QtWidgets.QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        w = QtWidgets.QWidget()
        w.setLayout(QtWidgets.QVBoxLayout())
        w.layout().setContentsMargins(48, 20, 48, 20)
        w.layout().setSpacing(16)
        sc.setWidget(w)
        return sc

    def _card(self, title, subtitle=None):
        c = QtWidgets.QFrame(); c.setObjectName("command_card")
        l = QtWidgets.QVBoxLayout(c); l.setContentsMargins(20, 16, 20, 16); l.setSpacing(10)
        lb = QtWidgets.QLabel(title); lb.setObjectName("card_title"); l.addWidget(lb)
        if subtitle:
            sb = QtWidgets.QLabel(subtitle); sb.setObjectName("card_subtitle"); sb.setWordWrap(True); l.addWidget(sb)
        return c

    def _stat_tile(self, label):
        t = QtWidgets.QFrame(); t.setObjectName("stat_tile")
        l = QtWidgets.QVBoxLayout(t); l.setContentsMargins(14, 10, 14, 10); label.setParent(t); l.addWidget(label)
        return t

    def _footer_shortcut_hint(self, key, action, callback=None):
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

    def _build_dashboard(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        lay.setContentsMargins(64, 16, 64, 16)
        hr = QtWidgets.QHBoxLayout(); hr.setSpacing(16)
        vc = self._card("TREADMILL"); vc.layout().addWidget(self.treadmill_visual, 1); hr.addWidget(vc, 3)
        ac = self._card("SESSION", "Start and stop sessions."); ac.setObjectName("dashboard_action_card")
        ac.layout().addWidget(self.session_state_label); ac.layout().addWidget(self.selected_profile_label); ac.layout().addSpacing(6)
        self.start_button.setText("Start"); self.stop_button.setText("Stop")
        ac.layout().addWidget(self.start_button); ac.layout().addWidget(self.stop_button); ac.layout().addStretch(1)
        hr.addWidget(ac, 2)
        lay.addLayout(hr)
        sg = QtWidgets.QGridLayout(); sg.setHorizontalSpacing(10); sg.setVerticalSpacing(10)
        for i, w in enumerate([self.speed_label, self.distance_label, self.calories_label, self.duration_label]):
            sg.addWidget(self._stat_tile(w), 0, i)
        lay.addLayout(sg)
        sg2 = QtWidgets.QGridLayout(); sg2.setHorizontalSpacing(10); sg2.setVerticalSpacing(10)
        for i, w in enumerate([self.sensor_status_label, self.joystick_status_label, self.steamvr_status_label, self.strava_status_label]):
            sg2.addWidget(self._stat_tile(w), i // 2, i % 2)
        lay.addLayout(sg2)
        lay.addStretch(1)
        return sc

    def _build_calibration(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        c = self._card("Noise Floor Calibration")
        c.layout().addWidget(QtWidgets.QLabel("Keep the belt still for 5 seconds. Maratron measures sensor noise and sets a baseline deadzone."))
        c.layout().addSpacing(8)
        self.cal_noise_label = QtWidgets.QLabel("Live noise: 0")
        self.cal_max_label = QtWidgets.QLabel("Max noise: —")
        self.cal_count_label = QtWidgets.QLabel("Samples: 0")
        c.layout().addWidget(self.cal_noise_label)
        c.layout().addWidget(self.cal_max_label)
        c.layout().addWidget(self.cal_count_label)
        c.layout().addSpacing(8)
        bb = QtWidgets.QHBoxLayout(); bb.setSpacing(8)
        bb.addWidget(self.calibrate_button); bb.addWidget(self.reset_health_button)
        c.layout().addLayout(bb)
        lay.addWidget(c)
        lay.addStretch(1)
        return sc

    def _build_profiles(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        pr = QtWidgets.QHBoxLayout(); pr.setSpacing(8)
        pr.addWidget(self.profile_combo, 1); pr.addWidget(self.new_profile_button); pr.addWidget(self.duplicate_profile_button); pr.addWidget(self.delete_profile_button)
        c = self._card("Profiles"); c.layout().addLayout(pr); lay.addWidget(c)
        gg = QtWidgets.QGridLayout(); gg.setHorizontalSpacing(10); gg.setVerticalSpacing(10)
        for i, n in enumerate(["BoneLab", "Half-Life: Alyx", "Skyrim VR", "Custom"]):
            gg.addWidget(self._profile_tile(n), i // 2, i % 2)
        lay.addLayout(gg)
        lay.addStretch(1)
        return sc

    def _build_stats(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        c1 = self._card("Last Session"); c1.layout().addWidget(self.last_session_label); c1.layout().addWidget(self.total_stats_label); lay.addWidget(c1)
        c2 = self._card("Strava"); c2.layout().addWidget(self.strava_status_label)
        sb = QtWidgets.QHBoxLayout(); sb.setSpacing(8)
        sb.addWidget(self.strava_authorize_button); sb.addWidget(self.strava_exchange_button); sb.addWidget(self.strava_upload_button)
        c2.layout().addLayout(sb); lay.addWidget(c2)
        lay.addStretch(1)
        return sc

    def _build_settings_page(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        lay.setContentsMargins(24, 12, 24, 12)

        # Settings header
        settings_header = QtWidgets.QFrame()
        settings_header.setObjectName("settings_header")
        settings_header_layout = QtWidgets.QHBoxLayout(settings_header)
        settings_header_layout.setContentsMargins(0, 0, 0, 10)
        settings_title = QtWidgets.QLabel("SETTINGS")
        settings_title.setObjectName("settings_title")
        settings_header_layout.addWidget(settings_title)
        settings_header_layout.addStretch(1)
        lay.addWidget(settings_header)

        # Sidebar + content
        hbox = QtWidgets.QHBoxLayout(); hbox.setSpacing(20)
        sidebar = QtWidgets.QFrame(); sidebar.setObjectName("menu_sidebar")
        sl = QtWidgets.QVBoxLayout(sidebar); sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(2)
        self.menu_list = QtWidgets.QListWidget(); self.menu_list.setObjectName("menu_list")
        self.menu_list.setIconSize(QtCore.QSize(20, 20))
        entries = [
            ("System", "system"),
            ("Input Device", "input_device"),
            ("Movement", "movement"),
            ("Sprint", "sprint"),
            ("Body & Sensor", "body_sensor"),
            ("SteamVR", "steamvr"),
            ("Strava", "strava"),
            ("Developer", "developer"),
        ]
        for label, icon_name in entries:
            item = QtWidgets.QListWidgetItem(f"  {label}")
            icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / f"{icon_name}.svg"
            if icon_path.exists():
                item.setIcon(QtGui.QIcon(str(icon_path)))
            self.menu_list.addItem(item)
        self.menu_list.setCurrentRow(0)
        sl.addWidget(self.menu_list)
        hbox.addWidget(sidebar, 2)

        self.menu_stack = QtWidgets.QStackedWidget(); self.menu_stack.setObjectName("menu_stack")
        hbox.addWidget(self.menu_stack, 7)
        lay.addLayout(hbox)

        def menu_page(title, *cards):
            p = self._make_page(); pl = p.widget().layout(); pl.setContentsMargins(12, 4, 12, 4)
            pl.addWidget(self._section_title(title))
            for c in cards: pl.addWidget(c)
            pl.addStretch(1); return p

        # System card with hardware info
        sys_card = self._card("System")
        for lb in [self.sys_os, self.sys_arch, self.sys_cpu, self.sys_ram, self.sys_python]:
            sys_card.layout().addWidget(lb)
        sys_save = QtWidgets.QPushButton("Save Profile"); sys_save.clicked.connect(self.save)
        sys_card.layout().addWidget(sys_save)

        input_card = self._card("Input Device")
        ifm = QtWidgets.QFormLayout(); ifm.addRow("Output mode", self.output_mode_combo)
        dr = QtWidgets.QHBoxLayout(); dr.setSpacing(8); dr.addWidget(self.device_combo, 1); dr.addWidget(self.refresh_devices_button)
        input_card.layout().addLayout(ifm); input_card.layout().addLayout(dr)

        move_card = self._card("Movement Tuning")
        sf = QtWidgets.QFormLayout(); sf.setSpacing(10)
        sf.addRow("Axis", self.axis_combo); sf.addRow("", self.omnidirectional_check); sf.addRow("", self.invert_check)
        sf.addRow("Deadzone", self.deadzone_spin); sf.addRow("Smoothing", self.smoothing_spin); sf.addRow("Max speed", self.max_speed_spin); sf.addRow("Interval", self.poll_spin)
        move_card.layout().addLayout(sf)
        curve_card = self._card("Response Curve")
        curve_card.layout().addWidget(QtWidgets.QLabel("Left-click add, drag move, right-click delete"))
        curve_card.layout().addWidget(self.curve_editor)

        sprint_card = self._card("Sprint")
        spf = QtWidgets.QFormLayout(); spf.setSpacing(10)
        spf.addRow("", self.auto_sprint_check); spf.addRow("Threshold", self.sprint_threshold_spin); spf.addRow("UInput button", self.sprint_button_combo); spf.addRow("SteamVR", self.steamvr_sprint_button_combo)
        sprint_card.layout().addLayout(spf)

        body_card = self._card("Body & Sensor")
        bf = QtWidgets.QFormLayout(); bf.setSpacing(10)
        bf.addRow("Height", self.height_spin); bf.addRow("", self.stride_estimate_label); bf.addRow("Weight", self.weight_spin); bf.addRow("Age", self.age_spin); bf.addRow("Gender", self.gender_combo)
        bf.addRow("DPI preset", self.mouse_dpi_combo); bf.addRow("Custom DPI", self.custom_dpi_spin); bf.addRow("Poll rate", self.polling_rate_spin); bf.addRow("Incline", self.incline_spin)
        body_card.layout().addLayout(bf)

        steamvr_card = self._card("SteamVR")
        sdr = QtWidgets.QHBoxLayout(); sdr.setSpacing(8); sdr.addWidget(self.install_driver_button); sdr.addWidget(self.uninstall_driver_button)
        steamvr_card.layout().addLayout(sdr)
        steamvr_card.layout().addWidget(QtWidgets.QLabel("Restart SteamVR after changing driver."))

        strava_card = self._card("Strava")
        sf2 = QtWidgets.QFormLayout(); sf2.setSpacing(10)
        sf2.addRow("Client ID", self.strava_client_id_edit); sf2.addRow("Secret", self.strava_client_secret_edit); sf2.addRow("Auth code", self.strava_code_edit)
        strava_card.layout().addLayout(sf2)

        diag_card = self._card("Developer Diagnostics")
        dg = QtWidgets.QGridLayout()
        for i, w in enumerate([self.raw_label, self.filtered_label, self.output_label, self.movement_label, self.steps_label, self.met_label]):
            dg.addWidget(self._stat_tile(w), i // 2, i % 2)
        diag_card.layout().addLayout(dg)

        for page in [
            menu_page("System", sys_card),
            menu_page("Input Device", input_card),
            menu_page("Movement", move_card, curve_card),
            menu_page("Sprint", sprint_card),
            menu_page("Body & Sensor", body_card),
            menu_page("SteamVR", steamvr_card),
            menu_page("Strava", strava_card),
            menu_page("Developer", diag_card),
        ]:
            self.menu_stack.addWidget(page)

        self.menu_list.currentRowChanged.connect(self.on_settings_entry_changed)
        return sc

    def _section_title(self, text):
        lb = QtWidgets.QLabel(text); lb.setObjectName("section_title"); return lb

    def _profile_tile(self, name):
        t = QtWidgets.QFrame(); t.setObjectName("profile_tile")
        l = QtWidgets.QVBoxLayout(t); l.setContentsMargins(18, 14, 18, 14)
        title = QtWidgets.QLabel(name); title.setObjectName("profile_title")
        desc = QtWidgets.QLabel("Game profile"); desc.setObjectName("card_subtitle")
        act = QtWidgets.QLabel("ACTIVE" if name == self.current_profile_name() else "AVAILABLE"); act.setObjectName("small_caps")
        l.addWidget(title); l.addWidget(desc); l.addStretch(1); l.addWidget(act)
        return t

    # --- Tab management ---
    def switch_tab(self, name):
        idx = ["Dashboard", "Calibration", "Profiles", "Stats"].index(name)
        self.content_stack.setCurrentIndex(idx)
        for b in self.tab_buttons:
            b.setChecked(b.text() == name.upper())
        self._settings_open = False

    def cycle_tab(self, direction):
        tabs = ["Dashboard", "Calibration", "Profiles", "Stats"]
        current = self.content_stack.currentIndex()
        if current not in range(len(tabs)):
            current = 0
        self.switch_tab(tabs[(current + direction) % len(tabs)])

    def update_profile_header(self):
        profile_name = self.current_profile_name()
        self.controller_label.setText(f"Profile: {profile_name}")
        initial = (profile_name.strip()[:1] or "M").upper()
        self.profile_avatar_label.setText(initial)

    def update_session_status(self, active):
        self.session_status_pill.setText("")
        self.session_status_pill.setProperty("status", "active" if active else "inactive")
        self.session_status_pill.style().unpolish(self.session_status_pill)
        self.session_status_pill.style().polish(self.session_status_pill)

    def toggle_settings(self):
        self._settings_open = not self._settings_open
        if self._settings_open:
            self._settings_history.clear()
            self.content_stack.setCurrentIndex(4)  # settings page
        else:
            # Return to current dashboard
            self.tab_buttons[0].setChecked(True)
            for b in self.tab_buttons:
                b.setChecked(b is self.tab_buttons[0])
            self.content_stack.setCurrentIndex(0)

    def close_settings(self):
        if self._settings_open:
            self.toggle_settings()

    def go_back(self):
        if self._settings_open:
            self.back_settings_entry()

    def on_settings_entry_changed(self, row):
        if row < 0:
            return
        previous_row = self.menu_stack.currentIndex()
        if not self._settings_history_blocked and previous_row >= 0 and previous_row != row:
            self._settings_history.append(previous_row)
        self.menu_stack.setCurrentIndex(row)

    def back_settings_entry(self):
        if not self._settings_history:
            return
        previous_row = self._settings_history.pop()
        self._settings_history_blocked = True
        try:
            self.menu_list.setCurrentRow(previous_row)
            self.menu_stack.setCurrentIndex(previous_row)
        finally:
            self._settings_history_blocked = False

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            super().keyPressEvent(event)
            return

        if event.key() in (QtCore.Qt.Key.Key_Control, QtCore.Qt.Key.Key_Meta):
            self._ctrl_pressed_for_settings = True
            event.accept()
            return

        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed_for_settings = False

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            super().keyReleaseEvent(event)
            return

        if event.key() in (QtCore.Qt.Key.Key_Control, QtCore.Qt.Key.Key_Meta):
            if self._ctrl_pressed_for_settings:
                self.toggle_settings()
                event.accept()
            self._ctrl_pressed_for_settings = False
            return

        super().keyReleaseEvent(event)

    # --- Remaining methods unchanged ---
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
            self.output_mode_combo, self.axis_combo, self.omnidirectional_check, self.invert_check,
            self.deadzone_spin, self.smoothing_spin, self.max_speed_spin, self.poll_spin,
            self.auto_sprint_check, self.sprint_threshold_spin, self.sprint_button_combo, self.steamvr_sprint_button_combo,
            self.height_spin, self.weight_spin, self.age_spin, self.gender_combo,
            self.mouse_dpi_combo, self.custom_dpi_spin, self.polling_rate_spin, self.incline_spin,
            self.strava_client_id_edit, self.strava_client_secret_edit,
        ]
        for w in widgets:
            if hasattr(w, "valueChanged"): w.valueChanged.connect(self.on_config_changed)
            if hasattr(w, "currentTextChanged"): w.currentTextChanged.connect(self.on_config_changed)
            if hasattr(w, "currentIndexChanged"): w.currentIndexChanged.connect(self.on_config_changed)
            if hasattr(w, "stateChanged"): w.stateChanged.connect(self.on_config_changed)
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
            idx = self.device_combo.findData(selected)
            if idx >= 0: self.device_combo.setCurrentIndex(idx)
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
        hc = float(health.get("height_cm", self._height_from_stride(float(health.get("stride_length_m", 0.72)))))
        self.height_spin.setValue(hc)
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
        self.update_axis_controls(); self.update_stride_estimate(); self.update_dpi_controls()
        self.selected_profile_label.setText(f"Profile: {self.data['active_profile']}")
        self.strava_status_label.setText("Strava: Connected" if self.data.get("strava", {}).get("access_token") else "Strava: Not Connected")
        self.update_profile_header()

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
        hc = self.height_spin.value()
        ex = profile.get("health", {})
        profile["health"] = {
            "height_cm": hc, "stride_length_m": self._stride_from_height(hc),
            "user_weight_kg": self.weight_spin.value(), "age_years": self.age_spin.value(),
            "gender": self.gender_combo.currentText(), "mouse_dpi": self._current_dpi_value(),
            "polling_rate_hz": self.polling_rate_spin.value(), "incline_degrees": self.incline_spin.value(),
            "manual_friction_multiplier": ex.get("manual_friction_multiplier", 1.0),
            "calorie_factor": ex.get("calorie_factor", 1.0),
        }
        self.data["active_profile"] = name
        return profile

    def on_curve_changed(self, points): self.on_config_changed()

    def on_config_changed(self):
        if not self.profile_combo.currentText(): return
        self.update_axis_controls()
        self.read_ui_to_profile()
        if self.worker is not None:
            self.worker.update_config(make_profile_config(self.data))

    def update_axis_controls(self): self.axis_combo.setEnabled(not self.omnidirectional_check.isChecked())
    def update_stride_estimate(self): self.stride_estimate_label.setText(f"Estimated stride: {self._stride_from_height(self.height_spin.value()):.2f} m")
    def update_dpi_controls(self): self.custom_dpi_spin.setEnabled(self.mouse_dpi_combo.currentData() == CUSTOM_DPI_VALUE)

    def _current_dpi_value(self):
        v = self.mouse_dpi_combo.currentData()
        return self.custom_dpi_spin.value() if v == CUSTOM_DPI_VALUE else float(v or 1600.0)

    def _set_dpi_value(self, dpi):
        idpi = int(round(dpi))
        idx = self.mouse_dpi_combo.findData(idpi)
        if idx >= 0: self.mouse_dpi_combo.setCurrentIndex(idx)
        else:
            ci = self.mouse_dpi_combo.findData(CUSTOM_DPI_VALUE)
            if ci >= 0: self.mouse_dpi_combo.setCurrentIndex(ci)
        self.custom_dpi_spin.setValue(float(dpi))

    @staticmethod
    def _stride_from_height(h): return max(0.1, float(h) * 0.415 / 100.0)
    @staticmethod
    def _height_from_stride(s): return max(80.0, min(230.0, float(s) * 100.0 / 0.415))

    def on_profile_selected(self, name):
        if not name: return
        self.data["active_profile"] = name; self.load_profile_to_ui(); self.update_profile_header(); self.on_config_changed()

    def new_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New profile", "Name:")
        name = name.strip()
        if not ok or not name: return
        if name in self.data["profiles"]:
            QtWidgets.QMessageBox.warning(self, "Exists", "That profile already exists."); return
        self.data["profiles"][name] = copy.deepcopy(DEFAULT_PROFILE)
        self.data["active_profile"] = name; self.refresh_profiles(); self.load_profile_to_ui(); self.save()

    def duplicate_profile(self):
        cur = self.current_profile_name()
        name, ok = QtWidgets.QInputDialog.getText(self, "Duplicate", "New name:")
        name = name.strip()
        if not ok or not name: return
        if name in self.data["profiles"]:
            QtWidgets.QMessageBox.warning(self, "Exists", "That profile already exists."); return
        self.data["profiles"][name] = copy.deepcopy(self.data["profiles"][cur])
        self.data["active_profile"] = name; self.refresh_profiles(); self.load_profile_to_ui(); self.save()

    def delete_profile(self):
        if len(self.data["profiles"]) <= 1:
            QtWidgets.QMessageBox.warning(self, "Cannot delete", "Keep at least one profile."); return
        name = self.current_profile_name()
        if QtWidgets.QMessageBox.question(self, "Delete", f"Delete '{name}'?") != QtWidgets.QMessageBox.StandardButton.Yes: return
        del self.data["profiles"][name]; self.data["active_profile"] = list(self.data["profiles"].keys())[0]
        self.refresh_profiles(); self.load_profile_to_ui(); self.save()

    def save(self):
        self.read_ui_to_profile(); save_data(self.data); self.status_label.setText("Saved")

    def start(self):
        if self.worker is not None and self.worker.isRunning(): return
        self.save()
        self.session_start_time = dt.datetime.now().replace(microsecond=0)
        self.session_elapsed_seconds = 0; self.session_state_label.setText("Running")
        self.update_session_status(True)
        self.joystick_status_label.setText("Joystick: Active"); self.session_timer.start(1000)
        self.last_telemetry = None; self.last_session = None
        self.worker = TreadmillWorker(make_profile_config(self.data))
        self.worker.telemetry.connect(self.update_telemetry)
        self.worker.status.connect(self.status_label.setText)
        self.worker.failed.connect(self.show_error)
        self.worker.start()

    def stop(self):
        if self.worker is not None:
            self.worker.stop(); self.worker.wait(1500); self.worker = None
            self.session_timer.stop(); self.session_state_label.setText("Ready")
            self.update_session_status(False)
            self.treadmill_visual.set_output_percent(0)
            self.joystick_status_label.setText("Joystick: Idle")
            self.treadmill_visual.set_speed(0.0); self.treadmill_visual.set_output_percent(0)
            self._finalize_session()

    def auto_calibrate(self):
        self.stop()
        if self.device_combo.currentIndex() < 0:
            QtWidgets.QMessageBox.warning(self, "No device", "Select a treadmill mouse first."); return
        self.calibrator = CalibrationWorker(self.device_combo.currentData(), axis=self.axis_combo.currentText(), seconds=4)
        self.calibrator.status.connect(self.status_label.setText)
        self.calibrator.failed.connect(self.show_error)
        self.calibrator.done.connect(self.apply_calibration)
        self.calibrator.start()

    def apply_calibration(self, result):
        self.deadzone_spin.setValue(int(result["deadzone"]))
        self.max_speed_spin.setValue(float(result["max_raw_speed"]))
        self.status_label.setText(f"Calibrated: dz={result['deadzone']}, samples={result['sample_count']}")
        self.save()

    def reset_health(self):
        if self.worker is not None: self.worker.reset_health()
        for w in [self.steps_label, self.speed_label, self.distance_label, self.calories_label, self.met_label]:
            w.setText(w.text().split(":")[0] + ": 0")

    def install_steamvr_driver(self):
        try: install_maratron_driver()
        except Exception as exc: self.show_error(f"Install failed:\n{exc}"); return
        self.status_label.setText("SteamVR driver installed.")

    def uninstall_steamvr_driver(self):
        try: uninstall_maratron_driver()
        except Exception as exc: self.show_error(f"Uninstall failed:\n{exc}"); return
        self.status_label.setText("SteamVR driver uninstalled.")

    def authorize_strava(self):
        self.read_ui_to_profile()
        try: url = build_authorization_url(self.data.get("strava", {}).get("client_id", ""))
        except Exception as exc: self.show_error(str(exc)); return
        webbrowser.open(url); self.status_label.setText("Auth page opened.")

    def exchange_strava_code(self):
        self.read_ui_to_profile(); strava = self.data.setdefault("strava", {})
        try:
            token = exchange_code(strava.get("client_id", ""), strava.get("client_secret", ""), self.strava_code_edit.text())
        except Exception as exc: self.show_error(f"Auth failed:\n{exc}"); return
        strava.update({"access_token": token.get("access_token", ""), "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")), "expires_at": token.get("expires_at", 0)})
        self.strava_code_edit.clear(); save_data(self.data); self.status_label.setText("Strava authorized.")

    def upload_last_session_to_strava(self):
        if not self.last_session: self.show_error("No session to upload."); return
        self.read_ui_to_profile(); strava = self.data.setdefault("strava", {})
        try: result, token = upload_activity(strava, self.last_session)
        except Exception as exc: self.show_error(f"Upload failed:\n{exc}"); return
        if token:
            strava.update({"access_token": token.get("access_token", strava.get("access_token", "")), "refresh_token": token.get("refresh_token", strava.get("refresh_token", "")), "expires_at": token.get("expires_at", strava.get("expires_at", 0))})
            save_data(self.data)
        self.status_label.setText(f"Uploaded: activity #{result.get('id', 'created')}")

    def show_error(self, msg): QtWidgets.QMessageBox.critical(self, "Maratron error", msg)

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
        self.session_state_label.setText("Running" if sk >= 8.0 else ("Walking" if sk > 0.2 else "Ready"))

    def update_session_duration(self):
        if self.session_start_time is None: return
        self.session_elapsed_seconds = max(0, int((dt.datetime.now().replace(microsecond=0) - self.session_start_time).total_seconds()))
        h, r = divmod(self.session_elapsed_seconds, 3600); m, s = divmod(r, 60)
        self.duration_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _finalize_session(self):
        if self.session_start_time is None or self.last_telemetry is None: self.session_start_time = None; return
        ended = dt.datetime.now().replace(microsecond=0)
        elapsed = max(1, int((ended - self.session_start_time).total_seconds()))
        dm = float(self.last_telemetry.get("distance_m", 0.0))
        avg = (dm / elapsed) * 3.6 if elapsed > 0 else 0.0
        thr = float(self.data.get("strava", {}).get("auto_detect_run_kmh", 8.0) or 8.0)
        at = "Run" if avg >= thr else "Walk"
        self.last_session = {
            "name": "Maratron Session", "activity_type": at,
            "start_date_local": self.session_start_time.isoformat(), "elapsed_time": elapsed,
            "distance_m": dm, "calories": float(self.last_telemetry.get("calories", 0.0)),
            "average_speed_kmh": avg, "description": "Manual treadmill session by MaratronVR.",
        }
        self.session_start_time = None
        self.last_session_label.setText(f"{at}  {dm:.1f}m  {avg:.2f}km/h  {elapsed}s")
        self.total_stats_label.setText(f"Last cal: {self.last_session['calories']:.1f} kcal")
        self.status_label.setText(f"Strava ready: {at}, {dm:.1f}m, {avg:.2f}km/h")

    def closeEvent(self, event):
        self.stop(); self.save()
        if self.output_mode_combo.currentData() == OUTPUT_UINPUT:
            try: uninstall_maratron_driver()
            except: pass
        super().closeEvent(event)

    def update_clock(self):
        self.clock_label.setText(dt.datetime.now().strftime("%-I:%M %p"))

    @staticmethod
    def _set_combo_data(c, v):
        i = c.findData(v)
        if i >= 0: c.setCurrentIndex(i)

    @staticmethod
    def run():
        import sys
        app = QtWidgets.QApplication(sys.argv)
        sp = Path(__file__).resolve().parent / "style.qss"
        if sp.exists():
            with open(sp) as f: app.setStyleSheet(f.read())
        w = MainWindow(); w.show(); sys.exit(app.exec())