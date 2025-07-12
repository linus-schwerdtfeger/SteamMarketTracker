import json
import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog, 
    QTabWidget, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
from data.fetcher import fetch_price, fetch_comprehensive_market_data
from data.db import (insert_price, get_price_history, init_db, 
                     insert_comprehensive_market_data, get_comprehensive_history)
from plots.chart import EnhancedPricePlotCanvas

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
        
        # Dynamische Größe statt fester Größe
        self.setMinimumSize(800, 600)  # Mindestgröße für Benutzerfreundlichkeit
        self.resize(1200, 800)  # Standardgröße beim Start
        
        # Fenster-Eigenschaften für bessere UX
        self.setWindowFlags(self.windowFlags() | self.windowFlags().WindowMaximizeButtonHint)
        
        # Zentrale das Fenster auf dem Bildschirm
        self.center_window()

        # Widgets mit verbesserter Größenpolitik
        self.skin_list = QListWidget()
        self.skin_list.setMinimumHeight(150)  # Mindesthöhe für Benutzerfreundlichkeit
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("z.B. AK-47 | Redline (Field-Tested)")
        self.add_button = QPushButton("Hinzufügen")
        self.remove_button = QPushButton("Entfernen")
        self.export_button = QPushButton("Preise exportieren (CSV)")
        
        # Checkbox für erweiterte Marktdaten
        self.enhanced_data_checkbox = QCheckBox("Erweiterte Marktdaten (Volumen & Spread)")
        self.enhanced_data_checkbox.setChecked(True)
        self.enhanced_data_checkbox.stateChanged.connect(self.on_enhanced_data_toggle)
        
        # Status Label
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        # Layouts mit verbesserter Skalierung
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field, 1)  # Stretch-Faktor für Input-Feld
        input_layout.addWidget(self.add_button)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.remove_button)
        
        # Options layout
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.enhanced_data_checkbox)
        options_layout.addStretch()
        options_layout.addWidget(self.status_label)

        # Haupt-Layout mit Stretch-Faktoren
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.skin_list, 1)  # Skin-Liste bekommt 30% der Höhe
        main_layout.addLayout(input_layout)
        main_layout.addLayout(options_layout)
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
        self.plot_canvas = EnhancedPricePlotCanvas()
        main_layout.addWidget(self.plot_canvas, 3)  # Chart bekommt 70% der Höhe

        # Events
        self.skin_list.currentTextChanged.connect(self.update_plot)

        # Auto-Aktualisieren
        self.refresh_all_prices()
        
        # UI-Setup nach Widget-Erstellung
        self.create_menu_bar()
        self.setup_shortcuts()


    def center_window(self):
        """Zentriert das Fenster auf dem Bildschirm."""
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            
            # Für sehr große Bildschirme: Maximale Fensterbreite begrenzen
            max_width = min(screen_geometry.width() * 0.8, 1600)
            max_height = min(screen_geometry.height() * 0.9, 1200)
            
            current_size = self.size()
            new_width = min(current_size.width(), max_width)
            new_height = min(current_size.height(), max_height)
            
            self.resize(new_width, new_height)
            
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

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

    def on_enhanced_data_toggle(self, state):
        """Behandelt das Ein-/Ausschalten der erweiterten Marktdaten."""
        self.update_plot()

    def update_price_for_skin(self, skin: str):
        """
        Aktualisiert den Preis für einen bestimmten Skin.
        
        Args:
            skin: Name des Skins
        """
        self.status_label.setText(f"Lade Daten für {skin}...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        if self.enhanced_data_checkbox.isChecked():
            # Erweiterte Marktdaten abrufen
            market_data = fetch_comprehensive_market_data(skin)
            if market_data and market_data.has_valid_data:
                insert_comprehensive_market_data(skin, market_data)
                if check_alert(skin, market_data.lowest_price):
                    QMessageBox.information(
                        self,
                        "💥 Preisalarm!",
                        f"{skin} kostet jetzt nur noch {market_data.lowest_price:.2f} €!\n"
                        f"Spread: {market_data.spread_percentage:.1f}% | Volumen: {market_data.volume}"
                    )
                self.status_label.setText(f"Daten aktualisiert für {skin}")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.status_label.setText(f"Fehler beim Laden von {skin}")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                print(f"Konnte erweiterte Marktdaten für '{skin}' nicht abrufen.")
        else:
            # Nur Basisdaten abrufen (Rückwärtskompatibilität)
            price, volume = fetch_price(skin)
            if price is not None and volume is not None:
                insert_price(skin, price, volume)
                if check_alert(skin, price):
                    QMessageBox.information(
                        self,
                        "💥 Preisalarm!",
                        f"{skin} kostet jetzt nur noch {price:.2f} €!"
                    )
                self.status_label.setText(f"Preis aktualisiert für {skin}")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.status_label.setText(f"Fehler beim Laden von {skin}")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
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
        
        if self.enhanced_data_checkbox.isChecked():
            # Verwende erweiterte Marktdaten wenn verfügbar
            comprehensive_history = get_comprehensive_history(skin_name)
            if comprehensive_history:
                self.plot_canvas.plot_comprehensive(comprehensive_history, skin_name)
            else:
                # Fallback auf einfache Preishistorie
                history = get_price_history(skin_name)
                self.plot_canvas.plot(history, skin_name)
        else:
            # Nur Preishistorie anzeigen
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
                if self.enhanced_data_checkbox.isChecked():
                    # Exportiere alle Marktdaten (Preis, Volumen, Spread)
                    from data.db import export_comprehensive_market_data
                    export_comprehensive_market_data(skin_name, filename)
                    QMessageBox.information(
                        self, 
                        "Erfolg", 
                        f"Vollständige Marktdaten erfolgreich exportiert:\n"
                        f"• Preisverlauf\n• Handelsvolumen\n• Bid-Ask Spread\n\n"
                        f"Datei: {filename}"
                    )
                else:
                    # Exportiere nur Preisdaten (Rückwärtskompatibilität)
                    from data.db import export_price_history
                    export_price_history(skin_name, filename)
                    QMessageBox.information(self, "Erfolg", f"Preisdaten erfolgreich nach {filename} exportiert.")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen: {e}")

    def create_menu_bar(self):
        """Erstellt eine Menüleiste für erweiterte Optionen."""
        try:
            menubar = self.menuBar()
            
            # Ansicht-Menü
            view_menu = menubar.addMenu('Ansicht')
            
            # Vollbild-Action
            fullscreen_action = view_menu.addAction('Vollbild')
            fullscreen_action.setShortcut('F11')
            fullscreen_action.triggered.connect(self.toggle_fullscreen)
            
            # Zoom-Aktionen für Charts
            view_menu.addSeparator()
            zoom_in_action = view_menu.addAction('Vergrößern')
            zoom_in_action.setShortcut('Ctrl++')
            zoom_in_action.triggered.connect(self.zoom_in_chart)
            
            zoom_out_action = view_menu.addAction('Verkleinern')
            zoom_out_action.setShortcut('Ctrl+-')
            zoom_out_action.triggered.connect(self.zoom_out_chart)
            
            # Datei-Menü
            file_menu = menubar.addMenu('Datei')
            export_action = file_menu.addAction('Exportieren...')
            export_action.setShortcut('Ctrl+E')
            export_action.triggered.connect(self.export_data)
        except Exception as e:
            print(f"Menüleiste konnte nicht erstellt werden: {e}")

    def setup_shortcuts(self):
        """Setzt Tastenkürzel für bessere Benutzerfreundlichkeit auf."""
        try:
            from PySide6.QtGui import QShortcut, QKeySequence
            
            # Prüfe, ob alle Widgets existieren
            if hasattr(self, 'input_field') and hasattr(self, 'skin_list'):
                # Enter zum Hinzufügen von Skins
                add_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.input_field)
                add_shortcut.activated.connect(self.add_skin)
                
                # Delete zum Entfernen
                delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.skin_list)
                delete_shortcut.activated.connect(self.remove_skin)
        except Exception as e:
            print(f"Shortcuts konnten nicht erstellt werden: {e}")

    def toggle_fullscreen(self):
        """Wechselt zwischen Vollbild und Fenster-Modus."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def zoom_in_chart(self):
        """Vergrößert die Chart-Darstellung."""
        try:
            if hasattr(self, 'plot_canvas') and hasattr(self.plot_canvas, 'fig'):
                current_dpi = self.plot_canvas.fig.dpi
                self.plot_canvas.fig.set_dpi(min(current_dpi * 1.2, 200))
                self.plot_canvas.draw()
        except Exception as e:
            print(f"Chart-Zoom nicht möglich: {e}")

    def zoom_out_chart(self):
        """Verkleinert die Chart-Darstellung."""
        try:
            if hasattr(self, 'plot_canvas') and hasattr(self.plot_canvas, 'fig'):
                current_dpi = self.plot_canvas.fig.dpi
                self.plot_canvas.fig.set_dpi(max(current_dpi * 0.8, 50))
                self.plot_canvas.draw()
        except Exception as e:
            print(f"Chart-Zoom nicht möglich: {e}")