from PyQt6 import QtCore, QtGui, QtWidgets


class TreadmillWidget(QtWidgets.QWidget):
    """Code-drawn animated treadmill visual for the 10-foot dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 280)
        self._speed_kmh = 0.0
        self._output_percent = 0
        self._belt_offset = 0.0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_speed(self, speed_kmh):
        self._speed_kmh = max(0.0, float(speed_kmh or 0.0))
        self.update()

    def set_output_percent(self, percent):
        self._output_percent = max(0, min(100, int(percent or 0)))
        self.update()

    def _tick(self):
        # Static when idle, visibly animated once movement starts.
        if self._speed_kmh <= 0.05 and self._output_percent <= 0:
            return
        step = 1.0 + min(self._speed_kmh, 16.0) * 0.9 + (self._output_percent / 100.0) * 2.0
        self._belt_offset = (self._belt_offset + step) % 48.0
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(18, 18, -18, -18)
        painter.fillRect(self.rect(), QtGui.QColor("#0b1118"))

        center = QtCore.QPointF(rect.center())
        glow = QtGui.QRadialGradient(center, max(rect.width(), rect.height()) * 0.62)
        glow.setColorAt(0.0, QtGui.QColor(30, 118, 160, 55))
        glow.setColorAt(1.0, QtGui.QColor(5, 9, 13, 0))
        painter.fillRect(self.rect(), glow)

        deck = QtCore.QRectF(
            rect.left() + rect.width() * 0.13,
            rect.top() + rect.height() * 0.20,
            rect.width() * 0.74,
            rect.height() * 0.58,
        )
        belt = deck.adjusted(deck.width() * 0.12, deck.height() * 0.17, -deck.width() * 0.12, -deck.height() * 0.17)

        # Side rails / body
        painter.setPen(QtGui.QPen(QtGui.QColor("#314152"), 3))
        painter.setBrush(QtGui.QColor("#121b25"))
        painter.drawRoundedRect(deck, 24, 24)

        # Belt base
        painter.setPen(QtGui.QPen(QtGui.QColor("#4c5d70"), 2))
        painter.setBrush(QtGui.QColor("#070c12"))
        painter.drawRoundedRect(belt, 18, 18)

        # Moving stripes clipped to belt.
        painter.save()
        path = QtGui.QPainterPath()
        path.addRoundedRect(belt, 18, 18)
        painter.setClipPath(path)
        painter.setPen(QtGui.QPen(QtGui.QColor(130, 168, 196, 200), 4))
        spacing = 40
        y = belt.top() - spacing + self._belt_offset
        while y < belt.bottom() + spacing:
            painter.drawLine(QtCore.QPointF(belt.left() + 18, y), QtCore.QPointF(belt.right() - 18, y + 28))
            y += spacing
        painter.restore()

        # Front roller and perspective lines.
        painter.setPen(QtGui.QPen(QtGui.QColor("#8fa3b8"), 2))
        painter.drawLine(QtCore.QPointF(deck.left() + 30, deck.bottom() - 26), QtCore.QPointF(deck.right() - 30, deck.bottom() - 26))
        painter.setPen(QtGui.QPen(QtGui.QColor(26, 159, 255, 120), 2))
        painter.drawRoundedRect(deck.adjusted(5, 5, -5, -5), 22, 22)

        # Output bar integrated into the treadmill visual.
        output_rect = QtCore.QRectF(deck.left() + 18, deck.bottom() - 14, max(20.0, (deck.width() - 36) * (self._output_percent / 100.0)), 6)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("#1a9fff"))
        painter.drawRoundedRect(output_rect, 3, 3)

        # Console-style speed + output readout.
        painter.setPen(QtGui.QColor("#f4f7fb"))
        speed_font = painter.font()
        speed_font.setPointSize(26)
        speed_font.setBold(False)
        painter.setFont(speed_font)
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignBottom, f"{self._speed_kmh:.1f} km/h")

        label_font = painter.font()
        label_font.setPointSize(10)
        label_font.setBold(False)
        painter.setFont(label_font)
        painter.setPen(QtGui.QColor("#9eadbd"))
        painter.drawText(rect.adjusted(0, 0, 0, -42), QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignBottom, f"OUTPUT {self._output_percent}%")
