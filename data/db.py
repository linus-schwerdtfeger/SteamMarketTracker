import sqlite3
from datetime import datetime
import csv
from typing import List, Tuple

DB_PATH = "skin_prices.db"

def init_db():
    """Initialisiert die SQLite-Datenbank mit der notwendigen Tabellenstruktur."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                skin TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER DEFAULT 0
            )
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
