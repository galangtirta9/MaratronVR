from PyQt6 import QtCore, QtWidgets


class ConfirmModal(QtWidgets.QDialog):
    """Centered card modal for irreversible actions. Flat-fill, no shadows."""

    def __init__(
        self,
        parent,
        title,
        body,
        confirm_text="Delete",
        cancel_text="Cancel",
        destructive=True,
    ):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumWidth(400)
        self.setMaximumWidth(520)

        self._build_ui(title, body, confirm_text, cancel_text, destructive)
        self._center_on_parent()

    def _build_ui(self, title, body, confirm_text, cancel_text, destructive):
        # Overlay
        container = QtWidgets.QWidget(self)
        container.setObjectName("modal_overlay")
        container.setStyleSheet(
            "#modal_overlay { background-color: rgba(0, 0, 0, 0.60); }"
        )
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Card
        card = QtWidgets.QFrame()
        card.setObjectName("modal_card")
        card.setMinimumWidth(self.minimumWidth())
        card.setMaximumWidth(self.maximumWidth())
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 24)
        card_layout.setSpacing(16)

        # Title
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("modal_title")
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)

        # Body
        body_label = QtWidgets.QLabel(body)
        body_label.setObjectName("modal_body")
        body_label.setWordWrap(True)
        card_layout.addWidget(body_label)

        card_layout.addSpacing(8)

        # Buttons
        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch(1)

        cancel_btn = QtWidgets.QPushButton(cancel_text)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(44)
        if not destructive:
            cancel_btn.setObjectName("start_button")

        confirm_btn = QtWidgets.QPushButton(confirm_text)
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setMinimumHeight(44)
        if destructive:
            confirm_btn.setObjectName("stop_button")
        else:
            confirm_btn.setObjectName("start_button")

        button_row.addWidget(cancel_btn)
        button_row.addWidget(confirm_btn)
        card_layout.addLayout(button_row)

        container_layout.addWidget(card)

        # Modal enters with a brief fade
        effect = QtWidgets.QGraphicsOpacityEffect(container)
        effect.setOpacity(0.0)
        container.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, b"opacity")
        animation.setDuration(120)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start()

    def _center_on_parent(self):
        if self.parent() is not None:
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.setGeometry(x, y, self.width(), self.height())

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()