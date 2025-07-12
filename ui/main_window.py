import json
import os
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog, QLabel
)
from PySide6.QtCore import Qt
from data.fetcher import fetch_comprehensive_market_data
from data.db import insert_market_data, get_market_history, init_db, export_market_data, get_latest_price
from plots.chart import MarketDataCanvas

# Konstanten
WATCHLIST_PATH = "watchlist.json"
ALERTS_PATH = "alerts.json"

def check_alert(skin: str, current_price: float) -> bool:
    """Prüft Preisalarme."""
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
        self.setWindowTitle("CS Skin Markt Analyzer - Enhanced")
        
        # Responsive Design
        self.setMinimumSize(900, 700)
        self.resize(1400, 900)
        self.center_window()

        # UI-Komponenten
        self.skin_list = QListWidget()
        self.skin_list.setMinimumHeight(180)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("z.B. AK-47 | Redline (Field-Tested)")
        
        self.add_button = QPushButton("Hinzufügen")
        self.remove_button = QPushButton("Entfernen")
        self.refresh_button = QPushButton("Alle aktualisieren")
        self.export_button = QPushButton("Marktdaten exportieren (CSV)")
        
        self.status_label = QLabel("Bereit für erweiterte Marktanalyse")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        # Layout
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.add_button)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.status_label)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.skin_list, 1)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.export_button)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Chart-Canvas
        self.chart_canvas = MarketDataCanvas()
        main_layout.addWidget(self.chart_canvas, 3)

        # Event-Connections
        self.add_button.clicked.connect(self.add_skin)
        self.remove_button.clicked.connect(self.remove_skin)
        self.refresh_button.clicked.connect(self.refresh_all_prices)
        self.export_button.clicked.connect(self.export_data)
        self.skin_list.currentTextChanged.connect(self.update_chart)

        # Initialisierung
        self.load_watchlist()
        init_db()
        self.create_menu_bar()
        self.setup_shortcuts()
        
        # Status auf "Bereit" setzen statt "Lädt..."
        self.status_label.setText("Bereit - Drücken Sie 'Alle aktualisieren' für neue Daten")
        self.status_label.setStyleSheet("color: #cccccc; font-weight: normal;")
        
        # Zeige ersten Skin falls vorhanden
        if self.skin_list.count() > 0:
            self.skin_list.setCurrentRow(0)
            self.update_chart()

    def center_window(self):
        """Zentriert das Fenster."""
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def load_watchlist(self):
        """Lädt die Watchlist."""
        if not os.path.exists(WATCHLIST_PATH):
            return
            
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                skins = json.load(f)
                if isinstance(skins, list):
                    for skin in skins:
                        if isinstance(skin, str) and skin.strip():
                            self.skin_list.addItem(skin.strip())
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Watchlist konnte nicht geladen werden: {e}")

    def save_watchlist(self):
        """Speichert die Watchlist."""
        skins = [self.skin_list.item(i).text() for i in range(self.skin_list.count())]
        try:
            with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
                json.dump(skins, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Watchlist konnte nicht gespeichert werden: {e}")

    def add_skin(self):
        """Fügt einen Skin hinzu."""
        skin_name = self.input_field.text().strip()
        if not skin_name:
            QMessageBox.information(self, "Info", "Bitte geben Sie einen Skin-Namen ein.")
            return
            
        # Prüfe Duplikate
        for i in range(self.skin_list.count()):
            if self.skin_list.item(i).text() == skin_name:
                QMessageBox.information(self, "Info", "Skin ist bereits in der Liste.")
                return
            
        self.skin_list.addItem(skin_name)
        self.input_field.clear()
        self.save_watchlist()
        
        # Sofort Marktdaten abrufen
        self.update_market_data_for_skin(skin_name)
        self.skin_list.setCurrentRow(self.skin_list.count() - 1)

    def remove_skin(self):
        """Entfernt einen Skin."""
        selected = self.skin_list.currentRow()
        if selected >= 0:
            self.skin_list.takeItem(selected)
            self.save_watchlist()
            self.update_chart()
        else:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Entfernen aus.")

    def update_market_data_for_skin(self, skin: str):
        """Aktualisiert Marktdaten für einen Skin."""
        self.status_label.setText(f"Lade erweiterte Marktdaten für {skin}...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        market_data = fetch_comprehensive_market_data(skin)
        if market_data and market_data.has_valid_data:
            insert_market_data(skin, market_data)
            
            if check_alert(skin, market_data.lowest_price):
                QMessageBox.information(
                    self,
                    "💥 Preisalarm!",
                    f"{skin} kostet jetzt nur noch {market_data.lowest_price:.2f} €!\n"
                    f"Spread: {market_data.spread_percentage:.1f}% | Volumen: {market_data.volume}"
                )
                
            self.status_label.setText(f"✅ Marktdaten aktualisiert für {skin}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.update_chart()
        else:
            self.status_label.setText(f"❌ Fehler beim Laden von {skin}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def refresh_all_prices(self):
        """Aktualisiert alle Marktdaten."""
        for i in range(self.skin_list.count()):
            skin = self.skin_list.item(i).text()
            self.update_market_data_for_skin(skin)
        self.status_label.setText("✅ Alle Marktdaten wurden aktualisiert")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def update_chart(self):
        """Aktualisiert das Chart."""
        current_item = self.skin_list.currentItem()
        if not current_item:
            self.chart_canvas.plot_market_data([], "Kein Skin ausgewählt")
            return
            
        skin_name = current_item.text()
        market_history = get_market_history(skin_name)
        self.chart_canvas.plot_market_data(market_history, skin_name)

    def export_data(self):
        """Exportiert Marktdaten."""
        current_item = self.skin_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Exportieren aus.")
            return
            
        skin_name = current_item.text()
        safe_filename = "".join(c for c in skin_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Marktdaten exportieren", 
            f"{safe_filename}_marktdaten.csv", 
            "CSV-Dateien (*.csv)"
        )
        
        if filename:
            try:
                export_market_data(skin_name, filename)
                QMessageBox.information(
                    self, 
                    "Erfolg", 
                    f"Vollständige Marktdaten exportiert:\n"
                    f"• Preisverlauf\n• Handelsvolumen\n• Bid-Ask Spread\n\n"
                    f"Datei: {filename}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen: {e}")

    def create_menu_bar(self):
        """Erstellt Menüleiste."""
        try:
            menubar = self.menuBar()
            
            view_menu = menubar.addMenu('Ansicht')
            fullscreen_action = view_menu.addAction('Vollbild')
            fullscreen_action.setShortcut('F11')
            fullscreen_action.triggered.connect(self.toggle_fullscreen)
            
            file_menu = menubar.addMenu('Datei')
            export_action = file_menu.addAction('Exportieren...')
            export_action.setShortcut('Ctrl+E')
            export_action.triggered.connect(self.export_data)
        except Exception as e:
            print(f"Menüleiste konnte nicht erstellt werden: {e}")

    def setup_shortcuts(self):
        """Setzt Tastenkürzel."""
        try:
            from PySide6.QtGui import QShortcut, QKeySequence
            
            if hasattr(self, 'input_field') and hasattr(self, 'skin_list'):
                add_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.input_field)
                add_shortcut.activated.connect(self.add_skin)
                
                delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.skin_list)
                delete_shortcut.activated.connect(self.remove_skin)
        except Exception as e:
            print(f"Shortcuts konnten nicht erstellt werden: {e}")

    def toggle_fullscreen(self):
        """Vollbild-Modus."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()