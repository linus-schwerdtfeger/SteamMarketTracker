import sqlite3
from datetime import datetime

DB_PATH = "skin_prices.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                skin TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)

def insert_price(skin, price):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO price_history (skin, timestamp, price) VALUES (?, ?, ?)",
            (skin, datetime.now().isoformat(timespec='seconds'), price)
        )

def get_price_history(skin):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT timestamp, price FROM price_history WHERE skin = ? ORDER BY timestamp",
            (skin,)
        )
        return cursor.fetchall()

def init_db():
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

def insert_price(skin, price, volume=0):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO price_history (skin, timestamp, price, volume) VALUES (?, ?, ?, ?)",
            (skin, datetime.now().isoformat(timespec='seconds'), price, volume)
        )

import csv

def export_price_history(skin, filename):
    rows = get_price_history(skin)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Preis (€)"])
        writer.writerows(rows)
