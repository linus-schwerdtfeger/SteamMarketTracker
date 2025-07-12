import json
import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog
)
from data.fetcher import fetch_price
from data.db import insert_price, get_price_history, init_db
from plots.chart import PricePlotCanvas

# Konstanten
WATCHLIST_PATH = "watchlist.json"
ALERTS_PATH = "alerts.json"

def check_alert(skin: str, current_price: float) -> bool:
    """
    Prüft, ob für einen Skin ein Preisalarm ausgelöst werden soll.
    
    Args:
        skin: Name des Skins
        current_price: Aktueller Preis
        
    Returns:
        True wenn Alarm ausgelöst werden soll, False sonst
    """
    try:
        if not os.path.exists(ALERTS_PATH):
            return False
            
        with open(ALERTS_PATH, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        
        limit = alerts.get(skin)
        return limit is not None and current_price <= limit
    except (json.JSONDecodeError, IOError):
        return False

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
        """Lädt die Watchlist aus der JSON-Datei."""
        if not os.path.exists(WATCHLIST_PATH):
            return
            
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                skins = json.load(f)
                if isinstance(skins, list):
                    for skin in skins:
                        if isinstance(skin, str) and skin.strip():
                            self.skin_list.addItem(skin.strip())
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.warning(self, "Fehler", f"Watchlist-Datei konnte nicht geladen werden: {e}")

    def save_watchlist(self):
        """Speichert die aktuelle Watchlist in die JSON-Datei."""
        skins = [self.skin_list.item(i).text() for i in range(self.skin_list.count())]
        try:
            with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
                json.dump(skins, f, indent=2, ensure_ascii=False)
        except IOError as e:
            QMessageBox.warning(self, "Fehler", f"Watchlist konnte nicht gespeichert werden: {e}")

    def _is_skin_in_list(self, skin_name: str) -> bool:
        """Prüft, ob ein Skin bereits in der Liste ist."""
        for i in range(self.skin_list.count()):
            if self.skin_list.item(i).text() == skin_name:
                return True
        return False

    def add_skin(self):
        """Fügt einen neuen Skin zur Watchlist hinzu."""
        skin_name = self.input_field.text().strip()
        if not skin_name:
            QMessageBox.information(self, "Info", "Bitte geben Sie einen Skin-Namen ein.")
            return
            
        if self._is_skin_in_list(skin_name):
            QMessageBox.information(self, "Info", "Skin ist bereits in der Liste.")
            return
            
        self.skin_list.addItem(skin_name)
        self.input_field.clear()
        self.save_watchlist()
        
        # Preis abrufen und Skin auswählen
        self.update_price_for_skin(skin_name)
        self.skin_list.setCurrentRow(self.skin_list.count() - 1)
        self.update_plot()

    def remove_skin(self):
        """Entfernt den ausgewählten Skin aus der Watchlist."""
        selected = self.skin_list.currentRow()
        if selected >= 0:
            self.skin_list.takeItem(selected)
            self.save_watchlist()
            self.update_plot()  # Plot aktualisieren
        else:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Entfernen aus.")

    def update_price_for_skin(self, skin: str):
        """
        Aktualisiert den Preis für einen bestimmten Skin.
        
        Args:
            skin: Name des Skins
        """
        price, volume = fetch_price(skin)
        if price is not None and volume is not None:
            insert_price(skin, price, volume)
            if check_alert(skin, price):
                QMessageBox.information(
                    self,
                    "💥 Preisalarm!",
                    f"{skin} kostet jetzt nur noch {price:.2f} €!"
                )
        else:
            print(f"Konnte Preis für '{skin}' nicht abrufen.")

    def refresh_all_prices(self):
        """Aktualisiert die Preise für alle Skins in der Watchlist."""
        for i in range(self.skin_list.count()):
            skin = self.skin_list.item(i).text()
            self.update_price_for_skin(skin)

    def update_plot(self):
        """Aktualisiert das Preisdiagramm für den ausgewählten Skin."""
        current_item = self.skin_list.currentItem()
        if not current_item:
            self.plot_canvas.plot([], "Kein Skin ausgewählt")
            return
            
        skin_name = current_item.text()
        history = get_price_history(skin_name)
        self.plot_canvas.plot(history, skin_name)

    def export_data(self):
        """Exportiert die Preisdaten des ausgewählten Skins als CSV."""
        current_item = self.skin_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Exportieren aus.")
            return
            
        skin_name = current_item.text()
        # Entferne ungültige Zeichen aus dem Dateinamen
        safe_filename = "".join(c for c in skin_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Exportieren als CSV", 
            f"{safe_filename}.csv", 
            "CSV-Dateien (*.csv)"
        )
        
        if filename:
            try:
                from data.db import export_price_history
                export_price_history(skin_name, filename)
                QMessageBox.information(self, "Erfolg", f"Daten erfolgreich nach {filename} exportiert.")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen: {e}")