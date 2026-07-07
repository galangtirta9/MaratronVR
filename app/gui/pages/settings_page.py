from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets


class SettingsPage(QtWidgets.QWidget):
    """Settings overlay: sidebar menu + stacked sub-pages for all config sections."""

    def __init__(
        self,
        sys_os,
        sys_arch,
        sys_cpu,
        sys_ram,
        sys_python,
        output_mode_combo,
        device_combo,
        refresh_devices_button,
        axis_combo,
        omnidirectional_check,
        invert_check,
        deadzone_spin,
        smoothing_spin,
        max_speed_spin,
        poll_spin,
        auto_sprint_check,
        sprint_threshold_spin,
        sprint_button_combo,
        steamvr_sprint_button_combo,
        height_spin,
        stride_estimate_label,
        weight_spin,
        age_spin,
        gender_combo,
        mouse_dpi_combo,
        custom_dpi_spin,
        polling_rate_spin,
        incline_spin,
        curve_editor,
        install_driver_button,
        uninstall_driver_button,
        strava_client_id_edit,
        strava_client_secret_edit,
        strava_code_edit,
        raw_label,
        filtered_label,
        output_label,
        movement_label,
        steps_label,
        met_label,
        save_callback,
        parent=None,
    ):
        super().__init__(parent)
        self.save_callback = save_callback
        self.menu_list = None
        self.menu_stack = None
        self._settings_history = []
        self._history_blocked = False

        # Build sub-page cards with injected widgets
        self._sys_os = sys_os
        self._sys_arch = sys_arch
        self._sys_cpu = sys_cpu
        self._sys_ram = sys_ram
        self._sys_python = sys_python

        self._output_mode_combo = output_mode_combo
        self._device_combo = device_combo
        self._refresh_devices_button = refresh_devices_button

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

        self._install_driver_button = install_driver_button
        self._uninstall_driver_button = uninstall_driver_button

        self._strava_client_id_edit = strava_client_id_edit
        self._strava_client_secret_edit = strava_client_secret_edit
        self._strava_code_edit = strava_code_edit

        self._raw_label = raw_label
        self._filtered_label = filtered_label
        self._output_label = output_label
        self._movement_label = movement_label
        self._steps_label = steps_label
        self._met_label = met_label

        self._build()

    def _build(self):
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
        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(20)

        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("menu_sidebar")
        sl = QtWidgets.QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 4, 0, 4)
        sl.setSpacing(0)

        self.menu_list = QtWidgets.QListWidget()
        self.menu_list.setObjectName("menu_list")
        self.menu_list.setIconSize(QtCore.QSize(24, 24))
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
            item = QtWidgets.QListWidgetItem(label)
            item.setSizeHint(QtCore.QSize(0, 46))
            icon_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "assets" / "icons" / f"{icon_name}.svg"
            )
            if icon_path.exists():
                item.setIcon(QtGui.QIcon(str(icon_path)))
            self.menu_list.addItem(item)

        self.menu_list.setCurrentRow(0)
        sl.addWidget(self.menu_list)
        hbox.addWidget(sidebar, 2)

        self.menu_stack = QtWidgets.QStackedWidget()
        self.menu_stack.setObjectName("menu_stack")
        hbox.addWidget(self.menu_stack, 7)
        lay.addLayout(hbox)

        # Build sub-pages
        for page in [
            self._build_system_page(),
            self._build_input_device_page(),
            self._build_movement_page(),
            self._build_sprint_page(),
            self._build_body_sensor_page(),
            self._build_steamvr_page(),
            self._build_strava_page(),
            self._build_developer_page(),
        ]:
            self.menu_stack.addWidget(page)

        self.menu_list.currentRowChanged.connect(self._on_entry_changed)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(sc)

    # --- Sub-page builders ---

    def _build_system_page(self):
        p = self._menu_page("System")
        sys_card = self._card("System")
        for lb in [
            self._sys_os, self._sys_arch, self._sys_cpu,
            self._sys_ram, self._sys_python,
        ]:
            sys_card.layout().addWidget(lb)
        self.sys_save_button = QtWidgets.QPushButton("Save Profile")
        if self.save_callback is not None:
            self.sys_save_button.clicked.connect(self.save_callback)
        sys_card.layout().addWidget(self.sys_save_button)
        p.widget().layout().addWidget(sys_card)
        return p

    def _build_input_device_page(self):
        p = self._menu_page("Input Device")
        input_card = self._card("Input Device")
        ifm = QtWidgets.QFormLayout()
        ifm.addRow("Output mode", self._output_mode_combo)
        dr = QtWidgets.QHBoxLayout()
        dr.setSpacing(8)
        dr.addWidget(self._device_combo, 1)
        dr.addWidget(self._refresh_devices_button)
        input_card.layout().addLayout(ifm)
        input_card.layout().addLayout(dr)
        p.widget().layout().addWidget(input_card)
        return p

    def _build_movement_page(self):
        p = self._menu_page("Movement")
        move_card = self._card("Movement Tuning")
        sf = QtWidgets.QFormLayout()
        sf.setSpacing(10)
        sf.addRow("Axis", self._axis_combo)
        sf.addRow("", self._omnidirectional_check)
        sf.addRow("", self._invert_check)
        sf.addRow("Deadzone", self._deadzone_spin)
        sf.addRow("Smoothing", self._smoothing_spin)
        sf.addRow("Max speed", self._max_speed_spin)
        sf.addRow("Interval", self._poll_spin)
        move_card.layout().addLayout(sf)
        p.widget().layout().addWidget(move_card)

        curve_card = self._card("Response Curve")
        curve_card.layout().addWidget(
            QtWidgets.QLabel("Left-click add, drag move, right-click delete")
        )
        curve_card.layout().addWidget(self._curve_editor)
        p.widget().layout().addWidget(curve_card)
        return p

    def _build_sprint_page(self):
        p = self._menu_page("Sprint")
        sprint_card = self._card("Sprint")
        spf = QtWidgets.QFormLayout()
        spf.setSpacing(10)
        spf.addRow("", self._auto_sprint_check)
        spf.addRow("Threshold", self._sprint_threshold_spin)
        spf.addRow("UInput button", self._sprint_button_combo)
        spf.addRow("SteamVR", self._steamvr_sprint_button_combo)
        sprint_card.layout().addLayout(spf)
        p.widget().layout().addWidget(sprint_card)
        return p

    def _build_body_sensor_page(self):
        p = self._menu_page("Body & Sensor")
        body_card = self._card("Body & Sensor")
        bf = QtWidgets.QFormLayout()
        bf.setSpacing(10)
        bf.addRow("Height", self._height_spin)
        bf.addRow("", self._stride_estimate_label)
        bf.addRow("Weight", self._weight_spin)
        bf.addRow("Age", self._age_spin)
        bf.addRow("Gender", self._gender_combo)
        bf.addRow("DPI preset", self._mouse_dpi_combo)
        bf.addRow("Custom DPI", self._custom_dpi_spin)
        bf.addRow("Poll rate", self._polling_rate_spin)
        bf.addRow("Incline", self._incline_spin)
        body_card.layout().addLayout(bf)
        p.widget().layout().addWidget(body_card)
        return p

    def _build_steamvr_page(self):
        p = self._menu_page("SteamVR")
        steamvr_card = self._card("SteamVR")
        sdr = QtWidgets.QHBoxLayout()
        sdr.setSpacing(8)
        sdr.addWidget(self._install_driver_button)
        sdr.addWidget(self._uninstall_driver_button)
        steamvr_card.layout().addLayout(sdr)
        steamvr_card.layout().addWidget(
            QtWidgets.QLabel("Restart SteamVR after changing driver.")
        )
        p.widget().layout().addWidget(steamvr_card)
        return p

    def _build_strava_page(self):
        p = self._menu_page("Strava")
        strava_card = self._card("Strava")
        sf2 = QtWidgets.QFormLayout()
        sf2.setSpacing(10)
        sf2.addRow("Client ID", self._strava_client_id_edit)
        sf2.addRow("Secret", self._strava_client_secret_edit)
        sf2.addRow("Auth code", self._strava_code_edit)
        strava_card.layout().addLayout(sf2)
        p.widget().layout().addWidget(strava_card)
        return p

    def _build_developer_page(self):
        p = self._menu_page("Developer")
        diag_card = self._card("Developer Diagnostics")
        dg = QtWidgets.QGridLayout()
        for i, w in enumerate(
            [
                self._raw_label,
                self._filtered_label,
                self._output_label,
                self._movement_label,
                self._steps_label,
                self._met_label,
            ]
        ):
            dg.addWidget(self._stat_tile(w), i // 2, i % 2)
        diag_card.layout().addLayout(dg)
        p.widget().layout().addWidget(diag_card)
        return p

    # --- Entry navigation ---

    def _on_entry_changed(self, row):
        if row < 0:
            return
        previous_row = self.menu_stack.currentIndex()
        if not self._history_blocked and previous_row >= 0 and previous_row != row:
            self._settings_history.append(previous_row)
        self.menu_stack.setCurrentIndex(row)

    def go_back(self):
        if not self._settings_history:
            return
        previous_row = self._settings_history.pop()
        self._history_blocked = True
        try:
            self.menu_list.setCurrentRow(previous_row)
            self.menu_stack.setCurrentIndex(previous_row)
        finally:
            self._history_blocked = False

    # --- Shared helpers ---

    @staticmethod
    def _make_page():
        sc = QtWidgets.QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        w = QtWidgets.QWidget()
        w.setLayout(QtWidgets.QVBoxLayout())
        w.layout().setContentsMargins(48, 20, 48, 20)
        w.layout().setSpacing(16)
        sc.setWidget(w)
        return sc

    @staticmethod
    def _card(title, subtitle=None):
        c = QtWidgets.QFrame()
        c.setObjectName("command_card")
        l = QtWidgets.QVBoxLayout(c)
        l.setContentsMargins(20, 16, 20, 16)
        l.setSpacing(10)
        lb = QtWidgets.QLabel(title)
        lb.setObjectName("card_title")
        l.addWidget(lb)
        if subtitle:
            sb = QtWidgets.QLabel(subtitle)
            sb.setObjectName("card_subtitle")
            sb.setWordWrap(True)
            l.addWidget(sb)
        return c

    @staticmethod
    def _stat_tile(label):
        t = QtWidgets.QFrame()
        t.setObjectName("stat_tile")
        l = QtWidgets.QVBoxLayout(t)
        l.setContentsMargins(14, 10, 14, 10)
        label.setParent(t)
        l.addWidget(label)
        return t

    @staticmethod
    def _menu_page(title):
        sc = QtWidgets.QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        w = QtWidgets.QWidget()
        w.setLayout(QtWidgets.QVBoxLayout())
        w.layout().setContentsMargins(12, 4, 12, 4)
        w.layout().setSpacing(16)
        section = QtWidgets.QLabel(title)
        section.setObjectName("section_title")
        w.layout().addWidget(section)
        sc.setWidget(w)
        return sc