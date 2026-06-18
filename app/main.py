import logging
import sys

from PyQt6 import QtWidgets

from app.gui.main_window import MainWindow


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()