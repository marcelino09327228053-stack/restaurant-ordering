"""Restaurant ordering data access."""

import os
import secrets
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv

from app.auth import hash_password, verify_password
from app.db import get_connection

load_dotenv()

ORDER_STATUSES = ("pending", "confirmed", "preparing", "ready", "served", "cancelled")
STATUS_TRANSITIONS = {
    "pending": {"confirmed", "preparing", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served", "cancelled"},
    "served": set(),
    "cancelled": set(),
}

DEFAULT_MENU = (
    ("Rice Meals", "Chicken Inasal", "Grilled chicken, rice, and atchara", 149.0),
    ("Rice Meals", "Pork Sisig", "Sizzling pork sisig served with rice", 169.0),
    ("Rice Meals", "Beef Tapa", "Tender beef tapa, egg, and garlic rice", 179.0),
    ("Noodles", "Pancit Canton", "Stir-fried noodles with vegetables", 139.0),
    ("Drinks", "Iced Tea", "House-blended iced tea", 49.0),
    ("Desserts", "Leche Flan", "Creamy caramel custard", 79.0),
)


def ensure_defaults() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM settings WHERE id = 1")
    if cursor.fetchone() is None:
        restaurant_name = os.getenv("RESTAURANT_NAME", "My Restaurant")
        password = os.getenv("CASHIER_PASSWORD", "cashier123")
        cursor.execute(
            """
            INSERT INTO settings (id, restaurant_name, cashier_password_hash)
            VALUES (1, ?, ?)
            """,
            (restaurant_name, hash_password(password)),
        )

    cursor.execute("SELECT COUNT(*) FROM restaurant_tables")
    if cursor.fetchone()[0] == 0:
        for number in range(1, 11):
            cursor.execute(
                """
                INSERT INTO restaurant_tables (name, access_code)
                VALUES (?, ?)
                """,
                (f"Table {number}", secrets.token_urlsafe(8)),
            )

    cursor.execute("SELECT COUNT(*) FROM restaurant_menu_items")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO restaurant_menu_items
                (category, name, description, price)
            VALUES (?, ?, ?, ?)
            """,
            list(DEFAULT_MENU),
        )
    conn.commit()


def get_settings() -> dict:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute("SELECT restaurant_name FROM settings WHERE id = 1")
    row = cursor.fetchone()
    return {"restaurant_name": row["restaurant_name"]}


def authenticate_cashier(password: str) -> bool:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute("SELECT cashier_password_hash FROM settings WHERE id = 1")
    row = cursor.fetchone()
    return bool(row) and verify_password(password, row["cashier_password_hash"])


def get_public_table(access_code: str) -> dict | None:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, name
        FROM restaurant_tables
        WHERE access_code = ? AND active = 1
        """,
        (access_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    settings = get_settings()
    return {
        "id": row["id"],
        "name": row["name"],
        "restaurant_name": settings["restaurant_name"],
    }


def list_menu(available_only: bool = False) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    sql = """
        SELECT id, category, name, description, price, available
        FROM restaurant_menu_items
    """
    if available_only:
        sql += " WHERE available = 1"
    sql += " ORDER BY category ASC, name ASC"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def create_menu_item(
    category: str, name: str, description: str, price: float
) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM restaurant_menu_items WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
    )
    if cursor.fetchone():
        return None
    cursor.execute(
        """
        INSERT INTO restaurant_menu_items (category, name, description, price)
        VALUES (?, ?, ?, ?)
        """,
        (category.strip(), name.strip(), description.strip(), round(price, 2)),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def set_menu_item_availability(item_id: int, available: bool) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE restaurant_menu_items SET available = ? WHERE id = ?",
        (1 if available else 0, item_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (item_id,))
    return dict(cursor.fetchone())


def list_tables() -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, name, access_code, active, created_at
        FROM restaurant_tables
        ORDER BY id ASC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def create_table(name: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM restaurant_tables WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
    )
    if cursor.fetchone():
        return None
    cursor.execute(
        """
        INSERT INTO restaurant_tables (name, access_code)
        VALUES (?, ?)
        """,
        (name.strip(), secrets.token_urlsafe(8)),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_tables WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def create_order(table: dict, items: list[dict], customer_note: str = "") -> dict:
    quantities: dict[int, int] = {}
    for item in items:
        item_id = int(item["menu_item_id"])
        quantities[item_id] = quantities.get(item_id, 0) + int(item["quantity"])

    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ", ".join("?" for _ in quantities)
    cursor.execute(
        f"""
        SELECT id, name, price
        FROM restaurant_menu_items
        WHERE available = 1 AND id IN ({placeholders})
        """,
        tuple(quantities.keys()),
    )
    menu_items = {int(row["id"]): dict(row) for row in cursor.fetchall()}
    if len(menu_items) != len(quantities):
        raise ValueError("One or more menu items are unavailable.")

    lines = []
    total = 0.0
    for item_id, quantity in quantities.items():
        menu_item = menu_items[item_id]
        line_total = round(float(menu_item["price"]) * quantity, 2)
        total += line_total
        lines.append(
            (item_id, menu_item["name"], float(menu_item["price"]), quantity, line_total)
        )
    total = round(total, 2)
    order_number = f"ORD-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}"

    try:
        cursor.execute(
            """
            INSERT INTO restaurant_orders
                (table_id, order_number, customer_note, total)
            VALUES (?, ?, ?, ?)
            """,
            (table["id"], order_number, customer_note.strip(), total),
        )
        order_id = cursor.lastrowid
        cursor.executemany(
            """
            INSERT INTO restaurant_order_items
                (order_id, menu_item_id, item_name, unit_price, quantity, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(order_id, *line) for line in lines],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_order_by_id(order_id)


def _attach_items(orders: list[dict]) -> list[dict]:
    if not orders:
        return orders
    order_ids = [order["id"] for order in orders]
    placeholders = ", ".join("?" for _ in order_ids)
    cursor = get_connection().cursor()
    cursor.execute(
        f"""
        SELECT order_id, menu_item_id, item_name, unit_price, quantity, line_total
        FROM restaurant_order_items
        WHERE order_id IN ({placeholders})
        ORDER BY id ASC
        """,
        tuple(order_ids),
    )
    grouped = {order_id: [] for order_id in order_ids}
    for row in cursor.fetchall():
        item = dict(row)
        grouped[item.pop("order_id")].append(item)
    for order in orders:
        order["items"] = grouped[order["id"]]
    return orders


def get_order_by_id(order_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT o.*, t.name AS table_name
        FROM restaurant_orders o
        JOIN restaurant_tables t ON t.id = o.table_id
        WHERE o.id = ?
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return _attach_items([dict(row)])[0]


def get_public_order(access_code: str, order_number: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT o.*, t.name AS table_name
        FROM restaurant_orders o
        JOIN restaurant_tables t ON t.id = o.table_id
        WHERE o.order_number = ? AND t.access_code = ?
        """,
        (order_number, access_code),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return _attach_items([dict(row)])[0]


def list_orders(status: str | None = None) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    sql = """
        SELECT o.*, t.name AS table_name
        FROM restaurant_orders o
        JOIN restaurant_tables t ON t.id = o.table_id
    """
    params: list = []
    if status:
        sql += " WHERE o.status = ?"
        params.append(status)
    sql += " ORDER BY o.created_at DESC, o.id DESC LIMIT 100"
    cursor.execute(sql, tuple(params))
    return _attach_items([dict(row) for row in cursor.fetchall()])


def update_order_status(order_id: int, status: str) -> tuple[dict | None, str | None]:
    order = get_order_by_id(order_id)
    if order is None:
        return None, "not_found"
    if status == order["status"]:
        return order, None
    if status not in STATUS_TRANSITIONS[order["status"]]:
        return order, "invalid_transition"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE restaurant_orders
        SET status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (status, order_id),
    )
    conn.commit()
    return get_order_by_id(order_id), None
