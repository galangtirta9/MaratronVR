from PyQt6 import QtCore, QtWidgets


class ToastNotification(QtWidgets.QFrame):
    """Lightweight auto-dismiss notification displayed at bottom-right of parent."""

    def __init__(self, parent, message, duration_ms=3000):
        super().__init__(parent)
        self.setObjectName("toast")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        label = QtWidgets.QLabel(message)
        label.setObjectName("toast_label")
        label.setWordWrap(True)
        layout.addWidget(label, 1)

        self.setMaximumWidth(360)
        self.setMinimumWidth(200)
        self.adjustSize()

        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)
        self.timer.start(duration_ms)

        self._position_at_parent_bottom()
        self._fade_in()

    def _position_at_parent_bottom(self):
        if self.parent() is None:
            return
        parent_rect = self.parent().rect()
        x = parent_rect.right() - self.width() - 24
        y = parent_rect.bottom() - self.height() - 56
        self.move(x, y)

    def _fade_in(self):
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._opacity_effect = effect

        self._fade_animation = QtCore.QPropertyAnimation(effect, b"opacity")
        self._fade_animation.setDuration(150)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()

    def _fade_out(self):
        if not hasattr(self, "_opacity_effect"):
            self.deleteLater()
            return

        self._fade_animation = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(120)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.deleteLater)
        self._fade_animation.start()