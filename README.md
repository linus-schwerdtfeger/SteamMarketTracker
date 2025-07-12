# Community Market Item Price-Tracker

Ein Desktop-Tool zum Verfolgen von Counter Strike Skin-Preisen mit Preishistorie, Diagrammen und Preisalarmen.

## Features

- 📊 **Preishistorie**: Verfolgen Sie Preisänderungen über die Zeit
- 📈 **Interaktive Diagramme**: Visualisierung der Preisentwicklung
- 🔔 **Preisalarme**: Benachrichtigungen bei Erreichen von Zielpreisen
- 💾 **Datenexport**: CSV-Export der Preisdaten
- 🎯 **Watchlist**: Verwalten Sie Ihre favorisierten Skins

## Installation

1. Python 3.8+ installieren
2. Abhängigkeiten installieren:
   ```bash
   pip install -r assets/requirements.txt
   ```
3. Anwendung starten:
   ```bash
   python main.py
   ```

## Verwendung

1. **Skin hinzufügen**: Geben Sie den vollständigen Skin-Namen ein (z.B. "AK-47 | Redline (Field-Tested)")
2. **Preise verfolgen**: Die Anwendung ruft automatisch aktuelle Preise ab
3. **Diagramme anzeigen**: Wählen Sie einen Skin aus der Liste, um die Preishistorie zu sehen
4. **Daten exportieren**: Exportieren Sie Preisdaten als CSV-Datei

## Technische Verbesserungen

### Code-Optimierungen
- ✅ **Entfernung duplizierter Funktionen**
- ✅ **Bessere Fehlerbehandlung** mit spezifischen Exception-Typen
- ✅ **Type Hints** für bessere Code-Dokumentation
- ✅ **Konstanten** statt hardcoded Werte
- ✅ **Verbesserte String-Parsing** mit regulären Ausdrücken
- ✅ **Robuste Eingabevalidierung**
- ✅ **Bessere Benutzer-Feedback** mit aussagekräftigen Fehlermeldungen

### Performance-Verbesserungen
- 🚀 **Effizientere API-Parameter** mit `requests.get(params=...)`
- 🚀 **Optimierte String-Verarbeitung** mit regex statt mehrfacher `.replace()`
- 🚀 **Reduzierte Netzwerk-Requests** durch bessere Validierung

### Wartbarkeit
- 📝 **Umfassende Dokumentation** mit Docstrings
- 🗂️ **Klare Trennung von Verantwortlichkeiten**
- 🔧 **Konfigurierbare Konstanten**
- 🧪 **Bessere Testbarkeit** durch modularen Aufbau

## 🆕 Neue Erweiterte Features

### Multi-Chart Dashboard
- **📈 Preisverlauf**: Zeigt sowohl niedrigsten als auch Median-Preis
- **📊 Handelsvolumen**: Balkendiagramm der Liquidität über die Zeit
- **📉 Bid-Ask Spread**: Linienchart der Markt-Spreads (absolut und prozentual)

### Erweiterte Marktdaten
- **Median-Preis**: Zusätzlich zum niedrigsten Preis
- **Volumen-Tracking**: Handelsvolumen als Liquiditätsindikator  
- **Spread-Analyse**: Unterschied zwischen Kauf- und Verkaufsangeboten
- **Spread-Prozentsatz**: Relative Spread-Berechnung für bessere Vergleichbarkeit

### Verbesserte Benutzeroberfläche
- **Toggle-Option**: Wechseln zwischen einfacher und erweiterter Ansicht
- **Status-Anzeige**: Live-Updates über Datenlade-Status
- **Drei-Panel Layout**: Übersichtliche Darstellung aller Marktaspekte

### Smart Data Management
- **Automatische Schema-Migration**: Bestehende Datenbanken werden automatisch erweitert
- **Fallback-Mechanismus**: Funktioniert auch wenn nur Basisdaten verfügbar sind
- **Effiziente Speicherung**: Optimierte Datenbankstruktur mit Indizes

## Migration für bestehende Installationen

Falls Sie bereits eine ältere Version verwenden:

```bash
python migrate_db.py
```

Dieses Skript erweitert Ihre bestehende Datenbank um die neuen Spalten.

## Architektur

```
├── main.py              # Anwendungs-Einstiegspunkt
├── data/
│   ├── fetcher.py       # Steam API Integration
│   └── db.py            # SQLite Datenbank-Operations
├── ui/
│   └── main_window.py   # GUI Hauptfenster
├── plots/
│   └── chart.py         # Matplotlib Diagramme
└── assets/
    └── requirements.txt # Python-Abhängigkeiten
```
