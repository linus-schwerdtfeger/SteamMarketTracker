import sqlite3
from datetime import datetime
import csv
from typing import List, Tuple

DB_PATH = "skin_prices.db"

def init_db():
    """Initialisiert die Datenbank für erweiterte Marktdaten."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY,
                skin TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                lowest_price REAL NOT NULL,
                median_price REAL NOT NULL,
                volume INTEGER NOT NULL,
                spread_absolute REAL NOT NULL,
                spread_percentage REAL NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_skin_timestamp 
            ON market_data(skin, timestamp)
        """)

def insert_market_data(skin: str, market_data):
    """
    Fügt umfassende Marktdaten zur Datenbank hinzu.
    
    Args:
        skin: Name des Skins
        market_data: MarketData Objekt
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO market_data 
            (skin, timestamp, lowest_price, median_price, volume, spread_absolute, spread_percentage) 
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

def get_market_history(skin: str) -> List[Tuple]:
    """
    Ruft die komplette Markthistorie für einen Skin ab.
    
    Returns:
        Liste von (timestamp, lowest_price, median_price, volume, spread_absolute, spread_percentage) Tupeln
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """SELECT timestamp, lowest_price, median_price, volume, spread_absolute, spread_percentage 
               FROM market_data WHERE skin = ? ORDER BY timestamp""",
            (skin,)
        )
        return cursor.fetchall()

def export_market_data(skin: str, filename: str):
    """Exportiert alle Marktdaten als CSV."""
    rows = get_market_history(skin)
    
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

def get_latest_price(skin: str) -> float:
    """Ruft den neuesten Preis für einen Skin ab."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT lowest_price FROM market_data WHERE skin = ? ORDER BY timestamp DESC LIMIT 1",
            (skin,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0.0
