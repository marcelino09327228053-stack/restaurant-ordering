"""FastAPI entrypoint for restaurant table ordering."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import repository as repo
from app.auth import require_owner
from app.cloudinary_routes import router as cloudinary_router
from app.db import get_connection, init_db, using_postgres
from app.mail import send_security_email
from app.repository import ensure_defaults
from app.router import router


LEGACY_SAMPLE_NAMES = {
    "Chicken Inasal",
    "Pork Sisig",
    "Beef Tapa",
    "Pancit Canton",
    "Iced Tea",
    "Leche Flan",
}


def without_legacy_samples(items: list[dict]) -> list[dict]:
    return [item for item in items if str(item.get("name") or "").strip() not in LEGACY_SAMPLE_NAMES]


def prepare_owner_menu_storage() -> None:
    """Allow repeated dish names while keeping owner scoping in application logic."""
    if not using_postgres():
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE restaurant_menu_items DROP CONSTRAINT IF EXISTS restaurant_menu_items_name_key")
    cursor.execute("DROP INDEX IF EXISTS idx_owner_menu_name_unique")
    conn.commit()


def install_owner_menu_fixes() -> None:
    """Provide reliable owner-scoped add/edit/delete behavior."""

    def list_owner_menu(owner_id: int) -> list[dict]:
        cursor = get_connection().cursor()
        cursor.execute(
            """
            SELECT id, category, name, description, price, image_url, available, owner_id
            FROM restaurant_menu_items
            WHERE owner_id = ? AND available = 1
            ORDER BY category ASC, name ASC, id ASC
            """,
            (owner_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

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
        clean_name = name.strip()
        cursor.execute(
            """
            INSERT INTO restaurant_menu_items
                (category, name, description, price, image_url, owner_id, available)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                category.strip(), clean_name, description.strip(), round(price, 2),
                image_url.strip(), owner_id,
            ),
        )
        item_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (item_id,))
        return dict(cursor.fetchone())

    def update_owner_menu_item(
        owner_id: int,
        item_id: int,
        *,
        category: str,
        name: str,
        description: str,
        price: float,
        image_url: str = "",
    ) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        clean_name = name.strip()
        cursor.execute(
            """
            UPDATE restaurant_menu_items
            SET category = ?, name = ?, description = ?, price = ?, image_url = ?, available = 1
            WHERE id = ? AND owner_id = ?
            """,
            (
                category.strip(), clean_name, description.strip(), round(price, 2),
                image_url.strip(), item_id, owner_id,
            ),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return None
        conn.commit()
        cursor.execute("SELECT * FROM restaurant_menu_items WHERE id = ?", (item_id,))
        return dict(cursor.fetchone())

    def delete_owner_menu_item(owner_id: int, item_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE restaurant_menu_items
            SET available = 0
            WHERE id = ? AND owner_id = ? AND available = 1
            """,
            (item_id, owner_id),
        )
        changed = cursor.rowcount > 0
        if changed:
            conn.commit()
        else:
            conn.rollback()
        return changed

    repo.list_owner_menu = list_owner_menu
    repo.create_owner_menu_item = create_owner_menu_item
    repo.update_owner_menu_item = update_owner_menu_item
    repo.delete_owner_menu_item = delete_owner_menu_item


def remove_legacy_sample_menu() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    samples = (
        ("Rice Meals", "Chicken Inasal", "Grilled chicken, rice, and atchara", 149.0),
        ("Rice Meals", "Pork Sisig", "Sizzling pork sisig served with rice", 169.0),
        ("Rice Meals", "Beef Tapa", "Tender beef tapa, egg, and garlic rice", 179.0),
        ("Noodles", "Pancit Canton", "Stir-fried noodles with vegetables", 139.0),
        ("Drinks", "Iced Tea", "House-blended iced tea", 49.0),
        ("Desserts", "Leche Flan", "Creamy caramel custard", 79.0),
    )
    for category, name, description, price in samples:
        cursor.execute(
            """
            UPDATE restaurant_menu_items
            SET owner_id = NULL, available = 0
            WHERE owner_id IS NOT NULL
              AND category = ? AND name = ? AND description = ? AND price = ?
            """,
            (category, name, description, price),
        )
    conn.commit()


def create_app() -> FastAPI:
    application = FastAPI(title="MB Business Hub")

    os.makedirs("static", exist_ok=True)
    application.mount("/static", StaticFiles(directory="static"), name="static")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/")
    async def home():
        return FileResponse("home.html")

    @application.get("/account")
    async def account_page():
        return FileResponse("account.html")

    @application.get("/login")
    async def login_page():
        return FileResponse("login.html")

    @application.get("/order")
    async def order_page():
        html = Path("order.html").read_text(encoding="utf-8")
        order_cleanup = """
        <style id="mb-order-cleanup">
          .search { display: none !important; }
          #heroCta { display: none !important; }
        </style>
        """
        html = html.replace("</head>", f"{order_cleanup}</head>", 1)
        html = html.replace(
            'document.title = `${data.restaurant_name} — Order`;',
            'document.title = "MB Business Hub — Order";',
            1,
        )
        html = html.replace(
            'document.getElementById("brandName").textContent = data.restaurant_name;',
            'document.getElementById("brandName").textContent = "MB Business Hub";',
            1,
        )
        html = html.replace(
            'document.getElementById("sheetTable").textContent = `${data.table_name} · ${data.restaurant_name}`;',
            'document.getElementById("sheetTable").textContent = `${data.table_name} · MB Business Hub`;',
            1,
        )
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
            },
        )

    @application.get("/cashier")
    async def cashier_page():
        return FileResponse("cashier.html")

    @application.get("/owner")
    async def owner_page():
        html = Path("owner.html").read_text(encoding="utf-8")
        boot_guard = """
        <style id="owner-studio-boot-guard">
          body > .top,
          body > .shell { display: none !important; }
          .design-top h2 {
            cursor: pointer;
            user-select: none;
            border-radius: 10px;
            padding: 7px 9px;
            margin-left: -9px;
          }
          .design-top h2:hover,
          .design-top h2:focus-visible {
            background: #ffffff0d;
            outline: 1px solid #ffffff18;
          }
        </style>
        <script>
          if (localStorage.getItem("owner_locked") === "1") {
            location.replace("/account?unlock=1");
          } else {
            document.addEventListener("DOMContentLoaded", function () {
              const title = document.querySelector(".design-top h2");
              if (title) {
                title.setAttribute("role", "button");
                title.setAttribute("tabindex", "0");
                title.setAttribute("aria-label", "Return to Design Your Page");
                const returnToDesign = function () {
                  document.querySelectorAll(".studio-panel").forEach(function (panel) { panel.hidden = true; });
                  const slideshow = document.getElementById("slideshowPanel");
                  if (slideshow) slideshow.hidden = true;
                  if (typeof closeEditorTool === "function") closeEditorTool();
                  if (typeof setCanvasToolsVisible === "function") setCanvasToolsVisible(true);
                  if (typeof syncTopToolbar === "function") syncTopToolbar();
                  if (typeof fitDesignBoard === "function") requestAnimationFrame(fitDesignBoard);
                };
                title.addEventListener("click", returnToDesign);
                title.addEventListener("keydown", function (event) {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    returnToDesign();
                  }
                });
              }
            });
          }
          window.sendMenuPreviewTheme = window.sendMenuPreviewTheme || function () {};
        </script>
        """
        html = html.replace("<title>Site Builder</title>", "<title>Design Your Page · MB Business Hub</title>", 1)
        html = html.replace(
            '<button class="btn" id="menuPhonePreview" type="button" aria-pressed="false" onclick="toggleMenuPhonePreview()">Phone preview</button>',
            "",
            1,
        )
        html = html.replace(
            'document.getElementById("menuPhonePreview").setAttribute("aria-pressed","false");',
            "",
            1,
        )
        html = html.replace(
            'button.disabled = true;\n        document.getElementById("menuPhotoHint").textContent = "Uploading photo…";',
            'button.disabled = true;\n        button.textContent = "Uploading photo…";\n        document.getElementById("menuPhotoHint").textContent = "Uploading photo… please wait";\n        document.getElementById("menuFeedback").textContent = "Please wait for the photo upload to finish before adding the menu item.";',
            1,
        )
        html = html.replace(
            'document.getElementById("menuPhotoHint").textContent = "photo ready ✓";\n          toast("Dish photo ready — fill details & add.", true);',
            'document.getElementById("menuPhotoHint").textContent = "photo ready ✓";\n          document.getElementById("menuFeedback").textContent = "Photo ready. You can add the menu item now.";\n          toast("Dish photo ready — fill details & add.", true);',
            1,
        )
        html = html.replace(
            'if (kind === "menu") document.getElementById("addMenuButton").disabled = false;',
            'if (kind === "menu") {\n          const menuButton = document.getElementById("addMenuButton");\n          menuButton.disabled = false;\n          menuButton.textContent = editingMenuId ? "Save changes" : "Add to menu";\n        }',
            1,
        )
        html = html.replace(
            '        await api(editingMenuId ? `/api/owner/menu/${editingMenuId}` : "/api/owner/menu", {',
            '        const savedItem = await api(editingMenuId ? `/api/owner/menu/${editingMenuId}` : "/api/owner/menu", {',
            1,
        )
        html = html.replace(
            '        menu = await api("/api/owner/menu");\n        renderMenuList();',
            '        const savedIndex = menu.findIndex(item => item.id === savedItem.id);\n        if (savedIndex >= 0) menu[savedIndex] = savedItem;\n        else menu.push(savedItem);\n        renderMenuList();\n        setTimeout(async () => {\n          try {\n            menu = await api("/api/owner/menu");\n            renderMenuList();\n          } catch (_) {}\n        }, 800);',
            1,
        )
        html = html.replace("</head>", f"{boot_guard}</head>", 1)
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
            },
        )

    @application.get("/api/owner/me")
    async def owner_me_guard(owner=Depends(require_owner)):
        data = repo.get_owner(owner["owner_id"])
        if data is None:
            raise HTTPException(status_code=401, detail="Owner session is stale. Please log in again.")
        return data

    @application.get("/api/owner/menu")
    async def owner_menu_without_samples(owner=Depends(require_owner)):
        return without_legacy_samples(repo.list_owner_menu(owner["owner_id"]))

    @application.get("/api/public/site/{slug}")
    async def public_site_without_samples(slug: str):
        owner = repo.get_owner_by_slug(slug)
        if owner is None:
            raise HTTPException(status_code=404, detail="Restaurant page not found.")
        menu = without_legacy_samples(repo.list_owner_menu(owner["id"]))
        tables = repo.list_owner_tables(owner["id"])
        return {
            "restaurant_name": owner["restaurant_name"],
            "slug": owner["slug"],
            "logo_url": owner.get("logo_url") or "",
            "about_text": owner.get("about_text") or "",
            "hero_images": owner.get("hero_images") or [],
            "custom_design": repo.public_design(owner.get("custom_design")),
            "slideshow_style": owner.get("slideshow_style") or "fade",
            "menu": menu,
            "tables": tables,
        }

    @application.get("/api/public/{access_code}/menu")
    async def public_table_menu_without_samples(access_code: str):
        table = repo.get_public_table(access_code)
        if table is None:
            raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
        owner_id = table.get("owner_id")
        items = repo.list_owner_menu(owner_id) if owner_id is not None else repo.list_menu(available_only=True)
        items = without_legacy_samples(items)
        return {
            "restaurant_name": table["restaurant_name"],
            "table_name": table["name"],
            "banner": ((repo.get_owner(owner_id) or {}).get("custom_design", {}).get("bannerPublished") if owner_id is not None else None),
            "menu_theme": ((repo.get_owner(owner_id) or {}).get("custom_design", {}).get("menuTheme", {}) if owner_id is not None else {}),
            "items": items,
            "payment_methods": repo.list_payment_methods(owner_id, active_only=True) if owner_id is not None else [],
        }

    @application.post("/api/owner/logout-notify")
    async def owner_logout_notify(owner=Depends(require_owner)):
        data = repo.get_owner(owner["owner_id"])
        if data is None:
            raise HTTPException(status_code=401, detail="Owner session is stale. Please log in again.")
        email = str(data.get("email") or owner.get("email") or "").strip()
        if email:
            try:
                send_security_email(
                    email,
                    "Owner account logged out",
                    f"Business: {data.get('restaurant_name') or 'MB Business Hub'}\nA full logout was requested from a signed-in device.",
                )
            except Exception as exc:
                print(f"[SECURITY EMAIL ERROR] {exc}")
        return {"ok": True}

    @application.get("/r/{slug}")
    async def restaurant_storefront(slug: str):
        return FileResponse("storefront.html")

    @application.get("/table-qrcodes")
    async def table_qrcodes_page():
        return FileResponse("table-qrcodes.html")

    @application.get("/qr-generator")
    async def qr_generator_page():
        return FileResponse("qr-generator.html")

    @application.get("/join/{access_code}")
    async def join_room_page(access_code: str):
        return FileResponse("join.html")

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    application.include_router(cloudinary_router)
    application.include_router(router)
    init_db()
    prepare_owner_menu_storage()
    install_owner_menu_fixes()
    ensure_defaults()
    remove_legacy_sample_menu()
    return application


app = create_app()
