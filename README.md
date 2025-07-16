# 🎯 CS Skin Markt Preis-Tracker v1.0
### Enhanced Auto-Update Edition

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

Ein professioneller Desktop-Tracker für Counter-Strike Skin-Preise mit **Echtzeit-Auto-Updates**, umfassender Marktanalyse und erweiterten Visualisierungen.

</div>

---

## 🚀 **Hauptfeatures v1.0**

### ⚡ **Intelligentes Auto-Update-System**
- **🔄 Kontinuierliche Überwachung**: Automatische Preisaktualisierungen in konfigurierbaren Intervallen (3-1440 Min)
- **🧵 Non-Blocking Threading**: Updates laufen im Hintergrund ohne UI-Einfrieren
- **📊 Progress-Tracking**: Live-Fortschrittsanzeige mit detailliertem Status-Feedback
- **⚠️ Smart Rate-Limiting**: Schutz vor Steam API-Limitierungen mit intelligenten Warnungen
- **🔔 Instant Alerts**: Preisalarme werden auch während Auto-Updates ausgelöst

### 📈 **Erweiterte Multi-Chart-Analyse**
- **💰 Dual-Preis-Tracking**: Niedrigster UND Median-Preis für bessere Markteinschätzung
- **📊 Volumen-Überwachung**: Handelsvolumen als Liquiditäts- und Popularitätsindikator
- **📉 Bid-Ask Spread-Analyse**: Markt-Effizienz-Metriken (absolut und prozentual)
- **🎨 Optimiertes Dark Theme**: Professionelle Drei-Panel-Visualisierung

### 🛡️ **Production-Ready Architektur**
- **🔧 Robustes Error Handling**: Umfassende Exception-Behandlung auf allen Ebenen
- **💾 Schema-Migration**: Automatische Datenbank-Updates für bestehende Installationen
- **🔒 Thread-Safe Operations**: Sichere Worker-Kommunikation mit Signal/Slot-System
- **⚡ Performance-Optimiert**: Effiziente Datenstrukturen und minimale API-Calls

---

## 📊 **Core Features**

| Feature | Beschreibung | Status |
|---------|-------------|---------|
| 🎯 **Watchlist-Management** | Hinzufügen/Entfernen von Skins mit Duplikat-Schutz | ✅ |
| 📈 **Preishistorie** | Langzeit-Tracking mit SQLite-Persistierung | ✅ |
| 📊 **Multi-Chart-Dashboard** | 3-Panel Layout: Preis, Volumen, Spread | ✅ |
| 🔔 **Preisalarme** | Benachrichtigungen bei Zielpreis-Erreichen | ✅ |
| 💾 **Datenexport** | CSV-Export mit vollständigen Marktdaten | ✅ |
| 🔄 **Auto-Updates** | Kontinuierliche Hintergrund-Überwachung | ✅ |
| 🎨 **Dark Theme** | Augenschonende Benutzeroberfläche | ✅ |
| ⌨️ **Keyboard Shortcuts** | Effiziente Bedienung (Enter, Delete, F11, Ctrl+E) | ✅ |

---

## 🛠️ **Installation**

### **Voraussetzungen**
- **Python 3.8+** (empfohlen: 3.10+)
- **Internetverbindung** für Steam Community Market API
- **~50MB freier Speicherplatz**

### **Schnell-Installation**
```bash
# 1. Repository klonen/herunterladen
git clone <repository-url>
cd cs_skin_tracker

# 2. Abhängigkeiten installieren
pip install -r assets/requirements.txt

# 3. Anwendung starten
python main.py
```

### **Alternative: Virtuelle Umgebung (empfohlen)**
```bash
# Virtuelle Umgebung erstellen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate
# Aktivieren (macOS/Linux)
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r assets/requirements.txt

# Starten
python main.py
```

---

## 🎮 **Benutzerhandbuch**

### **1. Skin zur Watchlist hinzufügen**
```
1. Vollständigen Namen eingeben: "AK-47 | Redline (Field-Tested)"
2. Enter drücken oder "Hinzufügen" klicken
3. Automatischer Download der Marktdaten
```

### **2. Auto-Update konfigurieren**
```
1. Gewünschtes Intervall einstellen (3-1440 Minuten)
2. "🔄 Auto-Update starten" klicken
3. Bei Warnungen: Intervall ggf. anpassen
4. System läuft kontinuierlich im Hintergrund
```

### **3. Preisalarme einrichten**
```json
// alerts.json erstellen/bearbeiten:
{
  "AK-47 | Redline (Field-Tested)": 25.50,
  "AWP | Dragon Lore (Factory New)": 8000.00
}
```

### **4. Daten exportieren**
```
1. Skin in Watchlist auswählen
2. Datei → Exportieren (Ctrl+E)
3. CSV-Datei mit vollständigen Marktdaten wird erstellt
```

---

## 📁 **Projektstruktur**

```
cs_skin_tracker/
├── 📄 main.py                    # Anwendungs-Einstiegspunkt
│
├── 📂 data/                      # Datenverarbeitung
│   ├── 🔌 fetcher.py            # Steam API Integration + MarketData-Klassen
│   └── 💾 db.py                 # SQLite Operationen + Schema-Management
│
├── 📂 ui/                        # Benutzeroberfläche
│   └── 🖥️ main_window.py        # Haupt-GUI + Auto-Update-System
│
├── 📂 plots/                     # Datenvisualisierung
│   └── 📊 chart.py              # Matplotlib Multi-Chart-Canvas
│
├── 📂 assets/                    # Projektressourcen
│   └── 📋 requirements.txt       # Python-Abhängigkeiten
│
├── 📄 README.md                  # Projekt-Dokumentation
├── 📄 watchlist.json            # Gespeicherte Skin-Liste (automatisch erstellt)
├── 📄 alerts.json               # Preisalarm-Konfiguration (optional)
└── 💾 skin_prices.db            # SQLite-Datenbank (automatisch erstellt)
```

---

## 🔧 **Technische Details**

### **Auto-Update-Architektur**
```python
# Worker-Thread-System für non-blocking Updates
class PriceUpdateWorker(QThread):
    """
    - Läuft in separatem Thread
    - Signal-basierte UI-Kommunikation
    - Rate-Limiting zwischen API-Calls
    - Sichere Thread-Beendigung
    """
```

### **Marktdaten-Schema**
```sql
-- Erweiterte Datenbank-Struktur (automatisch migriert)
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY,
    skin TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    lowest_price REAL NOT NULL,      -- Niedrigster Marktpreis
    median_price REAL NOT NULL,      -- Median-Preis für bessere Analyse
    volume INTEGER NOT NULL,         -- Handelsvolumen (Liquidität)
    spread_absolute REAL NOT NULL,   -- Absoluter Bid-Ask Spread
    spread_percentage REAL NOT NULL  -- Relativer Spread in %
);
```

### **API-Integration**
```python
# Steam Community Market API mit robustem Error Handling
STEAM_API_BASE_URL = "https://steamcommunity.com/market/priceoverview/"
CSGO_APP_ID = "730"
EUR_CURRENCY_ID = "3"
MIN_REQUEST_DELAY = 2.0  # Rate-Limiting

@dataclass
class MarketData:
    lowest_price: float
    median_price: float
    volume: int
    spread_absolute: float
    spread_percentage: float
```

---

## ⚙️ **Konfiguration**

### **Performance-Optimierung**
```python
# In main_window.py anpassbar:
MIN_REQUEST_DELAY = 2.0        # Sekunden zwischen API-Requests
MAX_CONCURRENT_REQUESTS = 1    # Keine parallelen Requests (Steam-konform)
```

### **UI-Anpassungen**
```python
# Farb-Schema in main_window.py:
BACKGROUND_COLOR = "rgb(45, 45, 45)"    # Haupthintergrund
SUCCESS_COLOR = "#28a745"               # Erfolg-Meldungen
ERROR_COLOR = "#dc3545"                 # Fehler-Meldungen
WARNING_COLOR = "#fd7e14"               # Warnungen
```

---

## 🚨 **Fehlerbehebung**

### **Häufige Probleme**

| Problem | Lösung |
|---------|--------|
| ❌ **"ImportError: pyqtSignal"** | Verwenden Sie `Signal` statt `pyqtSignal` in PySide6 |
| ❌ **"Keine Daten verfügbar"** | Prüfen Sie Internetverbindung + exakten Skin-Namen |
| ❌ **"UI eingefroren"** | Auto-Update verwenden statt manueller Massen-Updates |
| ❌ **"API-Limit erreicht"** | Erhöhen Sie das Update-Intervall (min. 5 Min empfohlen) |
| ❌ **"Chart zeigt nichts"** | Mindestens 2 Datenpunkte erforderlich für Visualisierung |

### **Debug-Modus**
```bash
# Verbose Logging aktivieren
python main.py --debug
```

### **Datenbank-Reset**
```bash
# Bei Struktur-Problemen
rm skin_prices.db
python main.py  # Automatische Neuinitialisierung
```

---

## 🔄 **Migration von v1.x**

### **Automatische Migration**
```bash
# Bestehende Installationen werden automatisch aktualisiert
python main.py  # Führt Schema-Migration durch
```

### **Manuelle Migration (falls erforderlich)**
```sql
-- Erweitere bestehende Tabelle
ALTER TABLE market_data ADD COLUMN median_price REAL DEFAULT 0.0;
ALTER TABLE market_data ADD COLUMN volume INTEGER DEFAULT 0;
ALTER TABLE market_data ADD COLUMN spread_absolute REAL DEFAULT 0.0;
ALTER TABLE market_data ADD COLUMN spread_percentage REAL DEFAULT 0.0;
```

---

## 📊 **Performance-Metriken**

| Metrik | Wert | Beschreibung |
|--------|------|-------------|
| **Startup-Zeit** | ~2-3s | Datenbank-Init + UI-Rendering |
| **API-Response** | ~1-2s | Steam Market API (abhängig von Netzwerk) |
| **Memory Usage** | ~50-80MB | Inklusive Chart-Caching |
| **Database Size** | ~1MB/1000 | Datenpunkte (komprimiert) |
| **Update-Zyklus** | 5-30s | Abhängig von Skin-Anzahl |

---

## 🤝 **Entwicklung & Beitrag**

### **Code-Style**
- **Type Hints**: Vollständige Typisierung für bessere Wartbarkeit
- **Docstrings**: Umfassende Dokumentation aller Methoden
- **Error Handling**: Spezifische Exception-Behandlung
- **Threading**: Signal/Slot-basierte Worker-Kommunikation

### **Testing**
```bash
# Unit Tests (falls implementiert)
python -m pytest tests/

# Manuelle Tests
python main.py --test-mode
```

### **Erweiterungen**
- 📈 **Weitere Chart-Typen**: Candlestick, Bollinger Bands
- 🔔 **Discord/Telegram Bot**: Externe Benachrichtigungen
- 📱 **Mobile App**: React Native Frontend
- 🤖 **ML-Predictions**: Preis-Vorhersage mit TensorFlow

---

## 📜 **Lizenz & Haftung**

```
MIT License - Freie Nutzung für private und kommerzielle Zwecke

⚠️ HAFTUNGSAUSSCHUSS:
Diese Software dient nur zu Informationszwecken. 
Marktpreise können volatil sein. Keine Anlageberatung.
Steam API-Nutzung unterliegt den Steam-Nutzungsbedingungen.
```

---

## 🔗 **Links & Ressourcen**

- 🎮 **Steam Community Market**: [steamcommunity.com/market](https://steamcommunity.com/market)
- 📚 **PySide6 Dokumentation**: [doc.qt.io/qtforpython](https://doc.qt.io/qtforpython)
- 📊 **Matplotlib Galerie**: [matplotlib.org/stable/gallery](https://matplotlib.org/stable/gallery)
- 🐍 **Python Best Practices**: [python.org/dev/peps](https://python.org/dev/peps)

---

<div align="center">

**Entwickelt mit ❤️ für die CS-Community**

*Für Fragen, Bugs oder Feature-Requests: GitHub Issues verwenden*

</div>
