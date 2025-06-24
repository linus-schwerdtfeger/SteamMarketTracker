import json
import os
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog
)
from data.fetcher import fetch_price
from data.db import insert_price, get_price_history, init_db
from plots.chart import PricePlotCanvas


@staticmethod
def check_alert(skin, current_price):
    with open("alerts.json", "r", encoding="utf-8") as f:
        alerts = json.load(f)
    limit = alerts.get(skin)
    if limit and current_price <= limit:
        return True
    return False


WATCHLIST_PATH = "watchlist.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CS Skin Markt Preis-Tracker")
        self.setFixedSize(1200, 800)

        # Widgets
        self.skin_list = QListWidget()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("z.B. AK-47 | Redline (Field-Tested)")
        self.add_button = QPushButton("Hinzufügen")
        self.remove_button = QPushButton("Entfernen")
        self.export_button = QPushButton("Preise exportieren (CSV)")

        # Layouts
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.add_button)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.remove_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.skin_list)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.export_button)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Events
        self.add_button.clicked.connect(self.add_skin)
        self.remove_button.clicked.connect(self.remove_skin)
        self.export_button.clicked.connect(self.export_data)

        # Watchlist laden
        self.load_watchlist()

        init_db()  # SQLite-DB initialisieren

        # Diagramm hinzufügen
        self.plot_canvas = PricePlotCanvas()
        main_layout.addWidget(self.plot_canvas)

        # Events
        self.skin_list.currentTextChanged.connect(self.update_plot)

        # Auto-Aktualisieren
        self.refresh_all_prices()


    def load_watchlist(self):
        if os.path.exists(WATCHLIST_PATH):
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                try:
                    skins = json.load(f)
                    for skin in skins:
                        self.skin_list.addItem(skin)
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "Fehler", "Watchlist-Datei ist beschädigt.")

    def save_watchlist(self):
        skins = [self.skin_list.item(i).text() for i in range(self.skin_list.count())]
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(skins, f, indent=2, ensure_ascii=False)

    def add_skin(self):
        skin_name = self.input_field.text().strip()
        if not skin_name:
            return
        if any(self.skin_list.item(i).text() == skin_name for i in range(self.skin_list.count())):
            QMessageBox.information(self, "Info", "Skin ist bereits in der Liste.")
            return
        self.skin_list.addItem(skin_name)
        self.input_field.clear()
        self.save_watchlist()
        self.update_price_for_skin(skin_name)
        self.skin_list.setCurrentRow(self.skin_list.count() - 1)  # Skin auswählen
        self.update_plot()  # Diagramm aktualisieren

    def remove_skin(self):
        selected = self.skin_list.currentRow()
        if selected >= 0:
            self.skin_list.takeItem(selected)
            self.save_watchlist()

    def update_price_for_skin(self, skin):
        price, volume = fetch_price(skin)
        if price is not None:
            insert_price(skin, price, volume)
            if check_alert(skin, price):
                QMessageBox.information(
                    self,
                    "💥 Preisalarm!",
                    f"{skin} kostet jetzt nur noch {price:.2f} €!"
                )

    def refresh_all_prices(self):
        for i in range(self.skin_list.count()):
            skin = self.skin_list.item(i).text()
            self.update_price_for_skin(skin)



    def update_plot(self):
        skin = self.skin_list.currentItem()
        if not skin:
            self.plot_canvas.plot([], "")
            return
        history = get_price_history(skin.text())
        self.plot_canvas.plot(history, skin.text())

    def export_data(self):
        skin = self.skin_list.currentItem()
        if not skin:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportieren als CSV", f"{skin.text()}.csv", "CSV-Dateien (*.csv)")
        if filename:
            from data.db import export_price_history
            export_price_history(skin.text(), filename)