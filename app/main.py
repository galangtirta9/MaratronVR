import sys
from pathlib import Path

from PyQt6 import QtWidgets
from app.gui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Load dark theme stylesheet
    style_path = Path(__file__).resolve().parent / "gui" / "style.qss"
    if style_path.exists():
        with open(style_path) as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()