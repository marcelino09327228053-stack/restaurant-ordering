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
        cashier_password_hash TEXT NOT NULL,
        qr_caption TEXT NOT NULL DEFAULT 'Scan the QR code to order'
    )
    """)

    settings_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(settings)")}
    if "qr_caption" not in settings_cols:
        cursor.execute(
            "ALTER TABLE settings ADD COLUMN qr_caption TEXT NOT NULL DEFAULT 'Scan the QR code to order'"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    table_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(restaurant_tables)")}
    if "qr_caption" not in table_cols:
        cursor.execute(
            "ALTER TABLE restaurant_tables ADD COLUMN qr_caption TEXT NOT NULL DEFAULT ''"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL DEFAULT 'Meals',
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL,
        image_url TEXT NOT NULL DEFAULT '',
        available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    columns = {row["name"] for row in cursor.execute("PRAGMA table_info(restaurant_menu_items)")}
    if "image_url" not in columns:
        cursor.execute(
            "ALTER TABLE restaurant_menu_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''"
        )

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
    CREATE TABLE IF NOT EXISTS owner_payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        account_name TEXT NOT NULL DEFAULT '',
        account_number_masked TEXT NOT NULL DEFAULT '',
        qr_image_url TEXT NOT NULL,
        instructions TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (owner_id) REFERENCES owners(id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_payment_methods_owner_active
    ON owner_payment_methods (owner_id, active, sort_order, id)
    """)

    order_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(restaurant_orders)")}
    for col, decl in (
        ("payment_method_id", "INTEGER"),
        ("payment_method_label", "TEXT NOT NULL DEFAULT ''"),
        ("payment_reference", "TEXT NOT NULL DEFAULT ''"),
        ("payment_proof_url", "TEXT NOT NULL DEFAULT ''"),
        ("payment_status", "TEXT NOT NULL DEFAULT 'unpaid'"),
        ("payment_verified_at", "TEXT"),
    ):
        if col not in order_cols:
            cursor.execute(f"ALTER TABLE restaurant_orders ADD COLUMN {col} {decl}")

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_orders_status
    ON restaurant_orders (status, created_at)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON restaurant_order_items (order_id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        restaurant_name TEXT NOT NULL DEFAULT 'My Restaurant',
        slug TEXT UNIQUE,
        logo_url TEXT NOT NULL DEFAULT '',
        about_text TEXT NOT NULL DEFAULT '',
        hero_images TEXT NOT NULL DEFAULT '[]',
        slideshow_style TEXT NOT NULL DEFAULT 'fade',
        custom_design TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    owner_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(owners)")}
    for col, decl in (
        ("slug", "TEXT"),
        ("logo_url", "TEXT NOT NULL DEFAULT ''"),
        ("about_text", "TEXT NOT NULL DEFAULT ''"),
        ("hero_images", "TEXT NOT NULL DEFAULT '[]'"),
        ("slideshow_style", "TEXT NOT NULL DEFAULT 'fade'"),
        ("custom_design", "TEXT NOT NULL DEFAULT '{}'"),
    ):
        if col not in owner_cols:
            cursor.execute(f"ALTER TABLE owners ADD COLUMN {col} {decl}")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_email_otps_email
    ON email_otps (email, created_at)
    """)

    # Scope existing tables to owners (nullable for legacy cashier board data).
    for table in ("restaurant_menu_items", "restaurant_tables", "restaurant_orders"):
        columns = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")}
        if "owner_id" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS table_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER NOT NULL,
        sender TEXT NOT NULL CHECK (sender IN ('customer', 'cashier')),
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (table_id) REFERENCES restaurant_tables(id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_table_messages_table
    ON table_messages (table_id, id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ops_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        room_type TEXT NOT NULL DEFAULT 'custom',
        qr_caption TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        sender TEXT NOT NULL CHECK (sender IN ('cashier', 'member')),
        sender_name TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (room_id) REFERENCES ops_rooms(id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_room_messages_room
    ON room_messages (room_id, id)
    """)

    conn.commit()
