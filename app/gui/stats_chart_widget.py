from PyQt6 import QtCore, QtGui, QtWidgets


class StatsChartWidget(QtWidgets.QWidget):
    """Flat-style line chart for session history. Two datasets, no shadows."""

    LINE_POSITIVE = QtGui.QColor("#4C8C5B")
    LINE_ACCENT = QtGui.QColor("#3B82F6")
    FILL_POSITIVE = QtGui.QColor(76, 140, 91, 38)
    FILL_ACCENT = QtGui.QColor(59, 130, 246, 31)
    GRID_LINE = QtGui.QColor(35, 43, 56, 128)
    AXIS_LABEL = QtGui.QColor("#5C6675")
    TOOLTIP_FILL = QtGui.QColor("#161C26")
    TEXT_PRIMARY = QtGui.QColor("#F2F4F8")
    TEXT_SECONDARY = QtGui.QColor("#9AA4B2")

    METRICS = ["Distance (km)", "Duration (min)", "Calories (kcal)"]
    METRIC_KEYS = ["distance_km", "elapsed_min", "calories"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chart_container")
        self.setMinimumSize(520, 260)

        self._sessions = []
        self._active_metric_index = 0
        self._margin = {"left": 56, "right": 24, "top": 20, "bottom": 36}
        self._hovered_index = None

        self.setMouseTracking(True)

    def set_sessions(self, sessions):
        """sessions: list of dicts with distance_m, elapsed_time, calories keys."""
        self._sessions = sessions or []
        self.update()

    def set_active_metric(self, index):
        self._active_metric_index = max(0, min(len(self.METRIC_KEYS) - 1, index))
        self._hovered_index = None
        self.update()

    def current_metric_label(self):
        return self.METRICS[self._active_metric_index]

    def _metric_key(self):
        return self.METRIC_KEYS[self._active_metric_index]

    def _data_points(self):
        if not self._sessions:
            return []
        key = self._metric_key()
        return [self._extract_metric(s, key) for s in self._sessions]

    @staticmethod
    def _extract_metric(session, key):
        if key == "distance_km":
            return session.get("distance_m", 0.0) / 1000.0
        if key == "elapsed_min":
            return session.get("elapsed_time", 0) / 60.0
        if key == "calories":
            return session.get("calories", 0.0)
        return 0.0

    def _chart_rect(self):
        rect = self.rect()
        return QtCore.QRectF(
            rect.left() + self._margin["left"],
            rect.top() + self._margin["top"],
            rect.width() - self._margin["left"] - self._margin["right"],
            rect.height() - self._margin["top"] - self._margin["bottom"],
        )

    def _value_at_index(self, index):
        points = self._data_points()
        if 0 <= index < len(points):
            return points[index]
        return 0.0

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QtGui.QColor("#0F141C"))

        chart_rect = self._chart_rect()
        points = self._data_points()

        if not points:
            self._draw_empty_chart(painter, chart_rect)
            return

        self._draw_grid(painter, chart_rect, points)
        self._draw_area(painter, chart_rect, points)
        self._draw_line(painter, chart_rect, points)
        self._draw_points(painter, chart_rect, points)
        self._draw_axis_labels(painter, chart_rect, points)
        self._draw_tooltip(painter, chart_rect, points)

    def _draw_empty_chart(self, painter, chart_rect):
        painter.setPen(self.AXIS_LABEL)
        font = painter.font()
        font.setPointSize(11)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRectF(chart_rect),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            "No session data yet",
        )

    def _draw_grid(self, painter, chart_rect, points):
        max_value = max(points) if points else 1.0
        max_value = max(max_value, 0.01)
        grid_count = 4

        painter.setPen(QtGui.QPen(self.GRID_LINE, 1))
        for i in range(grid_count + 1):
            y_frac = i / grid_count
            y = chart_rect.bottom() - y_frac * chart_rect.height()
            painter.drawLine(
                QtCore.QPointF(chart_rect.left(), y),
                QtCore.QPointF(chart_rect.right(), y),
            )

            # Grid label
            value = y_frac * max_value
            label = self._format_grid_label(value)
            painter.setPen(self.AXIS_LABEL)
            font = painter.font()
            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            fm = QtGui.QFontMetrics(font)
            text_rect = QtCore.QRectF(
                chart_rect.left() - 48,
                y - 10,
                44,
                20,
            )
            painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter, label)
            painter.setPen(QtGui.QPen(self.GRID_LINE, 1))

    def _format_grid_label(self, value):
        key = self._metric_key()
        if key == "calories":
            return f"{value:.0f}"
        if key == "elapsed_min":
            if value >= 60:
                return f"{value / 60:.1f}h"
            return f"{value:.0f}m"
        return f"{value:.1f}"

    def _draw_area(self, painter, chart_rect, points):
        if len(points) < 2:
            return

        path = QtGui.QPainterPath()
        x_step = chart_rect.width() / max(1, len(points) - 1)
        max_value = max(points) if points else 1.0
        max_value = max(max_value, 0.01)

        first_x = chart_rect.left()
        first_y = chart_rect.bottom() - (points[0] / max_value) * chart_rect.height()
        path.moveTo(first_x, chart_rect.bottom())
        path.lineTo(first_x, first_y)

        for i, value in enumerate(points):
            x = chart_rect.left() + i * x_step
            y = chart_rect.bottom() - (value / max_value) * chart_rect.height()
            path.lineTo(x, y)

        last_x = chart_rect.left() + (len(points) - 1) * x_step
        path.lineTo(last_x, chart_rect.bottom())
        path.closeSubpath()

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.FILL_POSITIVE)
        painter.drawPath(path)

    def _draw_line(self, painter, chart_rect, points):
        if len(points) < 2:
            return

        x_step = chart_rect.width() / max(1, len(points) - 1)
        max_value = max(points) if points else 1.0
        max_value = max(max_value, 0.01)

        pen = QtGui.QPen(self.LINE_POSITIVE, 2.5)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        for i in range(len(points) - 1):
            x1 = chart_rect.left() + i * x_step
            y1 = chart_rect.bottom() - (points[i] / max_value) * chart_rect.height()
            x2 = chart_rect.left() + (i + 1) * x_step
            y2 = chart_rect.bottom() - (points[i + 1] / max_value) * chart_rect.height()
            painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))

    def _draw_points(self, painter, chart_rect, points):
        x_step = chart_rect.width() / max(1, len(points) - 1)
        max_value = max(points) if points else 1.0
        max_value = max(max_value, 0.01)

        for i, value in enumerate(points):
            x = chart_rect.left() + i * x_step
            y = chart_rect.bottom() - (value / max_value) * chart_rect.height()
            r = 5 if i == self._hovered_index else 3
            color = self.LINE_ACCENT if i == self._hovered_index else self.LINE_POSITIVE
            painter.setBrush(color)
            painter.setPen(QtGui.QPen(QtGui.QColor("#0A0E14"), 1.5))
            painter.drawEllipse(QtCore.QPointF(x, y), r, r)

    def _draw_axis_labels(self, painter, chart_rect, points):
        if not points:
            return

        font = painter.font()
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(self.AXIS_LABEL)

        # X-axis: session indices
        step = max(1, len(points) // 5)
        for i in range(0, len(points), step):
            x_step = chart_rect.width() / max(1, len(points) - 1)
            x = chart_rect.left() + i * x_step
            text_rect = QtCore.QRectF(x - 20, chart_rect.bottom() + 4, 40, 20)
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                f"#{i + 1}",
            )

    def _draw_tooltip(self, painter, chart_rect, points):
        if self._hovered_index is None or self._hovered_index >= len(points):
            return

        x_step = chart_rect.width() / max(1, len(points) - 1)
        max_value = max(points) if points else 1.0
        max_value = max(max_value, 0.01)

        value = points[self._hovered_index]
        x = chart_rect.left() + self._hovered_index * x_step
        y = chart_rect.bottom() - (value / max_value) * chart_rect.height()

        key = self._metric_key()
        if key == "distance_km":
            label = f"{value:.2f} km"
        elif key == "elapsed_min":
            label = f"{int(value)}m {int((value - int(value)) * 60)}s" if value < 60 else f"{value:.1f} min"
        else:
            label = f"{value:.0f} kcal"

        fm = QtGui.QFontMetrics(painter.font())
        text_width = fm.horizontalAdvance(label) + 16
        text_height = fm.height() + 8

        tooltip_x = min(chart_rect.right() - text_width, max(chart_rect.left(), x - text_width / 2))
        tooltip_y = max(chart_rect.top(), y - text_height - 10)

        tooltip_rect = QtCore.QRectF(tooltip_x, tooltip_y, text_width, text_height)

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.TOOLTIP_FILL)
        painter.drawRoundedRect(tooltip_rect, 4, 4)

        painter.setPen(self.TEXT_PRIMARY)
        painter.drawText(
            tooltip_rect,
            QtCore.Qt.AlignmentFlag.AlignCenter,
            label,
        )

    def mouseMoveEvent(self, event):
        chart_rect = self._chart_rect()
        points = self._data_points()

        if not points or event.position().x() < chart_rect.left() or event.position().x() > chart_rect.right():
            if self._hovered_index is not None:
                self._hovered_index = None
                self.update()
            return

        x_step = chart_rect.width() / max(1, len(points) - 1)
        index = round((event.position().x() - chart_rect.left()) / x_step)
        index = max(0, min(len(points) - 1, index))

        if index != self._hovered_index:
            self._hovered_index = index
            self.update()

    def leaveEvent(self, event):
        if self._hovered_index is not None:
            self._hovered_index = None
            self.update()