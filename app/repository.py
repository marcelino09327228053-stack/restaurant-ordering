"""Restaurant ordering data access."""

import json
import os
import re
import secrets
from datetime import datetime, timezone
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

    restaurant_name = os.getenv("RESTAURANT_NAME", "My Restaurant")
    password = os.getenv("CASHIER_PASSWORD", "cashier123")
    cursor.execute("SELECT cashier_password_hash FROM settings WHERE id = 1")
    settings = cursor.fetchone()
    if settings is None:
        cursor.execute(
            """
            INSERT INTO settings (id, restaurant_name, cashier_password_hash)
            VALUES (1, ?, ?)
            """,
            (restaurant_name, hash_password(password)),
        )
    elif not verify_password(password, settings["cashier_password_hash"]):
        # Keep .env CASHIER_PASSWORD as the source of truth for this local app.
        cursor.execute(
            """
            UPDATE settings
            SET restaurant_name = ?, cashier_password_hash = ?
            WHERE id = 1
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
    cursor.execute("SELECT restaurant_name, qr_caption FROM settings WHERE id = 1")
    row = cursor.fetchone()
    caption = (row["qr_caption"] if row["qr_caption"] is not None else "").strip()
    if not caption:
        caption = "Scan the QR code to order"
    return {
        "restaurant_name": row["restaurant_name"],
        "qr_caption": caption,
    }


def update_qr_caption(caption: str) -> dict:
    text = (caption or "").strip()
    if not text:
        raise ValueError("QR text cannot be empty.")
    if len(text) > 120:
        raise ValueError("QR text is too long (max 120 characters).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET qr_caption = ? WHERE id = 1", (text,))
    conn.commit()
    return get_settings()


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
        SELECT id, name, owner_id
        FROM restaurant_tables
        WHERE access_code = ? AND active = 1
        """,
        (access_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    settings = get_settings()
    restaurant_name = settings["restaurant_name"]
    if row["owner_id"] is not None:
        owner = get_owner(int(row["owner_id"]))
        if owner:
            restaurant_name = owner["restaurant_name"]
    return {
        "id": row["id"],
        "name": row["name"],
        "owner_id": row["owner_id"],
        "restaurant_name": restaurant_name,
    }


def list_menu(available_only: bool = False) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    sql = """
        SELECT id, category, name, description, price, image_url, available
        FROM restaurant_menu_items
    """
    if available_only:
        sql += " WHERE available = 1"
    sql += " ORDER BY category ASC, name ASC"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def list_cashier_menu(owner_id: int | None = None) -> list[dict]:
    if owner_id is not None:
        return without_legacy_samples(list_owner_menu(owner_id))
    cursor = get_connection().execute(
        """SELECT id, category, name, description, price, image_url, available, owner_id
        FROM restaurant_menu_items
        WHERE available = 1 AND (? IS NULL OR owner_id = ?)
          AND (owner_id IS NOT NULL OR NOT EXISTS (SELECT 1 FROM owners))
        ORDER BY category ASC, name ASC""", (owner_id, owner_id)
    )
    return without_legacy_samples([dict(row) for row in cursor.fetchall()])


LEGACY_SAMPLE_NAMES = {
    "Chicken Inasal", "Pork Sisig", "Beef Tapa", "Pancit Canton", "Iced Tea", "Leche Flan",
}


def without_legacy_samples(items: list[dict]) -> list[dict]:
    return [item for item in items if str(item.get("name") or "").strip() not in LEGACY_SAMPLE_NAMES]


def create_menu_item(
    category: str, name: str, description: str, price: float, image_url: str = ""
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
        INSERT INTO restaurant_menu_items (category, name, description, price, image_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            category.strip(),
            name.strip(),
            description.strip(),
            round(price, 2),
            image_url.strip(),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def set_menu_item_image(item_id: int, image_url: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE restaurant_menu_items SET image_url = ? WHERE id = ?",
        (image_url.strip(), item_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (item_id,))
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


def list_tables(owner_id: int | None = None) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, name, access_code, active, created_at, qr_caption
        FROM restaurant_tables
        WHERE active = 1
          AND (? IS NULL OR owner_id = ?)
          AND (owner_id IS NOT NULL OR NOT EXISTS (SELECT 1 FROM owners))
        ORDER BY id ASC
        """, (owner_id, owner_id)
    )
    default_caption = get_settings()["qr_caption"]
    tables = []
    for row in cursor.fetchall():
        item = dict(row)
        custom = (item.get("qr_caption") or "").strip()
        item["qr_caption"] = custom
        item["display_caption"] = custom or default_caption
        tables.append(item)
    return tables


def create_table(name: str, qr_caption: str = "") -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM restaurant_tables WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
    )
    if cursor.fetchone():
        return None
    caption = (qr_caption or "").strip()[:120]
    cursor.execute(
        """
        INSERT INTO restaurant_tables (name, access_code, qr_caption)
        VALUES (?, ?, ?)
        """,
        (name.strip(), secrets.token_urlsafe(8), caption),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_tables WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    default_caption = get_settings()["qr_caption"]
    custom = (row.get("qr_caption") or "").strip()
    row["qr_caption"] = custom
    row["display_caption"] = custom or default_caption
    return row


def update_table_qr_caption(table_id: int, qr_caption: str) -> dict | None:
    text = (qr_caption or "").strip()
    if len(text) > 120:
        raise ValueError("QR text is too long (max 120 characters).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE restaurant_tables SET qr_caption = ? WHERE id = ?",
        (text, table_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    for table in list_tables():
        if table["id"] == table_id:
            return table
    return None


def list_payment_methods(owner_id: int, active_only: bool = False) -> list[dict]:
    cursor = get_connection().cursor()
    sql = """
        SELECT id, owner_id, provider, account_name, account_number_masked,
               qr_image_url, instructions, active, sort_order, created_at
        FROM owner_payment_methods
        WHERE owner_id = ?
    """
    params: list = [owner_id]
    if active_only:
        sql += " AND active = 1"
    sql += " ORDER BY sort_order ASC, id ASC"
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


def create_payment_method(
    owner_id: int,
    provider: str,
    account_name: str,
    account_number_masked: str,
    qr_image_url: str,
    instructions: str = "",
    sort_order: int = 0,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO owner_payment_methods
            (owner_id, provider, account_name, account_number_masked,
             qr_image_url, instructions, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            provider.strip(),
            account_name.strip(),
            account_number_masked.strip(),
            qr_image_url.strip(),
            instructions.strip(),
            sort_order,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM owner_payment_methods WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def set_payment_method_active(owner_id: int, method_id: int, active: bool) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE owner_payment_methods SET active = ? WHERE id = ? AND owner_id = ?",
        (int(active), method_id, owner_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM owner_payment_methods WHERE id = ?", (method_id,))
    return dict(cursor.fetchone())


def delete_payment_method(owner_id: int, method_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM owner_payment_methods WHERE id = ? AND owner_id = ?",
        (method_id, owner_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def create_order(
    table: dict,
    items: list[dict],
    customer_note: str = "",
    payment_method_id: int | None = None,
    payment_reference: str = "",
) -> dict:
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

    payment_label = "Pay at cashier"
    payment_status = "unpaid"
    selected_payment_id = None
    if payment_method_id is not None:
        owner_id = table.get("owner_id")
        if owner_id is None:
            raise ValueError("Online payment is not configured for this table.")
        cursor.execute(
            """
            SELECT id, provider, account_name
            FROM owner_payment_methods
            WHERE id = ? AND owner_id = ? AND active = 1
            """,
            (payment_method_id, owner_id),
        )
        method = cursor.fetchone()
        if not method:
            raise ValueError("Selected payment QR is unavailable.")
        selected_payment_id = int(method["id"])
        payment_label = method["provider"]
        if method["account_name"]:
            payment_label += f" · {method['account_name']}"
        payment_status = "pending"

    try:
        cursor.execute(
            """
            INSERT INTO restaurant_orders
                (table_id, order_number, customer_note, total, owner_id,
                 payment_method_id, payment_method_label, payment_reference, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                table["id"], order_number, customer_note.strip(), total,
                table.get("owner_id"), selected_payment_id, payment_label,
                payment_reference.strip(), payment_status,
            ),
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


def set_order_payment_proof(order_id: int, proof_url: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE restaurant_orders
        SET payment_proof_url = ?, payment_status = 'pending', updated_at = datetime('now')
        WHERE id = ? AND payment_status <> 'verified' AND status <> 'cancelled'
        """,
        (proof_url.strip(), order_id),
    )
    conn.commit()
    return get_order_by_id(order_id)


def update_payment_status(order_id: int, status: str) -> dict | None:
    if status not in {"unpaid", "pending", "verified", "rejected"}:
        raise ValueError("Invalid payment status.")
    conn = get_connection()
    cursor = conn.cursor()
    verified_at = "datetime('now')" if status == "verified" else "NULL"
    cursor.execute(
        f"""
        UPDATE restaurant_orders
        SET payment_status = ?, payment_verified_at = {verified_at}, updated_at = datetime('now')
        WHERE id = ? AND payment_status <> 'verified' AND status <> 'cancelled'
        """,
        (status, order_id),
    )
    conn.commit()
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


def list_orders(status: str | None = None, owner_id: int | None = None) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    sql = """
        SELECT o.*, t.name AS table_name
        FROM restaurant_orders o
        JOIN restaurant_tables t ON t.id = o.table_id
    """
    params: list = []
    clauses = []
    if status:
        clauses.append("o.status = ?")
        params.append(status)
    if owner_id is not None:
        clauses.append("t.owner_id = ?")
        params.append(owner_id)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
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
        WHERE id = ? AND (? <> 'cancelled' OR payment_status <> 'verified')
        """,
        (status, order_id, status),
    )
    changed = cursor.rowcount
    conn.commit()
    if not changed:
        return get_order_by_id(order_id), "invalid_transition"
    return get_order_by_id(order_id), None


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:60] or "restaurant")


def _owner_dict(row) -> dict:
    data = dict(row)
    try:
        data["hero_images"] = json.loads(data.get("hero_images") or "[]")
    except Exception:
        data["hero_images"] = []
    if not isinstance(data["hero_images"], list):
        data["hero_images"] = []
    if not data.get("slug"):
        data["slug"] = f"r{data['id']}"
    data["public_path"] = f"/r/{data['slug']}"
    data.setdefault("logo_url", "")
    data.setdefault("about_text", "")
    data.setdefault("slideshow_style", "fade")
    try:
        data["custom_design"] = json.loads(data.get("custom_design") or "{}")
    except Exception:
        data["custom_design"] = {}
    return data


def _unique_slug(base: str, owner_id: int | None = None) -> str:
    cursor = get_connection().cursor()
    slug = _slugify(base)
    candidate = slug
    n = 2
    while True:
        if owner_id is None:
            cursor.execute("SELECT id FROM owners WHERE slug = ?", (candidate,))
        else:
            cursor.execute(
                "SELECT id FROM owners WHERE slug = ? AND id != ?",
                (candidate, owner_id),
            )
        if cursor.fetchone() is None:
            return candidate
        candidate = f"{slug}-{n}"
        n += 1


def request_email_code(email: str) -> dict:
    """Create confirmation number for owner signup/login. No password."""
    from app.mail import generate_code, otp_expiry_iso, send_confirmation_email, smtp_configured

    email = _normalize_email(email)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Enter a valid email address.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT created_at FROM email_otps
        WHERE email = ?
        ORDER BY id DESC LIMIT 1
        """,
        (email,),
    )
    last = cursor.fetchone()
    if last:
        try:
            created = datetime.fromisoformat(last["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - created).total_seconds() < 45:
                raise ValueError("Please wait a moment before requesting another code.")
        except ValueError:
            raise
        except Exception:
            pass

    code = generate_code()
    cursor.execute(
        """
        INSERT INTO email_otps (email, code, expires_at)
        VALUES (?, ?, ?)
        """,
        (email, code, otp_expiry_iso()),
    )
    conn.commit()
    send_confirmation_email(email, code)
    result = {
        "ok": True,
        "email": email,
        "message": "Confirmation number sent. Check your email inbox.",
        "smtp_configured": smtp_configured(),
    }
    # Local/dev helper when SMTP is not configured yet.
    if not smtp_configured():
        result["dev_code"] = code
        result["message"] = (
            "SMTP is not set up yet. Use the confirmation number shown on screen "
            "(also printed in the server console)."
        )
    return result


def verify_email_code(email: str, code: str) -> dict:
    """Verify confirmation number and return/create owner account."""
    email = _normalize_email(email)
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError("Enter the 6-digit confirmation number.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, code, expires_at FROM email_otps
        WHERE email = ?
        ORDER BY id DESC LIMIT 1
        """,
        (email,),
    )
    row = cursor.fetchone()
    if row is None or row["code"] != code:
        raise ValueError("Incorrect confirmation number.")

    from datetime import timezone as tz

    try:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise ValueError("Confirmation number expired. Request a new one.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Confirmation number expired. Request a new one.") from exc

    cursor.execute("DELETE FROM email_otps WHERE email = ?", (email,))
    cursor.execute("SELECT * FROM owners WHERE email = ?", (email,))
    owner = cursor.fetchone()
    is_new = owner is None
    if is_new:
        default_name = email.split("@")[0].replace(".", " ").title() + "'s Kitchen"
        slug = _unique_slug(default_name)
        cursor.execute(
            """
            INSERT INTO owners (email, restaurant_name, slug, about_text, hero_images)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                email,
                default_name[:80],
                slug,
                "Fresh food. Fast table ordering. Built in minutes.",
                "[]",
            ),
        )
        owner_id = cursor.lastrowid
        cursor.execute("SELECT * FROM owners WHERE id = ?", (owner_id,))
        owner = cursor.fetchone()
    else:
        owner_dict = _owner_dict(owner)
        if not owner["slug"]:
            slug = _unique_slug(owner_dict["restaurant_name"], owner["id"])
            cursor.execute("UPDATE owners SET slug = ? WHERE id = ?", (slug, owner["id"]))
            cursor.execute("SELECT * FROM owners WHERE id = ?", (owner["id"],))
            owner = cursor.fetchone()
    conn.commit()
    return {"owner": _owner_dict(owner), "is_new": is_new}


def get_or_create_owner_by_email(email: str) -> dict:
    """Return or create an owner after an identity provider verified the email."""
    email = _normalize_email(email)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("A valid verified email is required.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM owners WHERE email = ?", (email,))
    owner = cursor.fetchone()
    is_new = owner is None
    if is_new:
        default_name = email.split("@")[0].replace(".", " ").title() + "'s Kitchen"
        cursor.execute(
            """INSERT INTO owners (email, restaurant_name, slug, about_text, hero_images)
               VALUES (?, ?, ?, ?, ?)""",
            (email, default_name[:80], _unique_slug(default_name),
             "Fresh food. Fast table ordering. Built in minutes.", "[]"),
        )
        cursor.execute("SELECT * FROM owners WHERE id = ?", (cursor.lastrowid,))
        owner = cursor.fetchone()
    elif not owner["slug"]:
        owner_data = _owner_dict(owner)
        cursor.execute("UPDATE owners SET slug = ? WHERE id = ?", (_unique_slug(owner_data["restaurant_name"], owner["id"]), owner["id"]))
        cursor.execute("SELECT * FROM owners WHERE id = ?", (owner["id"],))
        owner = cursor.fetchone()
    conn.commit()
    return {"owner": _owner_dict(owner), "is_new": is_new}


def get_owner(owner_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM owners WHERE id = ?", (owner_id,))
    row = cursor.fetchone()
    if not row:
        return None
    data = _owner_dict(row)
    if not row["slug"]:
        slug = _unique_slug(data["restaurant_name"], owner_id)
        cursor.execute("UPDATE owners SET slug = ? WHERE id = ?", (slug, owner_id))
        get_connection().commit()
        data["slug"] = slug
        data["public_path"] = f"/r/{slug}"
    return data


def get_owner_by_slug(slug: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM owners WHERE slug = ?", (slug.strip().lower(),))
    row = cursor.fetchone()
    return _owner_dict(row) if row else None


def update_owner_site(
    owner_id: int,
    *,
    restaurant_name: str | None = None,
    about_text: str | None = None,
    logo_url: str | None = None,
    hero_images: list[str] | None = None,
    slideshow_style: str | None = None,
    custom_design: dict | None = None,
) -> dict | None:
    owner = get_owner(owner_id)
    if owner is None:
        return None
    conn = get_connection()
    cursor = conn.cursor()

    name = owner["restaurant_name"]
    if restaurant_name is not None:
        name = restaurant_name.strip()
        if not name:
            raise ValueError("Restaurant name is required.")
        name = name[:80]

    about = owner.get("about_text") or ""
    if about_text is not None:
        about = about_text.strip()[:500]

    logo = owner.get("logo_url") or ""
    if logo_url is not None:
        logo = logo_url.strip()[:500]

    heroes = owner.get("hero_images") or []
    if hero_images is not None:
        heroes = [str(url).strip() for url in hero_images if str(url).strip()][:20]

    style = owner.get("slideshow_style") or "fade"
    if slideshow_style is not None:
        style = slideshow_style.strip().lower()
        if style not in {"fade", "slide", "zoom", "split", "kenburns", "flip", "curtain", "blur", "rotate", "diagonal"}:
            raise ValueError("Invalid slideshow style.")

    design = owner.get("custom_design") or {}
    if custom_design is not None:
        encoded_design = json.dumps(custom_design, separators=(",", ":"))
        if len(encoded_design) > 500_000:
            raise ValueError("Design is too large.")
        design = custom_design

    slug = owner.get("slug") or _unique_slug(name, owner_id)
    if restaurant_name is not None:
        slug = _unique_slug(name, owner_id)

    cursor.execute(
        """
        UPDATE owners
        SET restaurant_name = ?, about_text = ?, logo_url = ?, hero_images = ?, slideshow_style = ?, custom_design = ?, slug = ?
        WHERE id = ?
        """,
        (name, about, logo, json.dumps(heroes), style, json.dumps(design, separators=(",", ":")), slug, owner_id),
    )
    conn.commit()
    return get_owner(owner_id)


def update_owner_restaurant_name(owner_id: int, restaurant_name: str) -> dict | None:
    return update_owner_site(owner_id, restaurant_name=restaurant_name)


def list_owner_menu(owner_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, category, name, description, price, image_url, available, owner_id
        FROM restaurant_menu_items
        WHERE owner_id = ?
        ORDER BY category ASC, name ASC
        """,
        (owner_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def set_owner_menu_item_image(owner_id: int, item_id: int, image_url: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE restaurant_menu_items
        SET image_url = ?
        WHERE id = ? AND owner_id = ?
        """,
        (image_url.strip(), item_id, owner_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_owner_menu_item(owner_id: int, item_id: int) -> bool:
    """Delete an owner's menu item; order lines keep their saved name and price."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM restaurant_menu_items WHERE id = ? AND owner_id = ?",
        (item_id, owner_id),
    )
    deleted = cursor.rowcount > 0
    if deleted:
        conn.commit()
    return deleted


def create_owner_menu_item(
    owner_id: int,
    category: str,
    name: str,
    description: str,
    price: float,
    image_url: str = "",
) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM restaurant_menu_items
        WHERE owner_id = ? AND LOWER(name) = LOWER(?)
        """,
        (owner_id, name.strip()),
    )
    if cursor.fetchone():
        return None
    cursor.execute(
        """
        INSERT INTO restaurant_menu_items
            (category, name, description, price, image_url, owner_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            category.strip(),
            name.strip(),
            description.strip(),
            round(price, 2),
            image_url.strip(),
            owner_id,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_owner_tables(owner_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, name, access_code, active, created_at, owner_id, qr_caption
        FROM restaurant_tables
        WHERE owner_id = ? AND active = 1
        ORDER BY id ASC
        """,
        (owner_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def create_owner_table(owner_id: int, name: str, qr_caption: str = "") -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM restaurant_tables
        WHERE owner_id = ? AND LOWER(name) = LOWER(?) AND active = 1
        """,
        (owner_id, name.strip()),
    )
    if cursor.fetchone():
        return None
    caption = (qr_caption or "").strip()[:120]
    cursor.execute(
        """
        SELECT id FROM restaurant_tables
        WHERE owner_id = ? AND LOWER(name) = LOWER(?) AND active = 0
        ORDER BY id DESC LIMIT 1
        """,
        (owner_id, name.strip()),
    )
    archived = cursor.fetchone()
    if archived:
        table_id = archived["id"]
        cursor.execute(
            """
            UPDATE restaurant_tables
            SET active = 1, access_code = ?, qr_caption = ?
            WHERE id = ? AND owner_id = ?
            """,
            (secrets.token_urlsafe(8), caption, table_id, owner_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM restaurant_tables WHERE id = ?", (table_id,))
        return dict(cursor.fetchone())
    cursor.execute(
        """
        INSERT INTO restaurant_tables (name, access_code, owner_id, qr_caption)
        VALUES (?, ?, ?, ?)
        """,
        (name.strip(), secrets.token_urlsafe(8), owner_id, caption),
    )
    conn.commit()
    cursor.execute("SELECT * FROM restaurant_tables WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def update_owner_table_qr_caption(owner_id: int, table_id: int, qr_caption: str) -> dict | None:
    text = (qr_caption or "").strip()
    if len(text) > 120:
        raise ValueError("QR text is too long (max 120 characters).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE restaurant_tables
        SET qr_caption = ?
        WHERE id = ? AND owner_id = ? AND active = 1
        """,
        (text, table_id, owner_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute(
        """
        SELECT id, name, access_code, active, created_at, owner_id, qr_caption
        FROM restaurant_tables
        WHERE id = ? AND owner_id = ?
        """,
        (table_id, owner_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def archive_owner_table(owner_id: int, table_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE restaurant_tables
        SET active = 0
        WHERE id = ? AND owner_id = ? AND active = 1
        """,
        (table_id, owner_id),
    )
    changed = cursor.rowcount > 0
    if changed:
        conn.commit()
    return changed


def list_table_messages(table_id: int, after_id: int = 0) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT m.id, m.table_id, m.sender, m.body, m.image_url, m.created_at,
               m.reply_to_id, m.reaction, r.body AS reply_body, r.sender AS reply_sender
        FROM table_messages m
        LEFT JOIN table_messages r ON r.id = m.reply_to_id AND r.table_id = m.table_id
        WHERE m.table_id = ? AND m.id > ?
        ORDER BY m.id ASC
        """,
        (table_id, after_id),
    )
    return [dict(row) for row in cursor.fetchall()]


def add_table_message(
    table_id: int,
    sender: str,
    body: str = "",
    reply_to_id: int | None = None,
    image_url: str = "",
) -> dict:
    text = (body or "").strip()
    image = (image_url or "").strip()

    if not text and not image:
        raise ValueError("Message cannot be empty.")
    if len(text) > 500:
        raise ValueError("Message is too long (max 500 characters).")
    if len(image) > 500:
        raise ValueError("Image URL is too long.")
    if sender not in {"customer", "cashier"}:
        raise ValueError("Invalid sender.")

    conn = get_connection()
    cursor = conn.cursor()

    if reply_to_id is not None:
        cursor.execute(
            "SELECT id FROM table_messages WHERE id = ? AND table_id = ?",
            (reply_to_id, table_id),
        )
        if cursor.fetchone() is None:
            raise ValueError("Reply message not found.")

    cursor.execute(
        """
        INSERT INTO table_messages (table_id, sender, body, reply_to_id, image_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (table_id, sender, text, reply_to_id, image),
    )
    conn.commit()
    cursor.execute("SELECT * FROM table_messages WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def update_table_message(table_id: int, message_id: int, sender: str, body: str) -> dict | None:
    text = (body or "").strip()
    if not text:
        raise ValueError("Message cannot be empty.")
    if len(text) > 500:
        raise ValueError("Message is too long (max 500 characters).")
    if sender not in {"customer", "cashier"}:
        raise ValueError("Invalid sender.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE table_messages SET body = ?
        WHERE id = ? AND table_id = ? AND sender = ?
        """,
        (text, message_id, table_id, sender),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM table_messages WHERE id = ?", (message_id,))
    return dict(cursor.fetchone())


def delete_table_message(table_id: int, message_id: int, sender: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM table_messages WHERE id = ? AND table_id = ? AND sender = ?",
        (message_id, table_id, sender),
    )
    deleted = cursor.rowcount > 0
    if deleted:
        conn.commit()
    return deleted


def set_table_message_reaction(table_id: int, message_id: int, reaction: str) -> dict | None:
    value = (reaction or "").strip()[:8]
    allowed = {"", "👍", "❤️", "😂", "😮", "😢", "🙏"}
    if value not in allowed:
        raise ValueError("Invalid reaction.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE table_messages SET reaction = ? WHERE id = ? AND table_id = ?",
        (value, message_id, table_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    cursor.execute("SELECT * FROM table_messages WHERE id = ?", (message_id,))
    return dict(cursor.fetchone())


def list_message_threads() -> list[dict]:
    """Cashier inbox: one row per table that has messages, newest activity first."""
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT
            t.id AS table_id,
            t.name AS table_name,
            t.access_code,
            (
                SELECT body FROM table_messages m
                WHERE m.table_id = t.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_body,
            (
                SELECT sender FROM table_messages m
                WHERE m.table_id = t.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_sender,
            (
                SELECT created_at FROM table_messages m
                WHERE m.table_id = t.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_at,
            (
                SELECT COUNT(*) FROM table_messages m
                WHERE m.table_id = t.id AND m.sender = 'customer'
                  AND m.id > COALESCE((
                      SELECT MAX(id) FROM table_messages c
                      WHERE c.table_id = t.id AND c.sender = 'cashier'
                  ), 0)
            ) AS unread_from_customer
        FROM restaurant_tables t
        WHERE t.active = 1
          AND EXISTS (SELECT 1 FROM table_messages m WHERE m.table_id = t.id)
        ORDER BY last_at DESC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def get_table_by_id(table_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, name, access_code, active, owner_id
        FROM restaurant_tables
        WHERE id = ?
        """,
        (table_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None

ROOM_TYPES = ("kitchen", "warehouse", "bar", "custom")


def _enrich_room(row: dict) -> dict:
    data = dict(row)
    custom = (data.get("qr_caption") or "").strip()
    data["qr_caption"] = custom
    default = get_settings().get("qr_caption") or "Scan QR to connect"
    if data.get("room_type") == "kitchen" and not custom:
        data["display_caption"] = "Scan to join Kitchen chat"
    elif data.get("room_type") == "warehouse" and not custom:
        data["display_caption"] = "Scan to join Warehouse chat"
    elif data.get("room_type") == "bar" and not custom:
        data["display_caption"] = "Scan to join Bar chat"
    else:
        data["display_caption"] = custom or default
    return data


def list_ops_rooms(active_only: bool = True) -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    sql = """
        SELECT id, name, access_code, room_type, qr_caption, active, created_at
        FROM ops_rooms
    """
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id ASC"
    cursor.execute(sql)
    return [_enrich_room(dict(row)) for row in cursor.fetchall()]


def create_ops_room(name: str, room_type: str = "custom", qr_caption: str = "") -> dict | None:
    room_type = (room_type or "custom").strip().lower()
    if room_type not in ROOM_TYPES:
        raise ValueError("Room type must be kitchen, warehouse, bar, or custom.")
    text_name = name.strip()
    if not text_name:
        raise ValueError("Room name is required.")
    caption = (qr_caption or "").strip()[:120]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM ops_rooms WHERE LOWER(name) = LOWER(?)",
        (text_name,),
    )
    if cursor.fetchone():
        return None
    cursor.execute(
        """
        INSERT INTO ops_rooms (name, access_code, room_type, qr_caption)
        VALUES (?, ?, ?, ?)
        """,
        (text_name, secrets.token_urlsafe(8), room_type, caption),
    )
    conn.commit()
    return get_ops_room_by_id(cursor.lastrowid)


def get_ops_room_by_id(room_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM ops_rooms WHERE id = ?", (room_id,))
    row = cursor.fetchone()
    return _enrich_room(dict(row)) if row else None


def get_ops_room_by_code(access_code: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM ops_rooms
        WHERE access_code = ? AND active = 1
        """,
        (access_code.strip(),),
    )
    row = cursor.fetchone()
    return _enrich_room(dict(row)) if row else None


def update_ops_room_caption(room_id: int, qr_caption: str) -> dict | None:
    text = (qr_caption or "").strip()
    if len(text) > 120:
        raise ValueError("QR text is too long (max 120 characters).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ops_rooms SET qr_caption = ? WHERE id = ?",
        (text, room_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    return get_ops_room_by_id(room_id)


def list_room_messages(room_id: int, after_id: int = 0) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, room_id, sender, sender_name, body, created_at
        FROM room_messages
        WHERE room_id = ? AND id > ?
        ORDER BY id ASC
        """,
        (room_id, after_id),
    )
    return [dict(row) for row in cursor.fetchall()]


def add_room_message(
    room_id: int, sender: str, body: str, sender_name: str = ""
) -> dict:
    text = (body or "").strip()
    if not text:
        raise ValueError("Message cannot be empty.")
    if len(text) > 500:
        raise ValueError("Message is too long (max 500 characters).")
    if sender not in {"cashier", "member"}:
        raise ValueError("Invalid sender.")
    name = (sender_name or "").strip()[:40]
    if sender == "member" and not name:
        name = "Staff"
    if sender == "cashier":
        name = name or "Cashier"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO room_messages (room_id, sender, sender_name, body)
        VALUES (?, ?, ?, ?)
        """,
        (room_id, sender, name, text),
    )
    conn.commit()
    cursor.execute("SELECT * FROM room_messages WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_ops_room_threads() -> list[dict]:
    ensure_defaults()
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT
            r.id AS room_id,
            r.name AS room_name,
            r.room_type,
            r.access_code,
            (
                SELECT body FROM room_messages m
                WHERE m.room_id = r.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_body,
            (
                SELECT sender FROM room_messages m
                WHERE m.room_id = r.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_sender,
            (
                SELECT sender_name FROM room_messages m
                WHERE m.room_id = r.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_sender_name,
            (
                SELECT created_at FROM room_messages m
                WHERE m.room_id = r.id
                ORDER BY m.id DESC LIMIT 1
            ) AS last_at,
            (
                SELECT COUNT(*) FROM room_messages m
                WHERE m.room_id = r.id AND m.sender = 'member'
                  AND m.id > COALESCE((
                      SELECT MAX(id) FROM room_messages c
                      WHERE c.room_id = r.id AND c.sender = 'cashier'
                  ), 0)
            ) AS unread_from_members
        FROM ops_rooms r
        WHERE r.active = 1
        ORDER BY COALESCE(last_at, r.created_at) DESC, r.id DESC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def update_owner_menu_item(owner_id: int, item_id: int, *, category: str, name: str,
                           description: str, price: float, image_url: str = "") -> dict | None:
    conn = get_connection()
    if not conn.execute("SELECT id FROM restaurant_menu_items WHERE id=? AND owner_id=?", (item_id, owner_id)).fetchone():
        return None
    if conn.execute("SELECT id FROM restaurant_menu_items WHERE owner_id=? AND LOWER(name)=LOWER(?) AND id<>?", (owner_id, name.strip(), item_id)).fetchone():
        raise ValueError("A menu item with that name already exists.")
    conn.execute("UPDATE restaurant_menu_items SET category=?, name=?, description=?, price=?, image_url=? WHERE id=? AND owner_id=?",
                 (category.strip(), name.strip(), description.strip(), round(price, 2), image_url.strip(), item_id, owner_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM restaurant_menu_items WHERE id=?", (item_id,)).fetchone())


def list_table_bills() -> list[dict]:
    from decimal import Decimal
    cursor = get_connection().cursor()
    cursor.execute("""SELECT o.*, t.name AS table_name FROM restaurant_orders o
        JOIN restaurant_tables t ON t.id = o.table_id
        WHERE NOT EXISTS (SELECT 1 FROM closed_bill_orders b WHERE b.order_id = o.id)
        ORDER BY o.table_id, o.id""")
    grouped = {}
    for row in cursor.fetchall():
        order = dict(row)
        bill = grouped.setdefault(order["table_id"], {
            "table_id": order["table_id"], "table_name": order["table_name"], "orders": []})
        bill["orders"].append(order)
    for bill in grouped.values():
        chargeable = [o for o in bill["orders"] if o["status"] != "cancelled"]
        total = sum((Decimal(str(o["total"])) for o in chargeable), Decimal(0))
        paid = sum((Decimal(str(o["total"])) for o in chargeable if o["payment_status"] == "verified"), Decimal(0))
        bill.update(total=float(total), paid=float(paid), balance=float(total-paid))
        bill["can_close"] = all(o["status"] == "cancelled" or
            (o["status"] == "served" and o["payment_status"] == "verified") for o in bill["orders"])
    return list(grouped.values())


def settle_table_orders(table_id: int, order_ids: list[int]) -> dict:
    # A single conditional UPDATE makes retries and simultaneous cashiers idempotent.
    ids = sorted(set(order_ids))
    placeholders = ",".join("?" for _ in ids)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""UPDATE restaurant_orders
        SET payment_status = 'verified', payment_verified_at = datetime('now'),
            updated_at = datetime('now')
        WHERE table_id = ? AND id IN ({placeholders}) AND status <> 'cancelled'
          AND payment_status <> 'verified'
          AND NOT EXISTS (SELECT 1 FROM closed_bill_orders b WHERE b.order_id = restaurant_orders.id)
        RETURNING id, total""", (table_id, *ids))
    rows = cursor.fetchall()
    conn.commit()
    from decimal import Decimal
    return {"paid_order_ids": [r["id"] for r in rows],
            "amount_recorded": float(sum((Decimal(str(r["total"])) for r in rows), Decimal(0)))}


def close_table_bill(table_id: int, order_ids: list[int]) -> dict:
    # Only the displayed, fully settled orders close; newly arriving orders stay open.
    ids = sorted(set(order_ids))
    placeholders = ",".join("?" for _ in ids)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""INSERT INTO closed_bill_orders (order_id, closed_at)
        SELECT o.id, datetime('now') FROM restaurant_orders o
        WHERE o.table_id = ? AND o.id IN ({placeholders})
          AND (o.status = 'cancelled' OR (o.status = 'served' AND o.payment_status = 'verified'))
          AND NOT EXISTS (SELECT 1 FROM restaurant_orders x WHERE x.table_id = ?
              AND x.id IN ({placeholders}) AND x.status <> 'cancelled'
              AND (x.status <> 'served' OR x.payment_status <> 'verified'))
        ON CONFLICT (order_id) DO NOTHING""", (table_id, *ids, table_id, *ids))
    count = cursor.rowcount
    conn.commit()
    return {"closed_orders": count}
