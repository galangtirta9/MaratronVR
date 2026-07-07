from PyQt6 import QtCore, QtWidgets


class StatsPage(QtWidgets.QWidget):
    """Stats tab: summary tiles, session chart, recent sessions, Strava."""

    METRICS = ["Distance (km)", "Duration (min)", "Calories (kcal)"]
    METRIC_KEY_MAP = ["distance_km", "elapsed_min", "calories"]

    chart_metric_changed = QtCore.pyqtSignal(int)

    def __init__(
        self,
        stats_total_distance,
        stats_total_time,
        stats_total_calories,
        stats_session_count,
        stats_chart,
        stats_sessions_list,
        stats_empty,
        strava_status_label,
        strava_authorize_button,
        strava_exchange_button,
        strava_upload_button,
        on_chart_metric_toggle,
        parent=None,
    ):
        super().__init__(parent)
        self.stats_total_distance = stats_total_distance
        self.stats_total_time = stats_total_time
        self.stats_total_calories = stats_total_calories
        self.stats_session_count = stats_session_count
        self.stats_chart = stats_chart
        self.stats_sessions_list = stats_sessions_list
        self.stats_empty = stats_empty
        self.strava_status_label = strava_status_label
        self.strava_authorize_button = strava_authorize_button
        self.strava_exchange_button = strava_exchange_button
        self.strava_upload_button = strava_upload_button
        self._on_chart_metric_toggle = on_chart_metric_toggle
        self.chart_toggle_buttons = []
        self._build()

    def _build(self):
        sc = self._make_page()
        sc.setObjectName("stats_page")
        lay = sc.widget().layout()

        sg = QtWidgets.QGridLayout()
        sg.setHorizontalSpacing(10)
        sg.setVerticalSpacing(10)
        for i, lbl in enumerate(
            [
                self.stats_total_distance,
                self.stats_total_time,
                self.stats_total_calories,
                self.stats_session_count,
            ]
        ):
            sg.addWidget(self._stat_tile(lbl), 0, i)
        lay.addLayout(sg)

        self.stats_chart.setMinimumHeight(280)
        chart_card = self._card("SESSION HISTORY")
        chart_card.layout().addWidget(self.stats_chart)

        toggle_row = QtWidgets.QHBoxLayout()
        toggle_row.setSpacing(8)
        for idx, label in enumerate(self.METRICS):
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("nav_pill")
            btn.clicked.connect(
                lambda checked, i=idx: self._on_chart_metric_toggle(i)
            )
            if idx == 0:
                btn.setChecked(True)
            toggle_row.addWidget(btn)
            self.chart_toggle_buttons.append(btn)
        chart_card.layout().addLayout(toggle_row)
        lay.addWidget(chart_card)

        sessions_list_wrapper = QtWidgets.QWidget()
        sessions_list_wrapper.setLayout(self.stats_sessions_list)
        sessions_card = self._card("RECENT SESSIONS")
        sessions_card.layout().addWidget(sessions_list_wrapper)
        lay.addWidget(sessions_card)

        lay.addWidget(self.stats_empty)

        strava_card = self._card("STRAVA")
        strava_card.layout().addWidget(self.strava_status_label)
        sb = QtWidgets.QHBoxLayout()
        sb.setSpacing(8)
        sb.addWidget(self.strava_authorize_button)
        sb.addWidget(self.strava_exchange_button)
        sb.addWidget(self.strava_upload_button)
        strava_card.layout().addLayout(sb)
        lay.addWidget(strava_card)

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

    @staticmethod
    def _stat_tile(label):
        t = QtWidgets.QFrame()
        t.setObjectName("stat_tile")
        l = QtWidgets.QVBoxLayout(t)
        l.setContentsMargins(14, 10, 14, 10)
        label.setParent(t)
        l.addWidget(label)
        return t