from PyQt6 import QtWidgets


class ProfilesPage(QtWidgets.QWidget):
    """Profiles tab: profile toolbar, tiles, and empty state."""

    def __init__(
        self,
        profile_combo,
        new_profile_button,
        duplicate_profile_button,
        delete_profile_button,
        profiles_grid,
        profiles_empty,
        parent=None,
    ):
        super().__init__(parent)
        self.profile_combo = profile_combo
        self.new_profile_button = new_profile_button
        self.duplicate_profile_button = duplicate_profile_button
        self.delete_profile_button = delete_profile_button
        self.profiles_grid = profiles_grid
        self.profiles_empty = profiles_empty
        self._build()

    def _build(self):
        sc = self._make_page()
        sc.setObjectName("profiles_page")
        lay = sc.widget().layout()
        pr = QtWidgets.QHBoxLayout()
        pr.setSpacing(8)
        pr.addWidget(self.profile_combo, 1)
        pr.addWidget(self.new_profile_button)
        pr.addWidget(self.duplicate_profile_button)
        pr.addWidget(self.delete_profile_button)
        toolbar_card = self._card(
            "PROFILES", "Create, switch, and manage game profiles."
        )
        toolbar_card.layout().addLayout(pr)
        lay.addWidget(toolbar_card)
        card_wrapper = QtWidgets.QWidget()
        card_wrapper.setLayout(self.profiles_grid)
        lay.addWidget(card_wrapper)
        lay.addWidget(self.profiles_empty)
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