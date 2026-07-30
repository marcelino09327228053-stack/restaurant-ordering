"""SQLite connection and schema for restaurant ordering."""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("SQLITE_PATH", "restaurant.db"))
_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        restaurant_name TEXT NOT NULL,
        cashier_password_hash TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL DEFAULT 'Meals',
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL,
        available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER NOT NULL,
        order_number TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        customer_note TEXT NOT NULL DEFAULT '',
        total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (table_id) REFERENCES restaurant_tables(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES restaurant_orders(id),
        FOREIGN KEY (menu_item_id) REFERENCES restaurant_menu_items(id)
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_orders_status
    ON restaurant_orders (status, created_at)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON restaurant_order_items (order_id)
    """)
    conn.commit()
