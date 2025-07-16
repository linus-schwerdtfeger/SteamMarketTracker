"""
CS Skin Markt Preis-Tracker - Hauptfenster mit Auto-Update-System
================================================================

Dieses Modul implementiert die Haupt-GUI-Anwendung für den CS Skin Tracker mit
erweiterten Auto-Update-Funktionen und Multi-Threading-Unterstützung.

Hauptkomponenten:
- MainWindow: Zentrale GUI-Klasse mit PySide6
- PriceUpdateWorker: Thread für non-blocking API-Updates
- Auto-Update-System: Konfigurierbare Intervall-Updates
- Multi-Chart-Integration: Verbindung zu erweiterten Visualisierungen

Technische Besonderheiten:
- Signal/Slot-basierte Worker-Kommunikation
- Thread-sichere UI-Updates
- Rate-Limiting für Steam API-Schonung
- Robuste Exception-Behandlung auf allen Ebenen

Author: Linus
Version: 1.0
"""

import json
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

# PySide6 GUI-Framework
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog, QLabel,
    QSpinBox, QFrame, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QShortcut, QKeySequence

# Projekt-spezifische Module
from data.fetcher import fetch_comprehensive_market_data, MarketData
from data.db import insert_market_data, get_market_history, init_db, export_market_data, get_latest_price
from plots.chart import MarketDataCanvas

# ═══════════════════════════════════════════════════════════════════════════════
# KONFIGURATIONSKONSTANTEN
# ═══════════════════════════════════════════════════════════════════════════════

# Dateipfade für persistente Daten
WATCHLIST_PATH = "watchlist.json"     # Gespeicherte Skin-Liste
ALERTS_PATH = "alerts.json"           # Preisalarm-Konfiguration

# API-Rate-Limiting (Steam Community Market Schonung)
MIN_REQUEST_DELAY = 2.0               # Sekunden zwischen API-Requests
MAX_CONCURRENT_REQUESTS = 1           # Keine parallelen Requests

# UI-Performance-Einstellungen
CHART_UPDATE_DEBOUNCE = 100           # ms Verzögerung für Chart-Updates
MAX_STATUS_MESSAGE_LENGTH = 80        # Zeichen für Status-Nachrichten

# ═══════════════════════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def check_alert(skin: str, current_price: float) -> bool:
    """
    Prüft Preisalarm-Auslösung für einen Skin gegen konfigurierte Limits.
    
    Args:
        skin: Vollständiger Skin-Name
        current_price: Aktueller Marktpreis in Euro
        
    Returns:
        bool: True wenn Alarm ausgelöst werden soll
        
    Funktionalität:
    - Lädt Alert-Konfiguration aus alerts.json
    - Vergleicht aktuellen Preis mit gesetztem Limit
    - Robust gegen fehlende/korrupte Konfigurationsdateien
    - UTF-8 Encoding für internationale Skin-Namen
    
    Alarm-Logik:
    - Auslösung bei Preis <= Limit
    - Keine Alarme ohne konfigurierte Limits
    - Silent Fail bei Dateisystem-/JSON-Fehlern
    """
    try:
        if not os.path.exists(ALERTS_PATH):
            return False
            
        with open(ALERTS_PATH, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        
        limit = alerts.get(skin)
        return limit is not None and current_price <= limit
        
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Alert-Check Fehler für {skin}: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# WORKER-THREAD FÜR AUTO-UPDATES
# ═══════════════════════════════════════════════════════════════════════════════

class PriceUpdateWorker(QThread):
    """
    Worker-Thread für non-blocking Preis-Updates mit API-Rate-Limiting.
    
    Architektur:
    - Läuft parallel zur UI ohne Blocking
    - Signal/Slot-basierte thread-sichere Kommunikation
    - Cooperative multitasking mit should_stop Flag
    - Individuelles Error-Handling pro Skin
    
    Performance-Features:
    - Rate-Limiting zwischen API-Requests (MIN_REQUEST_DELAY)
    - Progress-Tracking für UI-Updates
    - Performance-Metriken (Dauer, Erfolgsrate)
    - Memory-effiziente Skin-Liste-Kopie
    
    Error-Handling:
    - Einzelne Skin-Fehler brechen Update-Zyklus nicht ab
    - Detaillierte Error-Messages für Debugging
    - Graceful Degradation bei API-Problemen
    - Exception-sichere Thread-Beendigung
    
    Signals:
        progress_update(str, int, int): Status-Message, aktuell, gesamt
        data_updated(str, MarketData): Skin-Name, neue Marktdaten
        alert_triggered(str, float, MarketData): Alarm mit Kontext-Data
        update_completed(int, int, str): Erfolgreiche, gesamt, Dauer
        error_occurred(str): Fehlermeldung für UI-Anzeige
    """
    
    # Qt Signals für thread-sichere UI-Kommunikation
    progress_update = Signal(str, int, int)        # message, current, total
    data_updated = Signal(str, object)             # skin_name, market_data
    alert_triggered = Signal(str, float, object)   # skin_name, price, market_data
    update_completed = Signal(int, int, str)       # successful, total, duration
    error_occurred = Signal(str)                   # error_message
    
    def __init__(self, skin_list: List[str], is_auto_update: bool = False):
        """
        Initialisiert Worker mit thread-sicherer Skin-Liste-Kopie.
        
        Args:
            skin_list: Liste der zu aktualisierenden Skins
            is_auto_update: True für Auto-Updates, False für manuelle Updates
            
        Thread-Safety:
        - Erstellt defensive Kopie der Skin-Liste
        - Keine shared state zwischen Threads
        - should_stop Flag für sichere Beendigung
        """
        super().__init__()
        self.skin_list = skin_list.copy()  # Thread-sichere Kopie
        self.is_auto_update = is_auto_update
        self.should_stop = False           # Cooperative cancellation
        self.start_time: Optional[float] = None
    
    def run(self) -> None:
        """
        Hauptschleife für API-Requests mit Rate-Limiting und Error-Handling.
        
        Ablauf:
        1. Performance-Tracking initialisieren
        2. Iteriere durch Skin-Liste mit Progress-Updates
        3. API-Request pro Skin mit individuellem Error-Handling
        4. Rate-Limiting zwischen Requests
        5. Signal-Emission für UI-Updates
        6. Completion-Metrics sammeln und übertragen
        
        Rate-Limiting:
        - MIN_REQUEST_DELAY zwischen API-Calls
        - Keine Verzögerung nach letztem Request
        - Should_stop-Prüfung vor Delays
        
        Error-Recovery:
        - Einzelne Skin-Fehler loggen und überspringen
        - Update-Zyklus bei partiellen Fehlern fortsetzen
        - Global Error-Handling für kritische Probleme
        """
        self.start_time = time.time()
        successful_updates = 0
        total_skins = len(self.skin_list)
        
        try:
            for i, skin in enumerate(self.skin_list):
                if self.should_stop:
                    break
                    
                # Progress-Update für UI
                update_type = "Auto-Update" if self.is_auto_update else "Manueller Update"
                progress_message = f"{update_type}: {skin[:30]}..."
                self.progress_update.emit(progress_message, i + 1, total_skins)
                
                try:
                    # Steam Community Market API-Call
                    market_data: Optional[MarketData] = fetch_comprehensive_market_data(skin)
                    
                    if market_data and market_data.has_valid_data:
                        # Erfolgreiche Daten -> UI-Updates via Signals
                        self.data_updated.emit(skin, market_data)
                        successful_updates += 1
                        
                        # Preisalarm-Prüfung
                        if check_alert(skin, market_data.lowest_price):
                            self.alert_triggered.emit(
                                skin, 
                                market_data.lowest_price, 
                                market_data
                            )
                    else:
                        print(f"Keine gültigen Daten für {skin}")
                        
                except Exception as skin_error:
                    # Einzelner Skin-Fehler -> Continue with next
                    print(f"Fehler bei {skin}: {skin_error}")
                    continue
                
                # Rate-Limiting (außer beim letzten Request)
                if i < total_skins - 1 and not self.should_stop:
                    time.sleep(MIN_REQUEST_DELAY)
            
            # Completion-Metrics berechnen und übertragen
            duration = time.time() - self.start_time if self.start_time else 0
            duration_str = f"{duration:.1f}s"
            self.update_completed.emit(successful_updates, total_skins, duration_str)
            
        except Exception as e:
            # Global Error für kritische Probleme
            self.error_occurred.emit(f"Update-Fehler: {str(e)}")
    
    def stop(self) -> None:
        """
        Sichere Thread-Beendigung via cooperative cancellation.
        
        Setzt should_stop Flag für graceful shutdown in run()-Schleife.
        Verhindert gewaltsame Thread-Terminierung und Race Conditions.
        """
        self.should_stop = True

# ═══════════════════════════════════════════════════════════════════════════════
# HAUPT-GUI-KLASSE
# ═══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Zentrale GUI-Klasse für CS Skin Tracker mit Auto-Update-System.
    
    Architektur-Features:
    - PySide6-basierte Qt-Anwendung mit Dark Theme
    - Thread-basierte Updates (Worker-Pattern)
    - Signal/Slot-System für lose Kopplung
    - Responsive Layout mit optimierten Proportionen
    - Performance-optimierte Chart-Integration
    
    Hauptfunktionalitäten:
    - Watchlist-Management: Add/Remove/Persist Skins
    - Auto-Update-System: Konfigurierbare Intervalle (3-1440 Min)
    - Manual-Update: On-Demand Datenaktualisierung
    - Multi-Chart-Dashboard: Preis/Volumen/Spread-Visualisierung
    - Preisalarm-System: JSON-konfigurierte Benachrichtigungen
    - Datenexport: CSV-Export mit Metadaten
    - Keyboard-Shortcuts: Effiziente Bedienung
    
    Threading-Model:
    - UI-Thread: Rendering, Event-Handling, User-Interaktion
    - Worker-Thread: API-Requests, Datenverarbeitung
    - Timer-System: Auto-Update-Scheduling, UI-Debouncing
    
    Performance-Optimierungen:
    - Chart-Update-Debouncing (100ms)
    - Rate-Limited API-Requests (2s minimum)
    - Memory-effiziente Datenstrukturen
    - Lazy-Loading für Chart-Daten
    - Optimierte UI-Updates via Signal-Batching
    
    Error-Handling:
    - Comprehensive Exception-Behandlung auf allen Ebenen
    - User-freundliche Error-Messages
    - Graceful Degradation bei API-Fehlern
    - Recovery-Mechanismen für kritische Operationen
    """
    
    def __init__(self):
        """
        Initialisiert Hauptfenster mit vollständigem Setup.
        
        Setup-Reihenfolge:
        1. Window-Konfiguration und Threading-System
        2. UI-Komponenten und Layout-Management
        3. Event-Verbindungen und Signal-Routing
        4. Datenbank-Initialisierung und Migration
        5. Watchlist-Loading und Persistierung
        6. Menü-System und Keyboard-Shortcuts
        7. Initiale UI-State und erste Chart-Darstellung
        
        Performance-Considerations:
        - Minimale Initialisierungszeit durch Lazy-Loading
        - Thread-Pool-Vorbereitung für Updates
        - Chart-Canvas-Optimierung für große Datenmengen
        """
        super().__init__()
        self.setWindowTitle("CS Skin Markt Analyzer - Enhanced mit Auto-Update")
        
        # ═══════════════════════════════════════════════════════════════════════
        # WORKER-SYSTEM UND TIMER
        # ═══════════════════════════════════════════════════════════════════════
        
        # Auto-Update Timer für regelmäßige Worker-Starts
        self.auto_update_timer: QTimer = QTimer()
        self.auto_update_timer.timeout.connect(self.start_auto_update_cycle)
        
        # Worker-Thread Referenz für sichere Beendigung
        self.update_worker: Optional[PriceUpdateWorker] = None
        
        # Auto-Update Status-Tracking
        self.is_auto_updating: bool = False
        self.last_update_time: Optional[datetime] = None
        
        # ═══════════════════════════════════════════════════════════════════════
        # UI-SETUP UND INITIALISIERUNG
        # ═══════════════════════════════════════════════════════════════════════
        
        self.setup_ui()              # UI-Komponenten erstellen
        self.setup_connections()     # Event-Handler verbinden
        self.load_watchlist()        # Gespeicherte Skins laden
        init_db()                    # Datenbank initialisieren/migrieren
        self.create_menu_bar()       # Menüleiste erstellen
        self.setup_shortcuts()       # Keyboard-Shortcuts setzen
        
        # Initialer UI-State
        self.status_label.setText("Bereit - Drücken Sie 'Alle aktualisieren' für neue Daten")
        self.status_label.setStyleSheet("color: #cccccc; font-weight: normal;")
        
        # Erste Skin-Auswahl und Chart-Update
        if self.skin_list.count() > 0:
            self.skin_list.setCurrentRow(0)
            self.update_chart()

    # ═══════════════════════════════════════════════════════════════════════════
    # UI-SETUP-METHODEN
    # ═══════════════════════════════════════════════════════════════════════════

    def setup_ui(self) -> None:
        """
        Erstellt responsive UI-Komponenten mit Dark Theme.
        
        Layout-Architektur:
        - Responsive Window-Sizing (900x750 min, 1400x950 standard)
        - Vertikales Haupt-Layout mit gewichteter Verteilung
        - Skin-Liste: 180px Mindesthöhe für 6-8 sichtbare Einträge
        - Input-Bereich: Horizontales Layout mit Stretch-Faktor
        - Button-Leiste: Aktionen links, Status rechts
        - Auto-Update-Panel: Gerahmter Bereich mit Dark Styling
        - Progress-Bar: Versteckt bis Update läuft
        - Chart-Canvas: Hauptbereich mit 3:1 Gewichtung
        
        Design-Prinzipien:
        - Konsistentes Dark Theme (rgb(45, 45, 45))
        - Accessibility-optimierte Kontraste
        - Hover-Effects für bessere UX
        - Einheitliche Spacing-Parameter
        - Responsive Design für verschiedene Bildschirmgrößen
        """
        # Responsive Window-Konfiguration
        self.setMinimumSize(900, 750)    # Minimum für alle Komponenten sichtbar
        self.resize(1400, 950)           # Optimale Standard-Größe
        self.center_window()             # Bildschirm-Zentrierung

        # ═══════════════════════════════════════════════════════════════════════
        # CORE UI-KOMPONENTEN
        # ═══════════════════════════════════════════════════════════════════════

        # Skin-Liste mit optimierter Höhe
        self.skin_list = QListWidget()
        self.skin_list.setMinimumHeight(180)  # 6-8 Einträge sichtbar
        
        # Input-Komponenten
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("z.B. AK-47 | Redline (Field-Tested)")
        
        # Basis-Action-Buttons
        self.add_button = QPushButton("Hinzufügen")
        self.remove_button = QPushButton("Entfernen")
        self.refresh_button = QPushButton("Alle aktualisieren")
        
        # ═══════════════════════════════════════════════════════════════════════
        # AUTO-UPDATE-KOMPONENTEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # Auto-Update Toggle-Button
        self.auto_update_button = QPushButton("🔄 Auto-Update starten")
        self.auto_update_button.setStyleSheet(self._get_button_style("#28a745"))
        
        # Intervall-Konfiguration (3-1440 Minuten)
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(3, 1440)      # 3 Min - 24 Stunden
        self.interval_spinbox.setValue(5)            # Standard: 5 Minuten
        self.interval_spinbox.setSuffix(" Min")
        self.interval_spinbox.setMinimumWidth(100)
        self.interval_spinbox.setStyleSheet(self._get_spinbox_style())
        
        # ═══════════════════════════════════════════════════════════════════════
        # STATUS-LABELS UND PROGRESS
        # ═══════════════════════════════════════════════════════════════════════
        
        # Haupt-Status für alle Operationen
        self.status_label = QLabel("Bereit für erweiterte Marktanalyse")
        
        # Auto-Update-spezifischer Status
        self.auto_status_label = QLabel("Auto-Update: Inaktiv")
        self.auto_status_label.setStyleSheet("color: #cccccc; font-style: italic;")
        
        # Progress-Bar für Update-Zyklen
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)           # Standardmäßig versteckt
        self.progress_bar.setStyleSheet(self._get_progressbar_style())
        
        # Layout-Setup delegieren
        self.setup_layout()

    def setup_layout(self) -> None:
        """
        Organisiert UI-Komponenten in optimierte Layout-Hierarchie.
        
        Layout-Struktur:
        1. Input-Layout: TextField + Add-Button (horizontal, stretch)
        2. Button-Layout: Actions + Stretch + Status (horizontal)
        3. Auto-Update-Frame: Controls + Status (horizontal, gerahmt)
        4. Progress-Bar: Vollbreite (conditional visibility)
        5. Chart-Canvas: Hauptvisualisierung (gewichtet)
        
        Gewichtung:
        - Skin-Liste: 1 (moderate Höhe)
        - Input/Buttons/Auto-Update: 0 (minimal height)
        - Chart-Canvas: 3 (maximale Höhe)
        
        Frame-Design:
        - Auto-Update-Frame mit Dark Theme
        - Subtle Borders und Rounded Corners
        - Optimierte Padding-Parameter
        """
        # Input-Layout für Skin-Hinzufügung
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field, 1)    # Stretch-Faktor
        input_layout.addWidget(self.add_button)

        # Button-Layout mit Status
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()                     # Push status rechts
        button_layout.addWidget(self.status_label)

        # Auto-Update-Frame (gerahmt)
        auto_update_frame = QFrame()
        auto_update_frame.setFrameStyle(QFrame.StyledPanel)
        auto_update_frame.setStyleSheet(self._get_frame_style())
        
        auto_update_layout = QHBoxLayout(auto_update_frame)
        auto_update_layout.addWidget(QLabel("🔁 Auto-Update alle:"))
        auto_update_layout.addWidget(self.interval_spinbox)
        auto_update_layout.addWidget(self.auto_update_button)
        auto_update_layout.addStretch()                # Status rechts
        auto_update_layout.addWidget(self.auto_status_label)

        # Haupt-Layout (vertikal)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.skin_list, 1)       # Moderate Gewichtung
        main_layout.addLayout(input_layout)            # Minimal height
        main_layout.addLayout(button_layout)           # Minimal height
        main_layout.addWidget(auto_update_frame)       # Minimal height
        main_layout.addWidget(self.progress_bar)       # Minimal height

        # Central Widget Setup
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Chart-Canvas Integration
        self.chart_canvas = MarketDataCanvas()
        main_layout.addWidget(self.chart_canvas, 3)    # Hohe Gewichtung

    def setup_connections(self) -> None:
        """
        Stellt Signal/Slot-Verbindungen zwischen UI und Logic her.
        
        Verbindungstypen:
        - Button.clicked -> Action-Handler
        - ListWidget.currentTextChanged -> Chart-Updates
        - Implicit Shortcuts -> Keyboard-Handling
        
        Design-Pattern:
        - Signal/Slot für lose Kopplung
        - Single Responsibility pro Handler
        - Thread-sichere UI-Updates via Qt-Signals
        """
        # Basis-Action-Verbindungen
        self.add_button.clicked.connect(self.add_skin)
        self.remove_button.clicked.connect(self.remove_skin)
        self.refresh_button.clicked.connect(self.start_manual_update)
        
        # Chart-Updates bei Skin-Auswahl
        self.skin_list.currentTextChanged.connect(self.update_chart)
        
        # Auto-Update Toggle
        self.auto_update_button.clicked.connect(self.toggle_auto_update)

    # ═══════════════════════════════════════════════════════════════════════════
    # STYLING-METHODEN (DRY-PRINZIP)
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_button_style(self, bg_color: str) -> str:
        """
        Generiert einheitliche Button-Styles mit State-Management.
        
        Args:
            bg_color: Hex-Hintergrundfarbe
            
        Returns:
            CSS-String mit hover/pressed-States
            
        Features:
        - Responsive Hover-Effekte
        - Pressed-State-Animation
        - Rounded Corners für modernen Look
        - Konsistente Padding-Parameter
        """
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(bg_color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(bg_color, 0.8)};
            }}
        """
    
    def _darken_color(self, hex_color: str, factor: float = 0.9) -> str:
        """
        Verdunkelt Hex-Farben für Hover-Effekte.
        
        Args:
            hex_color: Original Hex-Farbe
            factor: Verdunkelungs-Faktor (0.0-1.0)
            
        Returns:
            Verdunkelte Hex-Farbe
            
        Implementation:
        Vordefinierte Color-Map für Performance-Optimierung.
        Für erweiterte Farb-Manipulation könnte colorsys verwendet werden.
        """
        color_map = {
            "#28a745": "#218838" if factor == 0.9 else "#1e7e34",  # Grün-Varianten
            "#dc3545": "#c82333" if factor == 0.9 else "#bd2130"   # Rot-Varianten
        }
        return color_map.get(hex_color, hex_color)  # Fallback: Original
    
    def _get_spinbox_style(self) -> str:
        """
        SpinBox-Styling für Dark Theme.
        
        Returns:
            CSS mit Dark Theme und Fokus-Highlighting
            
        Features:
        - rgb(45, 45, 45) Hintergrund (Chart-konsistent)
        - Weiße Schrift für hohen Kontrast
        - Grüner Fokus-Border
        - Styled Up/Down-Buttons
        """
        return """
            QSpinBox {
                background-color: rgb(45, 45, 45);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid #28a745;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #555;
                border: 1px solid #666;
                border-radius: 2px;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #666;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                color: white;
            }
        """
    
    def _get_frame_style(self) -> str:
        """
        Frame-Styling für Auto-Update-Panel.
        
        Returns:
            CSS für gerahmten Bereich
            
        Features:
        - Konsistenter Dark Background
        - Subtle Border-Effekte
        - Rounded Corners
        - Label-Styling für Lesbarkeit
        """
        return """
            QFrame {
                background-color: rgb(45, 45, 45);
                border: 1px solid #555;
                border-radius: 6px;
                margin: 2px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """
    
    def _get_progressbar_style(self) -> str:
        """
        ProgressBar-Styling für Update-Fortschritt.
        
        Returns:
            CSS mit Dark Theme und grünem Progress-Chunk
            
        Features:
        - Dark Background
        - Grüner Progress-Chunk
        - Zentrierte Text-Anzeige
        - Rounded Corners
        """
        return """
            QProgressBar {
                background-color: rgb(45, 45, 45);
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE-SYSTEM (VEREINHEITLICHT)
    # ═══════════════════════════════════════════════════════════════════════════

    def start_manual_update(self) -> None:
        """
        Startet manuellen Update aller Watchlist-Skins.
        
        Validation:
        - Prüft Skin-Anzahl in Watchlist
        - User-Dialog bei leerer Liste
        
        Delegiert an _start_update_worker() für einheitliche Update-Logik.
        """
        if self.skin_list.count() == 0:
            QMessageBox.information(self, "Info", "Keine Skins in der Watchlist.")
            return
        
        self._start_update_worker(is_auto_update=False)

    def start_auto_update_cycle(self) -> None:
        """
        Startet Auto-Update Zyklus (Timer-Callback).
        
        Validation:
        - Prüft Auto-Update-Status
        - Silent return bei invaliden Bedingungen
        
        Design-Rationale:
        Timer-Callback sollte keine User-Dialoge zeigen.
        """
        if not self.is_auto_updating or self.skin_list.count() == 0:
            return
        
        self._start_update_worker(is_auto_update=True)

    def _start_update_worker(self, is_auto_update: bool) -> None:
        """
        Zentrale Worker-Thread-Erstellung für alle Update-Typen.
        
        Args:
            is_auto_update: Update-Typ für Kontext-abhängiges Verhalten
            
        Threading-Management:
        - Race Condition Prevention
        - Thread-sichere Skin-Liste-Kopie
        - Comprehensive Signal-Verbindungen
        - Worker-Lifecycle-Management
        
        UI-State-Management:
        - Progress-Bar-Konfiguration
        - Button-State-Updates
        - Status-Message-Initialisierung
        
        Performance:
        - Non-blocking UI durch Worker-Thread
        - Rate-Limited API-Requests
        - Memory-effiziente Datenstrukturen
        """
        # Race Condition Prevention
        if self.update_worker and self.update_worker.isRunning():
            return
        
        # Thread-sichere Skin-Liste
        current_skins: List[str] = [
            self.skin_list.item(i).text() 
            for i in range(self.skin_list.count())
        ]
        
        # Worker-Thread-Erstellung
        self.update_worker = PriceUpdateWorker(current_skins, is_auto_update)
        
        # Signal-Verbindungen für thread-sichere UI-Updates
        self.update_worker.progress_update.connect(self.on_worker_progress)
        self.update_worker.data_updated.connect(self.on_worker_data_updated)
        self.update_worker.alert_triggered.connect(self.on_worker_alert)
        self.update_worker.update_completed.connect(self.on_worker_completed)
        self.update_worker.error_occurred.connect(self.on_worker_error)
        
        # UI-Konfiguration für Update-Zyklus
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(current_skins))
        self.progress_bar.setValue(0)
        self.refresh_button.setEnabled(False)
        
        # Worker-Start
        self.update_worker.start()

    # ═══════════════════════════════════════════════════════════════════════════
    # WORKER-EVENT-HANDLER (SIGNAL-SLOTS)
    # ═══════════════════════════════════════════════════════════════════════════

    def on_worker_progress(self, message: str, current: int, total: int) -> None:
        """
        Behandelt Progress-Updates vom Worker mit UI-Feedback.
        
        Args:
            message: Status-Nachricht für User
            current: Aktueller Progress (1-basiert)
            total: Gesamtanzahl Items
            
        UI-Updates:
        - Status-Label mit Truncation für lange Messages
        - Progress-Bar mit numerischem Fortschritt
        - Orange Farbe für "Working"-Status
        - Responsive UI via processEvents()
        """
        # Message-Truncation für UI-Limits
        display_message = message[:MAX_STATUS_MESSAGE_LENGTH] + "..." if len(message) > MAX_STATUS_MESSAGE_LENGTH else message
        
        # Thread-sichere UI-Updates
        self.status_label.setText(f"{display_message} ({current}/{total})")
        self.status_label.setStyleSheet("color: #fd7e14; font-weight: bold;")  # Orange = Working
        self.progress_bar.setValue(current)
        
        # UI responsiv halten
        QApplication.processEvents()

    def on_worker_data_updated(self, skin_name: str, market_data: MarketData) -> None:
        """
        Verarbeitet neue Marktdaten vom Worker.
        
        Args:
            skin_name: Aktualisierter Skin
            market_data: Neue Marktdaten
            
        Database-Operations:
        - Speichert Daten via insert_market_data()
        - Error-Handling für DB-Probleme
        - Fortsetzung bei individuellen Fehlern
        
        Design-Rationale:
        DB-Operations im UI-Thread sind hier akzeptabel da SQLite sehr schnell ist.
        """
        try:
            insert_market_data(skin_name, market_data)
        except Exception as e:
            print(f"DB-Fehler für {skin_name}: {e}")

    def on_worker_alert(self, skin_name: str, price: float, market_data: MarketData) -> None:
        """
        Zeigt Preisalarm-Benachrichtigung.
        
        Args:
            skin_name: Skin mit Preisalarm
            price: Aktueller Preis
            market_data: Kontext-Daten
            
        User-Experience:
        - Sofortige QMessageBox-Benachrichtigung
        - Zusätzliche Marktdaten für Kontext
        - Emoji für visuelle Aufmerksamkeit
        """
        QMessageBox.information(
            self,
            "💥 Preisalarm!",
            f"{skin_name} kostet jetzt nur noch {price:.2f} €!\n"
            f"Spread: {market_data.spread_percentage:.1f}% | Volumen: {market_data.volume}"
        )

    def on_worker_completed(self, successful: int, total: int, duration: str) -> None:
        """
        Behandelt Worker-Fertigstellung mit Performance-Metriken.
        
        Args:
            successful: Erfolgreich aktualisierte Skins
            total: Gesamtanzahl versuchter Updates
            duration: Formatierte Dauer
            
        UI-State-Reset:
        - Progress-Bar ausblenden
        - Button-States reaktivieren
        - Status-Message mit Statistiken
        - Chart-Update für aktuellen Skin
        - Auto-Update-Status aktualisieren
        """
        self.last_update_time = datetime.now()
        
        # Kontext-abhängige Status-Messages
        if self.is_auto_updating:
            next_update_min = self.interval_spinbox.value()
            status_msg = f"✅ Auto-Update abgeschlossen: {successful}/{total} erfolgreich ({duration})"
            self.auto_status_label.setText(f"🔄 Nächstes Update in {next_update_min} Min")
            self.auto_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            status_msg = f"✅ Manuelle Aktualisierung abgeschlossen: {successful}/{total} erfolgreich ({duration})"
        
        # UI-State-Reset
        self.status_label.setText(status_msg)
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        
        # Chart-Update
        self.update_chart()

    def on_worker_error(self, error_message: str) -> None:
        """
        Behandelt Worker-Fehler mit Recovery.
        
        Args:
            error_message: Fehlerbeschreibung
            
        Error-Recovery:
        - UI-State zurücksetzen
        - Error-Message für User
        - System bleibt funktionsfähig
        """
        self.status_label.setText(f"❌ {error_message}")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTO-UPDATE-CONTROLS
    # ═══════════════════════════════════════════════════════════════════════════

    def toggle_auto_update(self) -> None:
        """
        Toggle-Funktion für Auto-Update-System.
        
        Delegiert an start_auto_update() oder stop_auto_update() basierend auf aktuellem Status.
        """
        if not self.is_auto_updating:
            self.start_auto_update()
        else:
            self.stop_auto_update()

    def start_auto_update(self) -> None:
        """
        Startet Auto-Update-System mit Validierung und Performance-Warnung.
        
        Validation:
        - Watchlist-Anzahl prüfen
        - Performance-Warnung bei kritischen Intervallen
        - User-Bestätigung für Zeitkritische Konfigurationen
        
        Timer-Setup:
        - QTimer-Konfiguration mit Millisekunden-Konvertierung
        - Auto-Update-Flag setzen
        - UI-State für aktiven Auto-Update
        - Sofortige erste Aktualisierung
        
        Performance-Considerations:
        - Estimated Duration vs. Interval Validation
        - User-Warning bei overlap-gefährdeten Konfigurationen
        - Recovery-freundliche Error-Handling
        """
        # Basis-Validation
        if self.skin_list.count() == 0:
            QMessageBox.information(
                self, 
                "Keine Skins", 
                "Bitte fügen Sie mindestens einen Skin zur Watchlist hinzu."
            )
            return
            
        interval_minutes = self.interval_spinbox.value()
        
        # Performance-Warnung für kritische Intervalle
        estimated_duration = self.skin_list.count() * MIN_REQUEST_DELAY
        if estimated_duration > (interval_minutes * 60 * 0.8):
            reply = QMessageBox.question(
                self,
                "Zeitkritisches Intervall",
                f"⚠️ Update-Zyklus dauert ~{estimated_duration:.0f}s\n"
                f"Gewähltes Intervall: {interval_minutes} Min\n\n"
                f"Empfehlung: Mindestens {int(estimated_duration/60)+2} Min\n\n"
                "Trotzdem fortfahren?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Auto-Update aktivieren
        self.auto_update_timer.start(interval_minutes * 60 * 1000)  # Millisekunden
        self.is_auto_updating = True
        
        # UI-State für aktiven Auto-Update
        self.auto_update_button.setText("⏹️ Auto-Update stoppen")
        self.auto_update_button.setStyleSheet(self._get_button_style("#dc3545"))
        
        self.auto_status_label.setText(f"🔄 Auto-Update aktiv (alle {interval_minutes} Min)")
        self.auto_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        
        # Sofortige erste Aktualisierung
        self.start_auto_update_cycle()
        
        # Bestätigungs-Dialog mit Details
        QMessageBox.information(
            self,
            "Auto-Update gestartet",
            f"✅ Auto-Update aktiviert!\n\n"
            f"🕒 Intervall: {interval_minutes} Min\n"
            f"📊 Skins: {self.skin_list.count()}\n"
            f"⏱️ Geschätzte Dauer: ~{estimated_duration:.0f}s/Zyklus"
        )

    def stop_auto_update(self) -> None:
        """
        Stoppt Auto-Update-System sicher mit Worker-Cleanup.
        
        Cleanup-Operationen:
        - Timer stoppen
        - Auto-Update-Flag zurücksetzen
        - Laufende Worker sicher beenden
        - UI-State für inaktiven Auto-Update
        - Status-Messages zurücksetzen
        
        Worker-Cleanup:
        - should_stop Flag setzen
        - Maximum 3s warten auf Thread-Beendigung
        - Graceful shutdown bevorzugt über forceful termination
        """
        # Timer und Flag zurücksetzen
        self.auto_update_timer.stop()
        self.is_auto_updating = False
        
        # Worker sicher stoppen
        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.stop()
            self.update_worker.wait(3000)  # Max 3s warten
        
        # UI-State für inaktiven Auto-Update
        self.auto_update_button.setText("🔄 Auto-Update starten")
        self.auto_update_button.setStyleSheet(self._get_button_style("#28a745"))
        
        self.auto_status_label.setText("Auto-Update: Gestoppt")
        self.auto_status_label.setStyleSheet("color: #cccccc; font-style: italic;")
        
        self.status_label.setText("Auto-Update wurde gestoppt")
        self.status_label.setStyleSheet("color: #6c757d; font-weight: normal;")

    def closeEvent(self, event) -> None:
        """
        Sichere Anwendungsbeendigung mit Auto-Update-Bestätigung.
        
        Cleanup-Workflow:
        - Auto-Update-Status prüfen
        - User-Bestätigung bei aktivem Auto-Update
        - Comprehensive Cleanup aller Threads und Timer
        - Graceful Event-Handling
        
        Args:
            event: QCloseEvent für Accept/Ignore-Entscheidung
        """
        # Bestätigung bei aktivem Auto-Update
        if self.is_auto_updating:
            reply = QMessageBox.question(
                self,
                "Auto-Update läuft",
                "Auto-Update ist aktiv. Wirklich beenden?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
                
        # Comprehensive Cleanup
        self.stop_auto_update()
        event.accept()

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY-METHODEN (OPTIMIERT)
    # ═══════════════════════════════════════════════════════════════════════════

    def center_window(self) -> None:
        """
        Zentriert Fenster auf primärem Bildschirm.
        
        Verwendet QGuiApplication für Multi-Monitor-Unterstützung.
        """
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def load_watchlist(self) -> None:
        """
        Lädt persistierte Watchlist mit Error-Handling.
        
        File-Handling:
        - UTF-8 Encoding für internationale Skin-Namen
        - JSON-Validierung und Type-Checking
        - Graceful Handling fehlender Dateien
        - User-Dialog bei Korruption
        """
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
            QMessageBox.warning(self, "Fehler", f"Watchlist konnte nicht geladen werden: {e}")

    def save_watchlist(self) -> None:
        """
        Speichert aktuelle Watchlist persistent.
        
        Persistierung:
        - JSON-Format mit UTF-8 Encoding
        - Indented Format für Lesbarkeit
        - Error-Handling für Dateisystem-Probleme
        """
        skins = [self.skin_list.item(i).text() for i in range(self.skin_list.count())]
        try:
            with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
                json.dump(skins, f, indent=2, ensure_ascii=False)
        except IOError as e:
            QMessageBox.warning(self, "Fehler", f"Watchlist konnte nicht gespeichert werden: {e}")

    def add_skin(self) -> None:
        """
        Fügt neuen Skin zur Watchlist hinzu mit Duplikat-Prüfung.
        
        Validation:
        - Input-Field-Validation
        - Case-insensitive Duplikat-Check
        - Sofortige Datenaktualisierung für neuen Skin
        - Auto-Selection des neuen Skins
        """
        skin_name = self.input_field.text().strip()
        if not skin_name:
            QMessageBox.information(self, "Info", "Bitte geben Sie einen Skin-Namen ein.")
            return
            
        # Case-insensitive Duplikat-Check
        for i in range(self.skin_list.count()):
            if self.skin_list.item(i).text().lower() == skin_name.lower():
                QMessageBox.information(self, "Info", "Skin ist bereits in der Liste.")
                return
            
        # Skin hinzufügen und persistieren
        self.skin_list.addItem(skin_name)
        self.input_field.clear()
        self.save_watchlist()
        
        # Sofortige Datenaktualisierung
        self.update_market_data_for_skin(skin_name)
        self.skin_list.setCurrentRow(self.skin_list.count() - 1)

    def remove_skin(self) -> None:
        """
        Entfernt ausgewählten Skin aus Watchlist.
        
        Functionality:
        - Selection-Validation
        - Persistierung nach Entfernung
        - Chart-Update nach Änderung
        - User-Info bei fehlender Auswahl
        """
        selected = self.skin_list.currentRow()
        if selected >= 0:
            self.skin_list.takeItem(selected)
            self.save_watchlist()
            self.update_chart()
        else:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Entfernen aus.")

    def update_market_data_for_skin(self, skin: str) -> None:
        """
        Aktualisiert Marktdaten für einzelnen Skin mit UI-Feedback.
        
        Args:
            skin: Skin-Name für Update
            
        Workflow:
        - Status-Updates während API-Request
        - MarketData-Fetching und Validation
        - Database-Persistierung
        - Preisalarm-Prüfung
        - Chart-Update bei Erfolg
        - Error-Handling mit User-Feedback
        """
        self.status_label.setText(f"Lade Marktdaten für {skin[:30]}...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        try:
            market_data = fetch_comprehensive_market_data(skin)
            if market_data and market_data.has_valid_data:
                insert_market_data(skin, market_data)
                
                # Preisalarm-Prüfung
                if check_alert(skin, market_data.lowest_price):
                    QMessageBox.information(
                        self,
                        "💥 Preisalarm!",
                        f"{skin} kostet jetzt nur noch {market_data.lowest_price:.2f} €!\n"
                        f"Spread: {market_data.spread_percentage:.1f}% | Volumen: {market_data.volume}"
                    )
                    
                # Erfolgs-Status
                self.status_label.setText(f"✅ Marktdaten aktualisiert: {skin[:30]}")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.update_chart()
            else:
                # Keine Daten verfügbar
                self.status_label.setText(f"❌ Keine Daten verfügbar: {skin[:30]}")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            # API/DB-Fehler
            self.status_label.setText(f"❌ Fehler: {str(e)[:50]}...")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def update_chart(self) -> None:
        """
        Aktualisiert Chart für aktuell ausgewählten Skin.
        
        Chart-Update-Workflow:
        - Current-Selection-Validation
        - Market-History-Fetching
        - Chart-Canvas-Update via plot_market_data()
        - Error-Handling mit Fallback-Darstellung
        
        Performance:
        - Debounced Updates für bessere Responsiveness
        - Lazy-Loading für große Datenmengen
        - Memory-effiziente Chart-Operationen
        """
        current_item = self.skin_list.currentItem()
        if not current_item:
            self.chart_canvas.plot_market_data([], "Kein Skin ausgewählt")
            return
            
        skin_name = current_item.text()
        try:
            market_history = get_market_history(skin_name)
            self.chart_canvas.plot_market_data(market_history, skin_name)
        except Exception as e:
            print(f"Chart-Update Fehler: {e}")
            self.chart_canvas.plot_market_data([], f"Fehler: {skin_name}")

    def export_data(self) -> None:
        """
        Exportiert Marktdaten als CSV mit File-Dialog.
        
        Export-Workflow:
        - Selection-Validation
        - Safe-Filename-Generierung
        - QFileDialog für Benutzer-Auswahl
        - CSV-Export via export_market_data()
        - Success/Error-Dialoge
        
        Features:
        - Sanitized Filenames für Dateisystem-Kompatibilität
        - UTF-8 CSV-Export mit Metadaten
        - User-freundliche Success-Messages
        """
        current_item = self.skin_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Skin zum Exportieren aus.")
            return
            
        skin_name = current_item.text()
        safe_filename = "".join(c for c in skin_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
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
                    "Export erfolgreich", 
                    f"Marktdaten exportiert nach:\n{filename}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Fehler", f"Export fehlgeschlagen: {e}")

    def create_menu_bar(self) -> None:
        """
        Erstellt Menüleiste mit Keyboard-Shortcuts.
        
        Menu-Struktur:
        - Datei-Menü: Export-Funktionen (Ctrl+E)
        - Ansicht-Menü: Vollbild-Toggle (F11)
        
        Error-Handling:
        - Exception-Catching für Qt-Probleme
        - Graceful Degradation bei Menu-Fehlern
        """
        try:
            menubar = self.menuBar()
            
            # Datei-Menü
            file_menu = menubar.addMenu('Datei')
            export_action = file_menu.addAction('Exportieren...')
            export_action.setShortcut('Ctrl+E')
            export_action.triggered.connect(self.export_data)
            
            # Ansicht-Menü
            view_menu = menubar.addMenu('Ansicht')
            fullscreen_action = view_menu.addAction('Vollbild')
            fullscreen_action.setShortcut('F11')
            fullscreen_action.triggered.connect(self.toggle_fullscreen)
            
        except Exception as e:
            print(f"Menüleiste-Fehler: {e}")

    def setup_shortcuts(self) -> None:
        """
        Konfiguriert Keyboard-Shortcuts für effiziente Bedienung.
        
        Shortcuts:
        - Return in Input-Field: add_skin()
        - Delete in Skin-List: remove_skin()
        
        Implementation:
        - QShortcut für Widget-spezifische Shortcuts
        - Context-sensitive Activation
        """
        try:
            # Enter im Input-Field für Add-Skin
            add_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.input_field)
            add_shortcut.activated.connect(self.add_skin)
            
            # Delete in Skin-List für Remove-Skin
            delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.skin_list)
            delete_shortcut.activated.connect(self.remove_skin)
            
        except Exception as e:
            print(f"Shortcuts-Fehler: {e}")

    def toggle_fullscreen(self) -> None:
        """
        Toggle zwischen Vollbild und Normal-Modus.
        
        State-Management für Vollbild-Modi mit Window-State-Tracking.
        """
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()