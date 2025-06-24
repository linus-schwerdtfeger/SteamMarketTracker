from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import sys
from data.fetcher import fetch_price
from data.db import insert_price, get_price_history, init_db
from plots.chart import PricePlotCanvas


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
# This code initializes a PySide6 application, creates an instance of MainWindow, and starts the event loop.