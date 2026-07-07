from PyQt6.QtCore import Qt


class NavigationController:
    """Coordinates tab switching, settings overlay, and keyboard navigation."""

    def __init__(self, content_stack, tab_buttons, settings_page):
        self._stack = content_stack
        self._tab_buttons = tab_buttons
        self._settings_page = settings_page
        self._settings_open = False
        self._ctrl_pressed = False

    # --- Tab switching ---

    def switch_tab(self, name):
        tabs = ["Dashboard", "Calibration", "Profiles", "Stats"]
        idx = tabs.index(name)
        self._stack.setCurrentIndex(idx)
        for btn in self._tab_buttons:
            btn.setChecked(btn.text() == name.upper())
        self._settings_open = False

    def cycle_tab(self, direction):
        tabs = ["Dashboard", "Calibration", "Profiles", "Stats"]
        current = self._stack.currentIndex()
        if current not in range(len(tabs)):
            current = 0
        self.switch_tab(tabs[(current + direction) % len(tabs)])

    # --- Settings ---

    def toggle_settings(self):
        self._settings_open = not self._settings_open
        if self._settings_open:
            self._stack.setCurrentIndex(4)
        else:
            self._tab_buttons[0].setChecked(True)
            for btn in self._tab_buttons:
                btn.setChecked(btn is self._tab_buttons[0])
            self._stack.setCurrentIndex(0)

    def close_settings(self):
        if self._settings_open:
            self.toggle_settings()

    def go_back(self):
        if self._settings_open:
            self._settings_page.go_back()

    @property
    def is_settings_open(self):
        return self._settings_open

    # --- Keyboard shortcut helpers ---

    def on_key_press(self, event):
        if event.isAutoRepeat():
            return False
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Meta):
            self._ctrl_pressed = True
            event.accept()
            return True
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed = False
        return False

    def on_key_release(self, event):
        if event.isAutoRepeat():
            return False
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Meta):
            if self._ctrl_pressed:
                self.toggle_settings()
                event.accept()
            self._ctrl_pressed = False
            return True
        return False
