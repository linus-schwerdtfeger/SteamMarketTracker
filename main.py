"""
CS Skin Markt Preis-Tracker - Anwendungs-Einstiegspunkt
======================================================

Diese Datei dient als Haupteinstiegspunkt für die CS Skin Tracker-Anwendung.
Sie initialisiert das Qt-Framework, konfiguriert die Anwendung und startet die GUI.

Technische Details:
- PySide6-basierte Qt-Anwendung
- Single-Window-Architektur
- Graceful Exit-Handling
- Application-Metadaten-Konfiguration

Design-Pattern:
- Main-Function-Pattern für strukturierten Startup
- Exception-Handling für robuste Fehlerbehandlung
- Sys.exit() für ordnungsgemäße Beendigung

Author: Linus
Version: 1.0

Usage:
    python main.py
"""

import sys
from typing import NoReturn

# PySide6 Qt-Framework
from PySide6.QtWidgets import QApplication

# Projekt-spezifische Module
from ui.main_window import MainWindow

# ═══════════════════════════════════════════════════════════════════════════════
# ANWENDUNGS-METADATEN
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "CS Skin Markt Preis-Tracker"
APP_VERSION = "1.0"
APP_ORGANIZATION = "Linus"


def main() -> int:
    """
    Hauptfunktion der Anwendung.
    
    Initialisiert das Qt-Framework, konfiguriert die Anwendung mit Metadaten
    und startet die Haupt-GUI. Behandelt auch die ordnungsgemäße Beendigung.
    
    Returns:
        int: Exit-Code der Anwendung (0 = Erfolg, != 0 = Fehler)
        
    Raises:
        SystemExit: Bei kritischen Initialisierungsfehlern
        
    Architecture-Notes:
        - QApplication verwaltet Event-Loop und System-Integration
        - MainWindow implementiert die gesamte GUI-Logik
        - app.exec() startet die Event-Loop (blocking call)
        
    Performance-Considerations:
        - QApplication-Initialisierung ~50-100ms
        - MainWindow-Setup ~200-500ms (abhängig von DB-Größe)
        - Memory-Footprint: ~50-80MB im Runtime
    """
    try:
        # ═══════════════════════════════════════════════════════════════════════
        # QT-ANWENDUNG INITIALISIEREN
        # ═══════════════════════════════════════════════════════════════════════
        
        # QApplication mit Kommandozeilen-Argumenten erstellen
        app = QApplication(sys.argv)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ANWENDUNGS-METADATEN KONFIGURIEREN
        # ═══════════════════════════════════════════════════════════════════════
        
        # Anwendungsname (erscheint in Taskleiste, Alt+Tab, etc.)
        app.setApplicationName(APP_NAME)
        
        # Versionsnummer (für About-Dialoge, Debugging)
        app.setApplicationVersion(APP_VERSION)
        
        # Organisation (für QSettings, Registry-Einträge)
        app.setOrganizationName(APP_ORGANIZATION)
        
        # Optional: Display-Name für bessere UX
        app.setApplicationDisplayName(f"{APP_NAME} v{APP_VERSION}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # HAUPT-GUI ERSTELLEN UND ANZEIGEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # MainWindow-Instanz erstellen (Initialisiert UI, DB, Watchlist)
        window = MainWindow()
        
        # Fenster anzeigen (non-blocking)
        window.show()
        
        # ═══════════════════════════════════════════════════════════════════════
        # EVENT-LOOP STARTEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # Qt Event-Loop starten (blocking until application exit)
        # Returns exit code when application is closed
        return app.exec()
        
    except ImportError as e:
        # Fehlende Dependencies (PySide6, etc.)
        print(f"❌ Import-Fehler: {e}")
        print("💡 Lösung: pip install -r assets/requirements.txt")
        return 1
        
    except Exception as e:
        # Unerwartete Initialisierungsfehler
        print(f"❌ Kritischer Fehler beim Anwendungsstart: {e}")
        print("💡 Prüfen Sie Dateiberechtigungen und verfügbaren Speicher.")
        return 1


if __name__ == "__main__":
    """
    Entry-Point für direkte Skript-Ausführung.
    
    Verwendet sys.exit() für ordnungsgemäße Beendigung mit korrektem Exit-Code.
    Dieser Block wird nur ausgeführt wenn das Skript direkt gestartet wird,
    nicht bei Import als Modul.
    
    Exit-Codes:
        0: Normale Beendigung
        1: Fehler bei Initialisierung
        130: Benutzer-Unterbrechung (Ctrl+C)
    """
    try:
        # Starte Anwendung und beende mit Exit-Code
        sys.exit(main())
        
    except KeyboardInterrupt:
        # Graceful handling von Ctrl+C
        print("\n⚠️ Anwendung wurde vom Benutzer unterbrochen.")
        sys.exit(130)  # Standard Unix exit code für SIGINT
        
    except SystemExit:
        # Re-raise SystemExit (normale Beendigung)
        raise
        
    except Exception as e:
        # Unbehandelte Exception im main()
        print(f"❌ Unbehandelte Exception: {e}")
        sys.exit(1)