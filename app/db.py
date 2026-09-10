"""Database connection and schema for restaurant ordering.

Uses PostgreSQL when DATABASE_URL is set (for Render), otherwise keeps
SQLite for local development.
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = Path(os.getenv("SQLITE_PATH", "restaurant.db"))

_sqlite_conn: sqlite3.Connection | None = None
_pg_conn = None


class CompatRow:
    """Row that supports both row[0] and row["column"] like sqlite3.Row."""

    def __init__(self, values: tuple, columns: list[str]):
        self._values = tuple(values)
        self._columns = columns
        self._index = {name: i for i, name in enumerate(columns)}

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._values[self._index[key]]
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return list(self._columns)


class PostgresCursorCompat:
    """Small DB-API compatibility wrapper for the existing SQLite-style queries."""

    def __init__(self, connection):
        self._connection = connection
        self._cursor = connection.cursor()
        self._last_insert_table: str | None = None
        self._lastrowid: int | None = None

    @staticmethod
    def _convert_sql(sql: str) -> str:
        # Existing repository queries use SQLite's datetime('now') and ? placeholders.
        sql = re.sub(r"datetime\s*\(\s*['\"]now['\"]\s*\)", "CURRENT_TIMESTAMP", sql, flags=re.I)
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple | list = ()):
        converted = self._convert_sql(sql)
        self._cursor.execute(converted, params)
        self._lastrowid = None
        match = re.match(r"\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", sql, flags=re.I)
        self._last_insert_table = match.group(1) if match else None
        return self

    def executemany(self, sql: str, seq_of_params):
        self._cursor.executemany(self._convert_sql(sql), seq_of_params)
        self._lastrowid = None
        match = re.match(r"\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", sql, flags=re.I)
        self._last_insert_table = match.group(1) if match else None
        return self

    def _columns(self) -> list[str]:
        if not self._cursor.description:
            return []
        return [desc.name for desc in self._cursor.description]

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return CompatRow(tuple(row), self._columns())

    def fetchall(self):
        rows = self._cursor.fetchall()
        columns = self._columns()
        return [CompatRow(tuple(row), columns) for row in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        if self._lastrowid is not None:
            return self._lastrowid
        if not self._last_insert_table:
            return None
        # All generated IDs in the PostgreSQL schema below use SERIAL sequences.
        with self._connection.cursor() as cur:
            cur.execute(
                "SELECT currval(pg_get_serial_sequence(%s, 'id'))",
                (self._last_insert_table,),
            )
            row = cur.fetchone()
            self._lastrowid = int(row[0]) if row else None
        return self._lastrowid


class PostgresConnectionCompat:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PostgresCursorCompat(self._connection)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def get_connection():
    global _sqlite_conn, _pg_conn

    if using_postgres():
        if _pg_conn is None or _pg_conn.closed:
            import psycopg

            raw = psycopg.connect(DATABASE_URL)
            _pg_conn = PostgresConnectionCompat(raw)
        return _pg_conn

    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
    return _sqlite_conn


def _init_postgres_db() -> None:
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owners (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        restaurant_name TEXT NOT NULL DEFAULT 'My Restaurant',
        slug TEXT UNIQUE,
        logo_url TEXT NOT NULL DEFAULT '',
        about_text TEXT NOT NULL DEFAULT '',
        hero_images TEXT NOT NULL DEFAULT '[]',
        slideshow_style TEXT NOT NULL DEFAULT 'fade',
        custom_design TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_tables (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text),
        qr_caption TEXT NOT NULL DEFAULT '',
        owner_id INTEGER REFERENCES owners(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_menu_items (
        id SERIAL PRIMARY KEY,
        category TEXT NOT NULL DEFAULT 'Meals',
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        price DOUBLE PRECISION NOT NULL,
        image_url TEXT NOT NULL DEFAULT '',
        available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text),
        owner_id INTEGER REFERENCES owners(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_orders (
        id SERIAL PRIMARY KEY,
        table_id INTEGER NOT NULL REFERENCES restaurant_tables(id),
        order_number TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        customer_note TEXT NOT NULL DEFAULT '',
        total DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text),
        updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text),
        owner_id INTEGER REFERENCES owners(id),
        payment_method_id INTEGER,
        payment_method_label TEXT NOT NULL DEFAULT '',
        payment_reference TEXT NOT NULL DEFAULT '',
        payment_proof_url TEXT NOT NULL DEFAULT '',
        payment_status TEXT NOT NULL DEFAULT 'unpaid',
        payment_verified_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES restaurant_orders(id),
        menu_item_id INTEGER NOT NULL REFERENCES restaurant_menu_items(id),
        item_name TEXT NOT NULL,
        unit_price DOUBLE PRECISION NOT NULL,
        quantity INTEGER NOT NULL,
        line_total DOUBLE PRECISION NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owner_payment_methods (
        id SERIAL PRIMARY KEY,
        owner_id INTEGER NOT NULL REFERENCES owners(id),
        provider TEXT NOT NULL,
        account_name TEXT NOT NULL DEFAULT '',
        account_number_masked TEXT NOT NULL DEFAULT '',
        qr_image_url TEXT NOT NULL,
        instructions TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_otps (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS table_messages (
        id SERIAL PRIMARY KEY,
        table_id INTEGER NOT NULL REFERENCES restaurant_tables(id),
        sender TEXT NOT NULL CHECK (sender IN ('customer', 'cashier')),
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ops_rooms (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        room_type TEXT NOT NULL DEFAULT 'custom',
        qr_caption TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room_messages (
        id SERIAL PRIMARY KEY,
        room_id INTEGER NOT NULL REFERENCES ops_rooms(id),
        sender TEXT NOT NULL CHECK (sender IN ('cashier', 'member')),
        sender_name TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_methods_owner_active ON owner_payment_methods (owner_id, active, sort_order, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON restaurant_orders (status, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON restaurant_order_items (order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_email ON email_otps (email, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_table_messages_table ON table_messages (table_id, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_messages_room ON room_messages (room_id, id)")

    conn.commit()


def _init_sqlite_db() -> None:
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
        cursor.execute("ALTER TABLE settings ADD COLUMN qr_caption TEXT NOT NULL DEFAULT 'Scan the QR code to order'")

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        access_code TEXT NOT NULL UNIQUE,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        qr_caption TEXT NOT NULL DEFAULT '',
        owner_id INTEGER,
        FOREIGN KEY (owner_id) REFERENCES owners(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL DEFAULT 'Meals',
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL,
        image_url TEXT NOT NULL DEFAULT '',
        available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        owner_id INTEGER,
        FOREIGN KEY (owner_id) REFERENCES owners(id)
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
        owner_id INTEGER,
        payment_method_id INTEGER,
        payment_method_label TEXT NOT NULL DEFAULT '',
        payment_reference TEXT NOT NULL DEFAULT '',
        payment_proof_url TEXT NOT NULL DEFAULT '',
        payment_status TEXT NOT NULL DEFAULT 'unpaid',
        payment_verified_at TEXT,
        FOREIGN KEY (table_id) REFERENCES restaurant_tables(id),
        FOREIGN KEY (owner_id) REFERENCES owners(id)
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
    CREATE TABLE IF NOT EXISTS email_otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

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

    # Keep older local SQLite files compatible with newer columns.
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

    for table in ("restaurant_menu_items", "restaurant_tables", "restaurant_orders"):
        columns = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")}
        if "owner_id" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER")

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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_methods_owner_active ON owner_payment_methods (owner_id, active, sort_order, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON restaurant_orders (status, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON restaurant_order_items (order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_email ON email_otps (email, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_table_messages_table ON table_messages (table_id, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_messages_room ON room_messages (room_id, id)")

    conn.commit()


def init_db() -> None:
    if using_postgres():
        _init_postgres_db()
    else:
        _init_sqlite_db()
