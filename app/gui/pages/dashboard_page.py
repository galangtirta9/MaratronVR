from PyQt6 import QtCore, QtWidgets


class DashboardPage(QtWidgets.QWidget):
    """Dashboard tab: treadmill visual, session controls, stats, status."""

    def __init__(
        self,
        treadmill_visual,
        session_state_label,
        selected_profile_label,
        start_button,
        stop_button,
        speed_label,
        distance_label,
        calories_label,
        duration_label,
        sensor_status_label,
        joystick_status_label,
        steamvr_status_label,
        strava_status_label,
        sensitivity_slider,
        sensitivity_label,
        parent=None,
    ):
        super().__init__(parent)
        self.treadmill_visual = treadmill_visual
        self.session_state_label = session_state_label
        self.selected_profile_label = selected_profile_label
        self.start_button = start_button
        self.stop_button = stop_button
        self.speed_label = speed_label
        self.distance_label = distance_label
        self.calories_label = calories_label
        self.duration_label = duration_label
        self.sensor_status_label = sensor_status_label
        self.joystick_status_label = joystick_status_label
        self.steamvr_status_label = steamvr_status_label
        self.strava_status_label = strava_status_label
        self.sensitivity_slider = sensitivity_slider
        self.sensitivity_label = sensitivity_label
        self.sensitivity_slider = sensitivity_slider
        self.sensitivity_label = sensitivity_label

        self._build()

    def _build(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        lay.setContentsMargins(64, 16, 64, 16)

        # Treadmill visual + session controls row
        hr = QtWidgets.QHBoxLayout()
        hr.setSpacing(16)

        vc = self._card("TREADMILL")
        vc.layout().addWidget(self.treadmill_visual, 1)
        hr.addWidget(vc, 3)

        ac = self._card("SESSION", "Start and stop sessions.")
        ac.setObjectName("dashboard_action_card")
        ac.layout().addWidget(self.session_state_label)
        ac.layout().addWidget(self.selected_profile_label)
        ac.layout().addSpacing(6)
        self.start_button.setText("Start")
        self.stop_button.setText("Stop")
        ac.layout().addWidget(self.start_button)
        ac.layout().addWidget(self.stop_button)
        ac.layout().addStretch(1)
        hr.addWidget(ac, 2)
        lay.addLayout(hr)

        # Primary stat tiles (speed, distance, calories, duration)
        sg = QtWidgets.QGridLayout()
        sg.setHorizontalSpacing(10)
        sg.setVerticalSpacing(10)
        for i, w in enumerate(
            [
                self.speed_label,
                self.distance_label,
                self.calories_label,
                self.duration_label,
            ]
        ):
            sg.addWidget(self._stat_tile(w), 0, i)
        lay.addLayout(sg)

        # Status tiles (sensor, joystick, steamvr, strava)
        sg2 = QtWidgets.QGridLayout()
        sg2.setHorizontalSpacing(10)
        sg2.setVerticalSpacing(10)
        for i, w in enumerate(
            [
                self.sensor_status_label,
                self.joystick_status_label,
                self.steamvr_status_label,
                self.strava_status_label,
            ]
        ):
            sg2.addWidget(self._stat_tile(w), i // 2, i % 2)
        lay.addLayout(sg2)

        # Sensitivity slider row
        sens_row = QtWidgets.QHBoxLayout()
        self.sensitivity_label.setObjectName("sensitivity_label")
        sens_row.addWidget(self.sensitivity_label)
        sens_row.addWidget(self.sensitivity_slider, 1)
        sens_card = self._card(
            "SENSITIVITY",
            "Adjust how much belt movement maps to joystick output.",
        )
        sens_card.layout().addLayout(sens_row)
        lay.addWidget(sens_card)

        lay.addStretch(1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(sc)

    # --- Shared helpers (mirror MainWindow's private builders) ---

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