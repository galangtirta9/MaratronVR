from PyQt6 import QtCore, QtGui, QtWidgets

from app.core.curve import clamp, normalize_curve_points


class CurveEditor(QtWidgets.QWidget):
    pointsChanged = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 180)
        self.points = normalize_curve_points([
            [0.0, 0.0],
            [0.25, 0.12],
            [0.50, 0.25],
            [0.75, 0.55],
            [1.0, 1.0],
        ])
        self.drag_index = None
        self.margin = 16

    def set_points(self, points):
        self.points = normalize_curve_points(points)
        self.update()

    def get_points(self):
        return normalize_curve_points(self.points)

    def to_screen(self, x, y):
        width = self.width() - self.margin * 2
        height = self.height() - self.margin * 2
        return QtCore.QPointF(self.margin + x * width, self.margin + (1.0 - y) * height)

    def from_screen(self, pos):
        width = self.width() - self.margin * 2
        height = self.height() - self.margin * 2
        x = (pos.x() - self.margin) / width
        y = 1.0 - ((pos.y() - self.margin) / height)
        return clamp(x, 0.0, 1.0), clamp(y, 0.0, 1.0)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#1e1e1e"))

        painter.setPen(QtGui.QPen(QtGui.QColor("#333333"), 1))
        for index in range(11):
            x = self.margin + index * (self.width() - self.margin * 2) / 10
            y = self.margin + index * (self.height() - self.margin * 2) / 10
            painter.drawLine(int(x), self.margin, int(x), self.height() - self.margin)
            painter.drawLine(self.margin, int(y), self.width() - self.margin, int(y))

        painter.setPen(QtGui.QPen(QtGui.QColor("#777777"), 1))
        painter.drawRect(
            self.margin,
            self.margin,
            self.width() - self.margin * 2,
            self.height() - self.margin * 2,
        )

        points = [self.to_screen(x, y) for x, y in self.points]
        painter.setPen(QtGui.QPen(QtGui.QColor("#f0d26a"), 4))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)

        for index, point in enumerate(points):
            color = "#ffdd77" if index == self.drag_index else "#ffffff"
            painter.setBrush(QtGui.QColor(color))
            painter.setPen(QtGui.QPen(QtGui.QColor("#111111"), 2))
            painter.drawEllipse(point, 7, 7)

    def nearest_point(self, pos):
        best = None
        best_dist = 999999

        for index, (x, y) in enumerate(self.points):
            point = self.to_screen(x, y)
            dist = (point.x() - pos.x()) ** 2 + (point.y() - pos.y()) ** 2
            if dist < best_dist:
                best = index
                best_dist = dist

        return best if best_dist <= 18 ** 2 else None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            index = self.nearest_point(event.position())
            if index is None:
                x, y = self.from_screen(event.position())
                self.points.append([x, y])
                self.points = normalize_curve_points(self.points)
                index = self.nearest_point(event.position())
            self.drag_index = index
            self.update()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            index = self.nearest_point(event.position())
            if index is not None and index not in (0, len(self.points) - 1):
                self.points.pop(index)
                self.points = normalize_curve_points(self.points)
                self.pointsChanged.emit(self.points)
                self.update()

    def mouseMoveEvent(self, event):
        if self.drag_index is None:
            return

        x, y = self.from_screen(event.position())

        if self.drag_index == 0:
            x = 0.0
        elif self.drag_index == len(self.points) - 1:
            x = 1.0
        else:
            left = self.points[self.drag_index - 1][0] + 0.01
            right = self.points[self.drag_index + 1][0] - 0.01
            x = clamp(x, left, right)

        self.points[self.drag_index] = [x, y]
        self.points = normalize_curve_points(self.points)
        self.pointsChanged.emit(self.points)
        self.update()

    def mouseReleaseEvent(self, event):
        self.drag_index = None
        self.pointsChanged.emit(self.points)
        self.update()