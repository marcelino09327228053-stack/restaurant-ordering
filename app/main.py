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
from app.db import get_connection, init_db
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


def remove_legacy_sample_menu() -> None:
    """Detach only the original six seeded demo dishes from owner menus.

    Keeping the rows preserves any historical order-line foreign keys while
    owner/customer menu queries stop showing these legacy samples.
    """
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
            "custom_design": owner.get("custom_design") or {},
            "slideshow_style": owner.get("slideshow_style") or "fade",
            "menu": [item for item in menu if item.get("available")],
            "tables": tables,
        }

    @application.get("/api/public/{access_code}/menu")
    async def public_table_menu_without_samples(access_code: str):
        table = repo.get_public_table(access_code)
        if table is None:
            raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
        owner_id = table.get("owner_id")
        items = repo.list_owner_menu(owner_id) if owner_id is not None else repo.list_menu(available_only=True)
        items = [item for item in without_legacy_samples(items) if item.get("available")]
        return {
            "restaurant_name": table["restaurant_name"],
            "table_name": table["name"],
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
    ensure_defaults()
    remove_legacy_sample_menu()
    return application


app = create_app()
