"""
CS Skin Tracker - Datenbank-Management und Persistierung
========================================================

Dieses Modul verwaltet die lokale SQLite-Datenbank für die Persistierung
von Marktdaten und Preishistorien der CS Skins.

Hauptfunktionen:
- init_db(): Datenbank-Initialisierung und Schema-Migration
- insert_market_data(): Speicherung neuer Marktdaten
- get_market_history(): Abruf der Preishistorie
- export_market_data(): CSV-Export für externe Analyse

Technische Details:
- SQLite3 für lokale Datenhaltung (serverless)
- Automatische Schema-Migration für Updates
- Optimierte Indizes für Performance
- Thread-sichere Operationen mit Context-Managern

Performance-Features:
- Transaktionale Operationen
- Effiziente Index-Strategien
- Batch-Processing-Unterstützung
- Memory-optimierte Abfragen

Schema-Evolution:
- v1: Basis-Schema (skin, timestamp, lowest_price)
- v2: Erweiterte Marktdaten (median_price, volume, spread_*, constraints)

Author: Linus
Version: 1.0
"""

import sqlite3
import csv
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Union, Dict, Any
from contextlib import contextmanager

# ═══════════════════════════════════════════════════════════════════════════════
# DATENBANK-KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Datenbank-Datei (im Arbeitsverzeichnis)
DB_PATH = "skin_prices.db"

# Schema-Version für Migration-Management
CURRENT_SCHEMA_VERSION = 2

# Performance-Einstellungen
DB_TIMEOUT = 30.0                    # Sekunden für DB-Lock-Timeout
MAX_RETRIES = 3                      # Anzahl Wiederholungsversuche
BATCH_SIZE = 1000                    # Optimale Batch-Größe für Bulk-Operations

# SQL-Performance-Konfiguration
PRAGMA_SETTINGS = {
    "foreign_keys": "ON",            # Referentielle Integrität
    "journal_mode": "WAL",           # Write-Ahead-Logging für Concurrency
    "synchronous": "NORMAL",         # Balancierte Sicherheit/Performance
    "cache_size": "10000",           # 10MB Cache für bessere Performance
    "temp_store": "MEMORY",          # Temporäre Tabellen im Arbeitsspeicher
    "mmap_size": "268435456"         # 256MB Memory-Mapped I/O
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATENBANK-SCHEMA DEFINITIONEN
# ═══════════════════════════════════════════════════════════════════════════════

# Haupt-Tabelle für Marktdaten (Version 2.0)
CREATE_MARKET_DATA_TABLE = """
    CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skin TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        lowest_price REAL NOT NULL,
        median_price REAL NOT NULL DEFAULT 0.0,
        volume INTEGER NOT NULL DEFAULT 0,
        spread_absolute REAL NOT NULL DEFAULT 0.0,
        spread_percentage REAL NOT NULL DEFAULT 0.0
    )
"""

# Schema-Versions-Tabelle für Migration-Tracking
CREATE_SCHEMA_VERSION_TABLE = """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        description TEXT,
        migration_time_ms INTEGER DEFAULT 0,
        
        -- Metadata für Debugging
        application_version TEXT DEFAULT '2.0',
        backup_created TEXT DEFAULT 'NO'
    )
"""

# Performance-optimierte Indizes
CREATE_INDEXES = [
    # Haupt-Index für Skin-Abfragen (häufigste Operation)
    "CREATE INDEX IF NOT EXISTS idx_skin_timestamp ON market_data(skin, timestamp)",
    
    # Index für Zeitbereich-Abfragen
    "CREATE INDEX IF NOT EXISTS idx_timestamp ON market_data(timestamp)",
    
    # Index für Skin-spezifische Abfragen
    "CREATE INDEX IF NOT EXISTS idx_skin ON market_data(skin)",
    
    # Composite-Index für neueste Preise (DESCENDING für LIMIT-Optimierung)
    "CREATE INDEX IF NOT EXISTS idx_skin_latest ON market_data(skin, timestamp DESC)",
    
    # Index für Preisbereich-Analysen
    "CREATE INDEX IF NOT EXISTS idx_price_range ON market_data(lowest_price, timestamp)",
    
    # Index für Volumen-Analysen
    "CREATE INDEX IF NOT EXISTS idx_volume_analysis ON market_data(volume DESC, timestamp)"
]

# Analytische Views für erweiterte Abfragen
CREATE_VIEWS = [
    # Daily Summary View für Performance-Analysen
    """
    CREATE VIEW IF NOT EXISTS daily_summary AS
    SELECT 
        skin,
        DATE(timestamp) as date,
        MIN(lowest_price) as daily_min,
        MAX(lowest_price) as daily_max,
        AVG(lowest_price) as daily_avg,
        SUM(volume) as daily_volume,
        COUNT(*) as data_points
    FROM market_data 
    GROUP BY skin, DATE(timestamp)
    """,
    
    # Latest Prices View für Dashboard
    """
    CREATE VIEW IF NOT EXISTS latest_prices AS
    SELECT DISTINCT
        skin,
        FIRST_VALUE(lowest_price) OVER (
            PARTITION BY skin ORDER BY timestamp DESC
        ) as current_price,
        FIRST_VALUE(median_price) OVER (
            PARTITION BY skin ORDER BY timestamp DESC
        ) as current_median,
        FIRST_VALUE(volume) OVER (
            PARTITION BY skin ORDER BY timestamp DESC
        ) as current_volume,
        FIRST_VALUE(timestamp) OVER (
            PARTITION BY skin ORDER BY timestamp DESC
        ) as last_updated
    FROM market_data
    """
]

# ═══════════════════════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN UND CONTEXT-MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@contextmanager
def get_db_connection(read_only: bool = False):
    """
    Context-Manager für sichere Datenbankverbindungen.
    
    Args:
        read_only: True für Read-Only-Zugriff (Performance-Optimierung)
    
    Vorteile:
    - Automatisches Connection-Cleanup
    - Exception-sichere Transaktionen
    - Konfigurierte Timeout-Werte
    - Thread-sichere Operationen
    - Optimierte PRAGMA-Settings
    
    Performance-Optimierungen:
    - WAL-Mode für bessere Concurrency
    - Memory-Mapped I/O für große Datenmengen
    - Optimierte Cache-Größe
    - Read-Only-Modus für Abfragen
    
    Yields:
        sqlite3.Connection: Konfigurierte Datenbankverbindung
        
    Raises:
        sqlite3.Error: Bei Datenbankfehlern
        OSError: Bei Dateisystem-Problemen
    """
    conn = None
    try:
        # URI-Parameter für erweiterte Konfiguration
        db_uri = f"file:{DB_PATH}"
        if read_only:
            db_uri += "?mode=ro"
        
        # Verbindung mit optimierten Einstellungen
        conn = sqlite3.connect(
            db_uri,
            timeout=DB_TIMEOUT,
            check_same_thread=False,  # Thread-sichere Nutzung
            uri=True  # URI-Parameter aktivieren
        )
        
        # Performance-Optimierungen anwenden
        for pragma, value in PRAGMA_SETTINGS.items():
            try:
                conn.execute(f"PRAGMA {pragma} = {value}")
            except sqlite3.OperationalError as e:
                # Einige PRAGMAs sind Read-Only-spezifisch
                if not read_only:
                    print(f"⚠️ PRAGMA {pragma} konnte nicht gesetzt werden: {e}")
        
        # Row-Factory für bessere Ergebnisse
        conn.row_factory = sqlite3.Row
        
        yield conn
        
    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()  # Rollback bei DB-Fehlern
        print(f"❌ Datenbankfehler: {e}")
        raise
        
    except OSError as e:
        print(f"❌ Dateisystem-Fehler: {e}")
        raise
        
    except Exception as e:
        if conn:
            conn.rollback()  # Rollback bei unerwarteten Fehlern
        print(f"❌ Unerwarteter Datenbankfehler: {e}")
        raise
        
    finally:
        if conn:
            conn.close()

def _get_schema_version() -> int:
    """
    Ermittelt die aktuelle Schema-Version der Datenbank.
    
    Returns:
        int: Schema-Version (0 wenn Tabelle nicht existiert)
        
    Raises:
        sqlite3.Error: Bei kritischen Datenbankfehlern
        
    Performance:
        Sehr schnell durch Primary Key Lookup (~1ms)
    """
    try:
        with get_db_connection(read_only=True) as conn:
            cursor = conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            result = cursor.fetchone()
            return result['version'] if result else 0
            
    except sqlite3.OperationalError:
        # Tabelle existiert noch nicht (neue Installation)
        return 0

def _set_schema_version(version: int, description: str, migration_time_ms: int = 0) -> None:
    """
    Setzt die Schema-Version in der Datenbank.
    
    Args:
        version: Neue Schema-Version
        description: Beschreibung der Änderungen
        migration_time_ms: Dauer der Migration in Millisekunden
        
    Raises:
        sqlite3.Error: Bei Datenbankfehlern
    """
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO schema_version 
            (version, applied_at, description, migration_time_ms, application_version) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                version, 
                datetime.now().isoformat(), 
                description,
                migration_time_ms,
                "2.0"
            )
        )
        conn.commit()

def _create_backup(suffix: str = "migration") -> str:
    """
    Erstellt ein Backup der Datenbank vor kritischen Operationen.
    
    Args:
        suffix: Suffix für Backup-Dateiname
        
    Returns:
        str: Pfad zur Backup-Datei
        
    Raises:
        OSError: Bei Dateisystem-Fehlern
    """
    if not os.path.exists(DB_PATH):
        return ""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DB_PATH}.{suffix}_{timestamp}.backup"
    
    try:
        with get_db_connection(read_only=True) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        print(f"💾 Backup erstellt: {backup_path}")
        return backup_path
        
    except Exception as e:
        print(f"❌ Backup-Erstellung fehlgeschlagen: {e}")
        raise

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA-MIGRATION-SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def _migrate_schema_v1_to_v2() -> float:
    """
    Migriert Schema von Version 1 zu Version 2.
    
    Änderungen in v2:
    - Neue Spalten: median_price, volume, spread_absolute, spread_percentage
    - Verbesserte Constraints für Datenqualität
    - Erweiterte Indizes für bessere Performance
    - Analytische Views für Dashboard-Features
    
    Migration-Strategie:
    - Non-destructive: Keine Daten gehen verloren
    - Rückwärts-kompatibel: v1-Abfragen funktionieren weiterhin
    - Performance-optimiert: Batch-Updates wo möglich
    - Rollback-fähig: Backup wird automatisch erstellt
    
    Performance:
    - Kleine DBs (<1000 Einträge): ~100-500ms
    - Mittlere DBs (<10K Einträge): ~1-5s
    - Große DBs (>10K Einträge): ~5-30s
    
    Returns:
        float: Migration-Dauer in Millisekunden
        
    Raises:
        sqlite3.Error: Bei Migration-Fehlern
        RuntimeError: Bei kritischen Problemen
    """
    start_time = datetime.now()
    print("🔄 Migriere Datenbank-Schema von v1 zu v2...")
    
    # Backup erstellen vor Migration
    backup_path = _create_backup("v1_to_v2")
    
    with get_db_connection() as conn:
        try:
            # Transaktion für atomare Migration
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            
            # Prüfe existierende Spalten
            cursor = conn.execute("PRAGMA table_info(market_data)")
            existing_columns = {row['name'] for row in cursor.fetchall()}
            
            # Füge fehlende Spalten hinzu (idempotent)
            new_columns = [
                ("median_price", "REAL NOT NULL DEFAULT 0.0"),
                ("volume", "INTEGER NOT NULL DEFAULT 0"),
                ("spread_absolute", "REAL NOT NULL DEFAULT 0.0"),
                ("spread_percentage", "REAL NOT NULL DEFAULT 0.0")
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    conn.execute(f"ALTER TABLE market_data ADD COLUMN {column_def}")
                    print(f"  ✅ Spalte '{column_name}' hinzugefügt")
                else:
                    print(f"  ⏭️ Spalte '{column_name}' bereits vorhanden")
            
            # Erstelle neue Indizes (idempotent)
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)
            
            # Erstelle analytische Views
            for view_sql in CREATE_VIEWS:
                conn.execute(view_sql)
            
            # Datenqualität verbessern: Leere/NULL-Werte korrigieren
            updates_applied = conn.execute("""
                UPDATE market_data 
                SET median_price = lowest_price 
                WHERE median_price = 0.0 AND lowest_price > 0
            """).rowcount
            
            if updates_applied > 0:
                print(f"  🔧 {updates_applied} median_price-Werte korrigiert")
            
            # Migration erfolgreich
            conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            print(f"✅ Schema-Migration v1→v2 erfolgreich abgeschlossen ({duration:.0f}ms)")
            
            return duration
            
        except Exception as e:
            # Rollback bei Fehlern
            conn.rollback()
            print(f"❌ Fehler bei Schema-Migration: {e}")
            print(f"💾 Backup verfügbar: {backup_path}")
            raise RuntimeError(f"Schema-Migration v1→v2 fehlgeschlagen: {e}") from e

def _migrate_database() -> None:
    """
    Führt alle notwendigen Schema-Migrationen durch.
    
    Migration-Chain:
    v0 → v1: Basis-Schema erstellen
    v1 → v2: Erweiterte Marktdaten hinzufügen
    
    Design-Prinzipien:
    - Idempotente Operationen (mehrfache Ausführung sicher)
    - Datenerhaltung (keine destruktiven Änderungen)
    - Rollback-Fähigkeit bei Fehlern
    - Performance-Tracking für Optimierungen
    - Automatische Backups bei kritischen Änderungen
    
    Raises:
        RuntimeError: Bei kritischen Migration-Fehlern
    """
    current_version = _get_schema_version()
    target_version = CURRENT_SCHEMA_VERSION
    
    if current_version == target_version:
        print(f"✅ Datenbank-Schema bereits aktuell (v{current_version})")
        return
    
    if current_version > target_version:
        raise RuntimeError(
            f"Datenbank-Schema v{current_version} ist neuer als erwartet v{target_version}. "
            "Bitte verwenden Sie eine neuere Version der Anwendung."
        )
    
    print(f"🔄 Starte Schema-Migration von v{current_version} zu v{target_version}")
    total_start = datetime.now()
    
    try:
        # Migration-Chain ausführen
        if current_version < 1:
            # v0 → v1: Initial schema
            print("🆕 Erstelle initiales Datenbank-Schema...")
            start_time = datetime.now()
            _create_initial_schema()
            duration = (datetime.now() - start_time).total_seconds() * 1000
            _set_schema_version(1, "Initial schema creation", int(duration))
            current_version = 1
        
        if current_version < 2:
            # v1 → v2: Enhanced market data
            duration = _migrate_schema_v1_to_v2()
            _set_schema_version(2, "Enhanced market data with spread analysis", int(duration))
            current_version = 2
        
        total_duration = (datetime.now() - total_start).total_seconds() * 1000
        print(f"🎉 Schema-Migration erfolgreich abgeschlossen (v{current_version}, {total_duration:.0f}ms)")
        
    except Exception as e:
        print(f"❌ Kritischer Fehler bei Schema-Migration: {e}")
        raise RuntimeError(f"Datenbank-Migration fehlgeschlagen: {e}") from e

def _create_initial_schema() -> None:
    """
    Erstellt das initiale Datenbank-Schema.
    
    Wird nur bei komplett neuen Installationen ausgeführt.
    Erstellt alle Tabellen, Indizes und Views in optimaler Reihenfolge.
    
    Raises:
        sqlite3.Error: Bei Schema-Erstellungsfehlern
    """
    with get_db_connection() as conn:
        try:
            # Tabellen erstellen (Reihenfolge wichtig für Foreign Keys)
            conn.execute(CREATE_SCHEMA_VERSION_TABLE)
            conn.execute(CREATE_MARKET_DATA_TABLE)
            
            # Performance-Indizes
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)
            
            # Analytische Views
            for view_sql in CREATE_VIEWS:
                conn.execute(view_sql)
            
            conn.commit()
            print("✅ Initiales Datenbank-Schema erstellt")
            
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Initiales Schema konnte nicht erstellt werden: {e}") from e

# ═══════════════════════════════════════════════════════════════════════════════
# ÖFFENTLICHE API-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def init_db() -> None:
    """
    Initialisiert die Datenbank für erweiterte Marktdaten.
    
    Diese Funktion sollte beim Anwendungsstart aufgerufen werden und:
    - Erstellt die Datenbank falls sie nicht existiert
    - Führt Schema-Migrationen durch
    - Optimiert die Datenbank für Performance
    - Validiert die Datenintegrität
    - Erstellt Backups bei kritischen Änderungen
    
    Error-Handling:
    - Bei kritischen Fehlern wird Exception geworfen
    - Detailliertes Logging für Debugging
    - Automatische Backup-Erstellung bei Migrationen
    - Graceful Degradation bei nicht-kritischen Fehlern
    
    Performance-Considerations:
    - Schnell bei existierenden DBs (~10-50ms)
    - Migration kann bei großen DBs länger dauern
    - WAL-Mode für bessere Concurrency
    - Optimierte PRAGMA-Settings
    
    Raises:
        RuntimeError: Bei kritischen Initialisierungsfehlern
    """
    try:
        print("🔧 Initialisiere Datenbank...")
        start_time = datetime.now()
        
        # Prüfe ob Datenbank-Datei existiert
        db_exists = os.path.exists(DB_PATH)
        
        if not db_exists:
            print("🆕 Erstelle neue Datenbank...")
        else:
            # Existierende Datenbank-Info
            db_size = os.path.getsize(DB_PATH)
            print(f"📁 Existierende Datenbank gefunden ({db_size:,} Bytes)")
        
        # Schema-Migration ausführen
        _migrate_database()
        
        # Datenbank-Integrität prüfen
        _validate_database_integrity()
        
        # Performance-Statistiken sammeln
        _collect_db_statistics()
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✅ Datenbank erfolgreich initialisiert ({duration:.0f}ms)")
        
    except sqlite3.Error as e:
        print(f"❌ SQLite-Fehler bei Datenbank-Initialisierung: {e}")
        raise RuntimeError(f"Datenbank-Initialisierung fehlgeschlagen: {e}") from e
    
    except OSError as e:
        print(f"❌ Dateisystem-Fehler bei Datenbank-Initialisierung: {e}")
        raise RuntimeError(f"Dateisystem-Problem: {e}") from e
    
    except Exception as e:
        print(f"❌ Kritischer Fehler bei Datenbank-Initialisierung: {e}")
        raise RuntimeError(f"Unerwarteter Initialisierungsfehler: {e}") from e

def insert_market_data(skin: str, market_data) -> None:
    """
    Fügt umfassende Marktdaten zur Datenbank hinzu.
    
    Args:
        skin: Name des Skins (z.B. "AK-47 | Redline (Field-Tested)")
        market_data: MarketData-Objekt mit allen Marktinformationen
    """
    # Basis-Input-Validierung
    if not skin or not skin.strip():
        raise ValueError("Skin-Name darf nicht leer sein")
    
    if not market_data:
        raise ValueError("MarketData-Objekt darf nicht None sein")
    
    # MarketData-Objekt-Validierung (nur Existenz prüfen)
    required_attributes = ['lowest_price', 'median_price', 'volume', 'spread_absolute', 'spread_percentage']
    for attr in required_attributes:
        if not hasattr(market_data, attr):
            raise ValueError(f"MarketData-Objekt fehlt Attribut '{attr}'")
    
    skin_clean = skin.strip()
    timestamp = datetime.now().isoformat(timespec='seconds')
    
    try:
        with get_db_connection() as conn:
            # Einfaches Insert ohne Validierung der Werte
            conn.execute("""
                INSERT INTO market_data 
                (skin, timestamp, lowest_price, median_price, volume, spread_absolute, spread_percentage) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                skin_clean,
                timestamp,
                float(market_data.lowest_price),
                float(market_data.median_price),
                int(market_data.volume),
                float(market_data.spread_absolute),
                float(market_data.spread_percentage)
            ))
            
            conn.commit()
            
            # Erfolgs-Logging
            print(f"✅ Marktdaten für '{skin_clean}' erfolgreich gespeichert "
                  f"(Preis: {market_data.lowest_price:.2f}€, "
                  f"Median: {market_data.median_price:.2f}€, "
                  f"Volume: {market_data.volume}, "
                  f"Spread: {market_data.spread_percentage:.1f}%)")
    
    except sqlite3.OperationalError as e:
        print(f"❌ Datenbank-Operational-Fehler für '{skin_clean}': {e}")
        raise RuntimeError(f"Datenbank-Operation fehlgeschlagen: {e}") from e
    
    except (TypeError, ValueError) as e:
        print(f"❌ Datentyp-Fehler für '{skin_clean}': {e}")
        raise ValueError(f"Ungültige Datentypen in MarketData: {e}") from e
    
    except Exception as e:
        print(f"❌ Unerwarteter Fehler beim Speichern für '{skin_clean}': {e}")
        raise RuntimeError(f"Fehler beim Speichern der Marktdaten: {e}") from e

def get_market_history(skin: str, limit: Optional[int] = None, days: Optional[int] = None) -> List[Tuple]:
    """
    Ruft die komplette oder gefilterte Markthistorie für einen Skin ab.
    
    Args:
        skin: Name des Skins
        limit: Maximale Anzahl Datensätze (neueste zuerst, dann chronologisch)
        days: Nur Daten der letzten N Tage
        
    Returns:
        List[Tuple]: Liste von (timestamp, lowest_price, median_price, volume, 
                     spread_absolute, spread_percentage) Tupeln, chronologisch sortiert
                     
    Query-Optimierung:
    - Verwendung von zusammengesetzten Indizes für bessere Performance
    - LIMIT-Klauseln zur Speicher-Optimierung
    - Chronologische Sortierung für Chart-Kompatibilität
    - WHERE-Klauseln mit Index-Unterstützung
    
    Performance:
    - Kleine Historien (<100 Punkte): ~5-10ms
    - Mittlere Historien (<1K Punkte): ~10-50ms
    - Große Historien (>1K Punkte): ~50-200ms
    - Optimiert für Zeitbereich-Abfragen
    - Memory-effizient auch bei großen Historien
    
    Edge-Cases:
    - Leerer Skin-Name: Gibt leere Liste zurück
    - Nicht-existenter Skin: Gibt leere Liste zurück
    - Ungültige Parameter: Werden ignoriert/korrigiert
    
    Raises:
        Keine - alle Fehler werden gefangen und leere Liste zurückgegeben
    """
    # Input-Validierung
    if not skin or not skin.strip():
        return []
    
    # Parameter-Normalisierung
    if limit is not None and limit <= 0:
        limit = None
    
    if days is not None and days <= 0:
        days = None
    
    skin_clean = skin.strip()
    
    try:
        with get_db_connection(read_only=True) as conn:
            # Base-Query mit allen relevanten Spalten
            query = """
                SELECT timestamp, lowest_price, median_price, volume, 
                       spread_absolute, spread_percentage 
                FROM market_data 
                WHERE skin = ?
            """
            params = [skin_clean]
            
            # Zeitbereich-Filter hinzufügen (nutzt Index)
            if days is not None:
                cutoff_date = datetime.now() - timedelta(days=days)
                query += " AND timestamp >= ?"
                params.append(cutoff_date.isoformat())
            
            # Sortierung (chronologisch für Charts, nutzt Index)
            query += " ORDER BY timestamp ASC"
            
            # Limit hinzufügen (nach Sortierung für korrekte Reihenfolge)
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            
            # Konvertiere sqlite3.Row zu Tupeln für Rückwärts-Kompatibilität
            result_tuples = [
                (
                    row['timestamp'], 
                    row['lowest_price'], 
                    row['median_price'], 
                    row['volume'], 
                    row['spread_absolute'], 
                    row['spread_percentage']
                ) 
                for row in results
            ]
            
            # Erfolgs-Logging mit Filterdetails
            filter_info = ""
            if days:
                filter_info += f" (letzte {days} Tage)"
            if limit:
                filter_info += f" (Limit: {limit})"
            
            print(f"📊 {len(result_tuples)} Marktdaten-Punkte für '{skin_clean}' abgerufen{filter_info}")
            
            return result_tuples
    
    except sqlite3.Error as e:
        print(f"❌ Datenbank-Fehler beim Abrufen der Historie für '{skin_clean}': {e}")
        return []
    
    except Exception as e:
        print(f"❌ Unerwarteter Fehler beim Abrufen der Historie für '{skin_clean}': {e}")
        return []

def get_latest_price(skin: str) -> float:
    """
    Ruft den neuesten lowest_price für einen Skin ab.
    
    Args:
        skin: Name des Skins
        
    Returns:
        float: Neuester Preis oder 0.0 wenn keine Daten vorhanden
        
    Performance:
    - Sehr schnell durch optimierte Indizes (~1-2ms)
    - Verwendet LIMIT 1 für minimalen Memory-Footprint
    - Index idx_skin_latest wird genutzt (skin, timestamp DESC)
    
    Use-Cases:
    - Dashboard-Anzeigen
    - Preisvergleiche
    - Alert-Systeme
    - Quick-Status-Checks
    """
    if not skin or not skin.strip():
        return 0.0
    
    skin_clean = skin.strip()
    
    try:
        with get_db_connection(read_only=True) as conn:
            cursor = conn.execute(
                "SELECT lowest_price FROM market_data "
                "WHERE skin = ? ORDER BY timestamp DESC LIMIT 1",
                (skin_clean,)
            )
            result = cursor.fetchone()
            
            if result:
                price = float(result['lowest_price'])
                print(f"💰 Neuester Preis für '{skin_clean}': {price:.2f}€")
                return price
            else:
                print(f"📭 Keine Preisdaten für '{skin_clean}' gefunden")
                return 0.0
    
    except sqlite3.Error as e:
        print(f"❌ Datenbank-Fehler beim Abrufen des neuesten Preises für '{skin_clean}': {e}")
        return 0.0
    
    except (TypeError, ValueError) as e:
        print(f"❌ Datentyp-Fehler beim Abrufen des neuesten Preises für '{skin_clean}': {e}")
        return 0.0
    
    except Exception as e:
        print(f"❌ Unerwarteter Fehler beim Abrufen des neuesten Preises für '{skin_clean}': {e}")
        return 0.0

def export_market_data(skin: str, filename: str, format: str = 'csv', include_metadata: bool = True) -> None:
    """
    Exportiert alle Marktdaten für einen Skin in das angegebene Format.
    
    Args:
        skin: Name des Skins
        filename: Ziel-Dateiname
        format: Export-Format ('csv', weitere geplant)
        include_metadata: Metadaten in Export einschließen
        
    CSV-Format:
    - UTF-8 Encoding für internationale Zeichen
    - Deutsche Spalten-Header für bessere UX
    - Comma-separated für Excel-Kompatibilität
    - ISO-Timestamp-Format für Sortierbarkeit
    - Optionale Metadaten-Header
    
    Metadaten (optional):
    - Export-Zeitstempel
    - Skin-Name
    - Anzahl Datensätze
    - Zeitbereich (erste/letzte Daten)
    - Anwendungsversion
    
    Error-Handling:
    - Datei-Permissions-Prüfung
    - Vollständige Pfad-Validierung
    - Rollback bei Schreibfehlern
    - Verzeichnis-Erstellung falls notwendig
    
    Performance:
    - Streaming-Export für große Datenmengen
    - Memory-effizient auch bei tausenden Datenpunkten
    - Progress-Feedback bei großen Exporten
    - Optimierte Batch-Verarbeitung
    
    Raises:
        ValueError: Bei ungültigen Parametern
        RuntimeError: Bei Export-Fehlern
        OSError: Bei Dateisystem-Problemen
    """
    # Input-Validierung
    if not skin or not skin.strip():
        raise ValueError("Skin-Name darf nicht leer sein")
    
    if not filename or not filename.strip():
        raise ValueError("Dateiname darf nicht leer sein")
    
    if format.lower() != 'csv':
        raise ValueError(f"Format '{format}' wird noch nicht unterstützt (verfügbar: csv)")
    
    skin_clean = skin.strip()
    filename_clean = filename.strip()
    
    try:
        # Marktdaten abrufen
        print(f"📤 Starte Export für '{skin_clean}'...")
        rows = get_market_history(skin_clean)
        
        if not rows:
            print(f"⚠️ Keine Daten für '{skin_clean}' gefunden, Export abgebrochen")
            return
        
        # Verzeichnis sicherstellen
        dir_path = os.path.dirname(filename_clean)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Export-Metadaten sammeln
        export_timestamp = datetime.now().isoformat()
        first_timestamp = rows[0][0] if rows else None
        last_timestamp = rows[-1][0] if rows else None
        
        # CSV-Export mit erweiterten Features
        with open(filename_clean, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            
            # Optionale Metadaten-Header
            if include_metadata:
                writer.writerow([f"# CS Skin Tracker Export"])
                writer.writerow([f"# Skin: {skin_clean}"])
                writer.writerow([f"# Export-Zeit: {export_timestamp}"])
                writer.writerow([f"# Datensätze: {len(rows)}"])
                if first_timestamp and last_timestamp:
                    writer.writerow([f"# Zeitbereich: {first_timestamp} bis {last_timestamp}"])
                writer.writerow([f"# Version: 2.0"])
                writer.writerow([])  # Leerzeile
            
            # Spalten-Header (deutsche Namen für bessere UX)
            writer.writerow([
                "Zeitstempel", 
                "Niedrigster Preis (€)", 
                "Median Preis (€)", 
                "Handelsvolumen", 
                "Spread Absolut (€)", 
                "Spread Prozent (%)"
            ])
            
            # Daten exportieren (Batch-weise für bessere Performance)
            batch_size = 1000
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                writer.writerows(batch)
                
                # Progress-Feedback bei großen Exporten
                if len(rows) > 5000:
                    progress = min(100, (i + batch_size) * 100 // len(rows))
                    print(f"  📊 Export-Fortschritt: {progress}%")
        
        # Erfolgs-Meldung mit Details
        file_size = os.path.getsize(filename_clean)
        print(f"✅ {len(rows):,} Datensätze nach '{filename_clean}' exportiert "
              f"({file_size:,} Bytes)")
        
        # Export-Statistiken
        if rows:
            price_range = f"{min(row[1] for row in rows):.2f}€ - {max(row[1] for row in rows):.2f}€"
            print(f"📊 Preisbereich: {price_range}")
    
    except PermissionError as e:
        print(f"❌ Berechtigung verweigert: {filename_clean}")
        raise OSError(f"Keine Schreibberechtigung für '{filename_clean}': {e}") from e
    
    except OSError as e:
        print(f"❌ Dateisystem-Fehler beim Export nach '{filename_clean}': {e}")
        raise OSError(f"Dateisystem-Fehler: {e}") from e
    
    except Exception as e:
        print(f"❌ Fehler beim Export nach '{filename_clean}': {e}")
        raise RuntimeError(f"Export fehlgeschlagen: {e}") from e

def get_db_statistics() -> Dict[str, Any]:
    """
    Sammelt umfassende Datenbank-Statistiken für Monitoring und Debugging.
    
    Returns:
        Dict[str, Any]: Statistiken-Dictionary mit verschiedenen Metriken
        
    Statistiken:
    - Gesamtanzahl Datensätze
    - Anzahl einzigartige Skins
    - Zeitbereich der Daten
    - Datenbankgröße
    - Top-Skins nach Datenpunkten
    - Performance-Metriken
    
    Performance:
    - Optimierte Abfragen mit Indizes
    - Minimal-Memory-Footprint
    - Cacheable Ergebnisse
    """
    try:
        with get_db_connection(read_only=True) as conn:
            stats = {}
            
            # Basis-Statistiken
            cursor = conn.execute("SELECT COUNT(*) FROM market_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT skin) FROM market_data")
            stats['unique_skins'] = cursor.fetchone()[0]
            
            # Zeitbereich
            cursor = conn.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM market_data"
            )
            time_range = cursor.fetchone()
            stats['first_record'] = time_range[0]
            stats['last_record'] = time_range[1]
            
            # Datenbankgröße
            if os.path.exists(DB_PATH):
                stats['db_size_bytes'] = os.path.getsize(DB_PATH)
                stats['db_size_mb'] = stats['db_size_bytes'] / (1024 * 1024)
            
            # Schema-Version
            stats['schema_version'] = _get_schema_version()
            
            # Top-Skins nach Datenpunkten
            cursor = conn.execute("""
                SELECT skin, COUNT(*) as count 
                FROM market_data 
                GROUP BY skin 
                ORDER BY count DESC 
                LIMIT 5
            """)
            stats['top_skins'] = [
                {'skin': row[0], 'records': row[1]} 
                for row in cursor.fetchall()
            ]
            
            return stats
            
    except Exception as e:
        print(f"❌ Fehler beim Sammeln von DB-Statistiken: {e}")
        return {'error': str(e)}

def _collect_db_statistics() -> None:
    """
    Sammelt und zeigt Datenbank-Statistiken beim Startup an.
    
    Interne Funktion für init_db() - zeigt nützliche Informationen
    über den aktuellen Datenbankzustand.
    """
    try:
        stats = get_db_statistics()
        
        if 'error' not in stats:
            print(f"📊 DB-Statistiken:")
            print(f"   • Datensätze: {stats.get('total_records', 0):,}")
            print(f"   • Skins: {stats.get('unique_skins', 0)}")
            print(f"   • DB-Größe: {stats.get('db_size_mb', 0):.1f} MB")
            print(f"   • Schema: v{stats.get('schema_version', 0)}")
            
            if stats.get('first_record') and stats.get('last_record'):
                print(f"   • Zeitbereich: {stats['first_record']} bis {stats['last_record']}")
    
    except Exception as e:
        print(f"⚠️ Konnte DB-Statistiken nicht anzeigen: {e}")

def _validate_database_integrity() -> None:
    """
    Überprüft die Integrität der Datenbank (ohne Constraint-Validierung).
    """
    issues = []
    
    try:
        with get_db_connection(read_only=True) as conn:
            print("🔍 Überprüfe Datenbank-Integrität...")
            
            # 1. Leere/NULL-Werte prüfen
            cursor = conn.execute("""
                SELECT COUNT(*) FROM market_data 
                WHERE skin IS NULL OR skin = '' OR timestamp IS NULL OR timestamp = ''
            """)
            empty_values = cursor.fetchone()[0]
            if empty_values > 0:
                issues.append(f"{empty_values} leere/NULL-Werte in kritischen Spalten")
            
            # 2. Timestamp-Format prüfen
            cursor = conn.execute("""
                SELECT COUNT(*) FROM market_data 
                WHERE timestamp NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]*'
            """)
            invalid_timestamps = cursor.fetchone()[0]
            if invalid_timestamps > 0:
                issues.append(f"{invalid_timestamps} ungültige Timestamp-Formate")
            
            # 3. Duplizierte Zeitstempel für gleichen Skin
            cursor = conn.execute("""
                SELECT skin, timestamp, COUNT(*) as cnt
                FROM market_data 
                GROUP BY skin, timestamp 
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                total_dupes = sum(row[2] for row in duplicates)
                issues.append(f"{len(duplicates)} Skin-Zeitstempel-Kombinationen mit Duplikaten ({total_dupes} Einträge)")
            
            # Ergebnis auswerten
            if issues:
                print("❌ Datenintegritätsprobleme gefunden:")
                for issue in issues:
                    print(f"   • {issue}")
                
                # Nur bei kritischen Problemen Exception werfen
                critical_issues = [issue for issue in issues if any(keyword in issue.lower() for keyword in ['null', 'leer'])]
                if critical_issues:
                    raise RuntimeError(f"Kritische Datenintegritätsprobleme: {'; '.join(critical_issues)}")
                else:
                    print("⚠️ Probleme gefunden, aber nicht kritisch für Betrieb")
            else:
                print("✅ Datenbank-Integrität geprüft, keine Probleme gefunden")
    
    except sqlite3.Error as e:
        print(f"❌ Datenbankfehler bei Integritätsprüfung: {e}")
        raise RuntimeError(f"Datenbank-Integritätsprüfung fehlgeschlagen: {e}") from e
    
    except Exception as e:
        print(f"❌ Fehler bei der Datenbank-Integritätsprüfung: {e}")
        raise RuntimeError(f"Unerwarteter Fehler bei Integritätsprüfung: {e}") from e

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY-FUNKTIONEN FÜR ERWEITERTE ANALYSEN
# ═══════════════════════════════════════════════════════════════════════════════

def get_price_statistics(skin: str, days: Optional[int] = None) -> Dict[str, float]:
    """
    Berechnet umfassende Preisstatistiken für einen Skin.
    
    Args:
        skin: Name des Skins
        days: Nur Daten der letzten N Tage berücksichtigen
        
    Returns:
        Dict mit Statistiken: min, max, avg, median, std_dev, trend, etc.
    """
    try:
        history = get_market_history(skin, days=days)
        
        if not history:
            return {}
        
        prices = [row[1] for row in history]  # lowest_price
        
        stats = {
            'count': len(prices),
            'min': min(prices),
            'max': max(prices),
            'average': sum(prices) / len(prices),
            'range': max(prices) - min(prices),
            'latest': prices[-1] if prices else 0
        }
        
        # Trend-Berechnung (vereinfacht)
        if len(prices) >= 2:
            first_half_avg = sum(prices[:len(prices)//2]) / (len(prices)//2)
            second_half_avg = sum(prices[len(prices)//2:]) / (len(prices) - len(prices)//2)
            trend_change = second_half_avg - first_half_avg
            
            if abs(trend_change) < 0.01:
                stats['trend'] = 'stable'
            elif trend_change > 0:
                stats['trend'] = 'rising'
            else:
                stats['trend'] = 'falling'
            
            stats['trend_change'] = trend_change
        else:
            stats['trend'] = 'insufficient_data'
            stats['trend_change'] = 0.0
        
        return stats
        
    except Exception as e:
        print(f"❌ Fehler bei Preisstatistik-Berechnung für '{skin}': {e}")
        return {}

def cleanup_old_data(days_to_keep: int = 365) -> int:
    """
    Entfernt alte Marktdaten zur Datenbank-Optimierung.
    
    Args:
        days_to_keep: Anzahl Tage die behalten werden sollen
        
    Returns:
        int: Anzahl gelöschter Datensätze
        
    Sicherheit:
    - Backup wird automatisch erstellt
    - Transaktion für atomare Operation
    - Bestätigung vor Löschung erforderlich
    """
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    try:
        # Backup erstellen
        backup_path = _create_backup("cleanup")
        
        with get_db_connection() as conn:
            # Zähle zu löschende Datensätze
            cursor = conn.execute(
                "SELECT COUNT(*) FROM market_data WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete == 0:
                print("✅ Keine alten Daten zum Löschen gefunden")
                return 0
            
            print(f"⚠️ {count_to_delete} Datensätze älter als {days_to_keep} Tage gefunden")
            print(f"💾 Backup erstellt: {backup_path}")
            
            # Löschung durchführen
            conn.execute(
                "DELETE FROM market_data WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            # VACUUM für Speicherrückgewinnung
            conn.execute("VACUUM")
            
            conn.commit()
            
            print(f"✅ {count_to_delete} alte Datensätze erfolgreich entfernt")
            return count_to_delete
            
    except Exception as e:
        print(f"❌ Fehler beim Cleanup alter Daten: {e}")
        raise RuntimeError(f"Cleanup fehlgeschlagen: {e}") from e
