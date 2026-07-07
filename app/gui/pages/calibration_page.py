from PyQt6 import QtWidgets


class CalibrationPage(QtWidgets.QWidget):
    """Calibration tab: noise floor calibration card."""

    def __init__(
        self,
        calibrate_button,
        reset_health_button,
        cal_noise_label,
        cal_max_label,
        cal_count_label,
        parent=None,
    ):
        super().__init__(parent)
        self.calibrate_button = calibrate_button
        self.reset_health_button = reset_health_button
        self.cal_noise_label = cal_noise_label
        self.cal_max_label = cal_max_label
        self.cal_count_label = cal_count_label
        self._build()

    def _build(self):
        sc = self._make_page()
        lay = sc.widget().layout()
        c = self._card("Noise Floor Calibration")
        c.layout().addWidget(
            QtWidgets.QLabel(
                "Keep the belt still for 5 seconds. "
                "Maratron measures sensor noise and sets a baseline deadzone."
            )
        )
        c.layout().addSpacing(8)
        c.layout().addWidget(self.cal_noise_label)
        c.layout().addWidget(self.cal_max_label)
        c.layout().addWidget(self.cal_count_label)
        c.layout().addSpacing(8)
        bb = QtWidgets.QHBoxLayout()
        bb.setSpacing(8)
        bb.addWidget(self.calibrate_button)
        bb.addWidget(self.reset_health_button)
        c.layout().addLayout(bb)
        lay.addWidget(c)
        lay.addStretch(1)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(sc)

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