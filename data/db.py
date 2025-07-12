import sqlite3
from datetime import datetime
import csv
from typing import List, Tuple, Optional

DB_PATH = "skin_prices.db"

def init_db():
    """Initialisiert die SQLite-Datenbank mit der notwendigen Tabellenstruktur."""
    with sqlite3.connect(DB_PATH) as conn:
        # Erweiterte Tabelle für umfassende Marktdaten
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                skin TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                median_price REAL DEFAULT 0,
                volume INTEGER DEFAULT 0,
                spread_absolute REAL DEFAULT 0,
                spread_percentage REAL DEFAULT 0
            )
        """)
        
        # Index für bessere Performance bei Abfragen
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_skin_timestamp 
            ON price_history(skin, timestamp)
        """)

def insert_price(skin: str, price: float, volume: int = 0):
    """
    Fügt einen neuen Preiseintrag zur Datenbank hinzu.
    
    Args:
        skin: Name des Skins
        price: Preis des Skins
        volume: Handelsvolumen (optional)
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO price_history (skin, timestamp, price, volume) VALUES (?, ?, ?, ?)",
            (skin, datetime.now().isoformat(timespec='seconds'), price, volume)
        )

def insert_comprehensive_market_data(skin: str, market_data):
    """
    Fügt umfassende Marktdaten zur Datenbank hinzu.
    
    Args:
        skin: Name des Skins
        market_data: MarketData Objekt mit allen Marktinformationen
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO price_history 
            (skin, timestamp, price, median_price, volume, spread_absolute, spread_percentage) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            skin, 
            datetime.now().isoformat(timespec='seconds'), 
            market_data.lowest_price,
            market_data.median_price,
            market_data.volume,
            market_data.spread_absolute,
            market_data.spread_percentage
        ))

def get_price_history(skin: str) -> List[Tuple[str, float]]:
    """
    Ruft die Preishistorie für einen Skin ab.
    
    Args:
        skin: Name des Skins
        
    Returns:
        Liste von (timestamp, price) Tupeln, sortiert nach Zeit
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT timestamp, price FROM price_history WHERE skin = ? ORDER BY timestamp",
            (skin,)
        )
        return cursor.fetchall()

def export_price_history(skin: str, filename: str):
    """
    Exportiert die Preishistorie eines Skins in eine CSV-Datei.
    
    Args:
        skin: Name des Skins
        filename: Pfad zur Ausgabe-CSV-Datei
    """
    rows = get_price_history(skin)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Preis (€)"])
        writer.writerows(rows)

def export_comprehensive_market_data(skin: str, filename: str):
    """
    Exportiert die kompletten Marktdaten eines Skins in eine CSV-Datei.
    Enthält alle Daten: Preis, Median-Preis, Volumen und Spread.
    
    Args:
        skin: Name des Skins
        filename: Pfad zur Ausgabe-CSV-Datei
    """
    rows = get_comprehensive_history(skin)
    
    if not rows:
        # Fallback auf einfache Preishistorie
        simple_rows = get_price_history(skin)
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Preis (€)"])
            writer.writerows(simple_rows)
        return
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", 
            "Niedrigster Preis (€)", 
            "Median Preis (€)", 
            "Handelsvolumen", 
            "Spread Absolut (€)", 
            "Spread Prozent (%)"
        ])
        writer.writerows(rows)

def get_volume_history(skin: str) -> List[Tuple[str, int]]:
    """
    Ruft die Volumenhistorie für einen Skin ab.
    
    Args:
        skin: Name des Skins
        
    Returns:
        Liste von (timestamp, volume) Tupeln, sortiert nach Zeit
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT timestamp, volume FROM price_history WHERE skin = ? ORDER BY timestamp",
            (skin,)
        )
        return cursor.fetchall()

def get_spread_history(skin: str) -> List[Tuple[str, float, float]]:
    """
    Ruft die Spread-Historie für einen Skin ab.
    
    Args:
        skin: Name des Skins
        
    Returns:
        Liste von (timestamp, spread_absolute, spread_percentage) Tupeln
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """SELECT timestamp, spread_absolute, spread_percentage 
               FROM price_history WHERE skin = ? ORDER BY timestamp""",
            (skin,)
        )
        return cursor.fetchall()

def get_comprehensive_history(skin: str) -> List[Tuple]:
    """
    Ruft die komplette Markthistorie für einen Skin ab.
    
    Args:
        skin: Name des Skins
        
    Returns:
        Liste von (timestamp, price, median_price, volume, spread_absolute, spread_percentage) Tupeln
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """SELECT timestamp, price, median_price, volume, spread_absolute, spread_percentage 
               FROM price_history WHERE skin = ? ORDER BY timestamp""",
            (skin,)
        )
        return cursor.fetchall()
