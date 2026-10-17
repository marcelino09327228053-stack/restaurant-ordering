"""FastAPI entrypoint for restaurant table ordering."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import repository as repo
from app.auth import require_owner
from app.cloudinary_routes import _cloudinary_configured, router as cloudinary_router
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
    conn = get_connection()
    if using_postgres():
        conn.execute("ALTER TABLE restaurant_menu_items ADD COLUMN IF NOT EXISTS background_color TEXT NOT NULL DEFAULT '#17171b'")
    else:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(restaurant_menu_items)")}
        if "background_color" not in columns:
            conn.execute("ALTER TABLE restaurant_menu_items ADD COLUMN background_color TEXT NOT NULL DEFAULT '#17171b'")
    conn.commit()
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
            SELECT id, category, name, description, price, image_url, background_color, available, owner_id
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
        background_color: str = "#17171b",
    ) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        clean_name = name.strip()

        existing = cursor.execute(
            """
            SELECT id
            FROM restaurant_menu_items
            WHERE owner_id = ? AND LOWER(name) = LOWER(?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (owner_id, clean_name),
        ).fetchone()

        if existing:
            item_id = existing["id"]
            cursor.execute(
                """
                UPDATE restaurant_menu_items
                SET category = ?, name = ?, description = ?, price = ?,
                    image_url = ?, background_color = ?, available = 1
                WHERE id = ? AND owner_id = ?
                """,
                (
                    category.strip(), clean_name, description.strip(), round(price, 2),
                    image_url.strip(), background_color, item_id, owner_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO restaurant_menu_items
                    (category, name, description, price, image_url, background_color, owner_id, available)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    category.strip(), clean_name, description.strip(), round(price, 2),
                    image_url.strip(), background_color, owner_id,
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
        background_color: str = "#17171b",
    ) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        clean_name = name.strip()
        cursor.execute(
            """
            UPDATE restaurant_menu_items
            SET category = ?, name = ?, description = ?, price = ?, image_url = ?, background_color = ?, available = 1
            WHERE id = ? AND owner_id = ?
            """,
            (
                category.strip(), clean_name, description.strip(), round(price, 2),
                image_url.strip(), background_color, item_id, owner_id,
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

    @application.get("/phone-order")
    async def phone_order_page():
        return FileResponse(
            "phone-order.html",
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
        tables_tabs_patch = """
        <style id="mb-native-table-tabs-style">
          #tablesPanel { width:min(760px,calc(100% - 32px)) !important; max-width:760px !important; left:50% !important; right:auto !important; transform:translateX(-50%) !important; }
          #mbNativeTableTabs { display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:4px; margin:0 0 16px; border:1px solid #ffffff1f; border-radius:12px; background:#0d1015; position:sticky; top:0; z-index:50; }
          #mbNativeTableTabs button { min-height:44px; border:1px solid transparent; border-radius:9px; background:transparent; color:#aeb4bd; font-weight:800; cursor:pointer; }
          #mbNativeTableTabs button.active { color:#fff; background:#f97316; border-color:#fb923c; box-shadow:0 6px 20px #f9731626; }
          #mbNativeTableTabs button:not(.active):hover { color:#fff; background:#ffffff08; }
          .mb-native-table-pane[hidden] { display:none !important; }
          .mb-native-table-pane { width:100%; }
          #mbNativePaymentPane .block { border:0 !important; box-shadow:none !important; padding:0 !important; margin:0 !important; }
          #tablePaymentSection { display:none !important; }
        </style>
        <script id="mb-native-table-tabs-script">
          (function () {
            function installTablesTabs() {
              const body = document.getElementById("tablesPanelBody");
              const paymentBody = document.getElementById("paymentsPanelBody");
              const paymentSection = document.getElementById("tablePaymentSection");
              if (!body || !paymentBody || !paymentSection) {
                setTimeout(installTablesTabs, 150);
                return;
              }
              if (document.getElementById("mbNativeTableTabs")) return;

              document.querySelectorAll("#mbDirectTableTabs,#mbTableTabs").forEach(function (node) { node.remove(); });
              const tabs = document.createElement("div");
              tabs.id = "mbNativeTableTabs";
              tabs.setAttribute("role", "tablist");
              tabs.innerHTML = '<button type="button" class="active" data-tab="tables" role="tab" aria-selected="true">Table & QR</button><button type="button" data-tab="payment" role="tab" aria-selected="false">Payment</button>';

              const tablePane = document.createElement("section");
              tablePane.id = "mbNativeTablePane";
              tablePane.className = "mb-native-table-pane";
              const paymentPane = document.createElement("section");
              paymentPane.id = "mbNativePaymentPane";
              paymentPane.className = "mb-native-table-pane";
              paymentPane.hidden = true;

              Array.from(body.children).forEach(function (child) {
                if (child !== paymentSection && child !== tabs) tablePane.appendChild(child);
              });
              paymentPane.appendChild(paymentBody);
              paymentSection.remove();
              body.replaceChildren(tabs, tablePane, paymentPane);

              function selectTab(name) {
                const payment = name === "payment";
                tablePane.hidden = payment;
                paymentPane.hidden = !payment;
                tabs.querySelectorAll("button").forEach(function (button) {
                  const active = button.dataset.tab === name;
                  button.classList.toggle("active", active);
                  button.setAttribute("aria-selected", String(active));
                });
                body.scrollTop = 0;
              }
              tabs.querySelector('[data-tab="tables"]').addEventListener("click", function () { selectTab("tables"); });
              tabs.querySelector('[data-tab="payment"]').addEventListener("click", function () { selectTab("payment"); });
              window.mbSelectTablesTab = selectTab;
              selectTab("tables");
            }

            window.addEventListener("load", function () {
              setTimeout(installTablesTabs, 0);
              setTimeout(installTablesTabs, 500);
              setTimeout(installTablesTabs, 1200);
            });
            document.addEventListener("DOMContentLoaded", function () { setTimeout(installTablesTabs, 0); });
          })();
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
            'button.disabled = true;\
        document.getElementById("menuPhotoHint").textContent = "Uploading photo…";',
            'button.disabled = true;\
        button.textContent = "Uploading photo…";\
        document.getElementById("menuPhotoHint").textContent = "Uploading photo… please wait";\
        document.getElementById("menuFeedback").textContent = "Please wait for the photo upload to finish before adding the menu item.";',
            1,
        )
        html = html.replace(
            'document.getElementById("menuPhotoHint").textContent = "photo ready ✓";\
          toast("Dish photo ready — fill details & add.", true);',
            'document.getElementById("menuPhotoHint").textContent = "photo ready ✓";\
          document.getElementById("menuFeedback").textContent = "Photo ready. You can add the menu item now.";\
          toast("Dish photo ready — fill details & add.", true);',
            1,
        )
        html = html.replace(
            'if (kind === "menu") document.getElementById("addMenuButton").disabled = false;',
            'if (kind === "menu") {\
          const menuButton = document.getElementById("addMenuButton");\
          menuButton.disabled = false;\
          menuButton.textContent = editingMenuId ? "Save changes" : "Add to menu";\
        }',
            1,
        )
        html = html.replace(
            '        await api(editingMenuId ? `/api/owner/menu/${editingMenuId}` : "/api/owner/menu", {',
            '        const savedItem = await api(editingMenuId ? `/api/owner/menu/${editingMenuId}` : "/api/owner/menu", {',
            1,
        )
        html = html.replace(
            '        menu = await api("/api/owner/menu");\
        renderMenuList();',
            '        const savedIndex = menu.findIndex(item => item.id === savedItem.id);\
        if (savedIndex >= 0) menu[savedIndex] = savedItem;\
        else menu.push(savedItem);\
        renderMenuList();\
        setTimeout(async () => {\
          try {\
            menu = await api("/api/owner/menu");\
            renderMenuList();\
          } catch (_) {}\
        }, 800);',
            1,
        )
        html = html.replace("</head>", f"{boot_guard}{tables_tabs_patch}</head>", 1)
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
            "custom_design": {k: v for k, v in (owner.get("custom_design") or {}).items() if k != "editorDraft"},
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
                    f"Business: {data.get('restaurant_name') or 'MB Business Hub'}\
A full logout was requested from a signed-in device.",
                )
            except Exception as exc:
                print(f"[SECURITY EMAIL ERROR] {exc}")
        return {"ok": True}

    @application.get("/r/{slug}")
    async def restaurant_storefront(slug: str):
        html = Path("storefront.html").read_text(encoding="utf-8")
        slideshow_public_patch = """
        <style id="mb-placed-slideshow-style">
          .design-slideshow-live { position:absolute; overflow:hidden; border-radius:12px; background:#111; pointer-events:none; z-index:4; }
          .design-slideshow-live img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; opacity:0; transform:scale(1.04); transition:opacity .8s ease, transform 1s ease; }
          .design-slideshow-live img.on { opacity:1; transform:scale(1); }
          .design-slideshow-live.style-slide img { transform:translateX(100%); opacity:1; }
          .design-slideshow-live.style-slide img.on { transform:translateX(0); }
          .design-slideshow-live.style-zoom img { transform:scale(.78); }
          .design-slideshow-live.style-zoom img.on { transform:scale(1); }
          .design-slideshow-live.style-blur img { filter:blur(18px); transform:scale(1.08); }
          .design-slideshow-live.style-blur img.on { filter:blur(0); transform:scale(1); }
        </style>
        <script id="mb-placed-slideshow-script">
          window.renderPlacedSlideshow = function (design, images, style) {
            const wrap = document.getElementById("companyDesign");
            if (!wrap || !design?.enabled || !Array.isArray(design?.canvas?.objects)) return;
            wrap.querySelectorAll(".design-slideshow-live").forEach(el => el.remove());
            const object = design.canvas.objects.find(item => item.assetType === "slideshow");
            if (!object || !Array.isArray(images) || !images.length) return;
            const box = document.createElement("div");
            box.className = `design-slideshow-live style-${style || object.slideshowStyle || "fade"}`;
            const width = (Number(object.width) || 560) * (Number(object.scaleX) || 1);
            const height = (Number(object.height) || 250) * (Number(object.scaleY) || 1);
            box.style.left = `${((Number(object.left) || 0) / 900) * 100}%`;
            box.style.top = `${((Number(object.top) || 0) / 500) * 100}%`;
            box.style.width = `${(width / 900) * 100}%`;
            box.style.height = `${(height / 500) * 100}%`;
            box.style.transform = `rotate(${Number(object.angle) || 0}deg)`;
            box.style.transformOrigin = "center";
            images.forEach((url, index) => {
              const img = document.createElement("img");
              img.src = url;
              img.alt = "";
              if (index === 0) img.classList.add("on");
              box.appendChild(img);
            });
            wrap.appendChild(box);
            let index = 0;
            if (images.length > 1) {
              setInterval(() => {
                const slides = [...box.querySelectorAll("img")];
                slides[index]?.classList.remove("on");
                index = (index + 1) % slides.length;
                slides[index]?.classList.add("on");
              }, 3200);
            }
          };
        </script>
        """
        html = html.replace("</head>", f"{slideshow_public_patch}</head>", 1)
        html = html.replace(
            'canvas.getObjects().filter(obj => obj.assetType === "video").forEach(obj => {',
            'canvas.getObjects().filter(obj => obj.assetType === "slideshow").forEach(obj => canvas.remove(obj));\
        canvas.getObjects().filter(obj => obj.assetType === "video").forEach(obj => {',
            1,
        )
        html = html.replace(
            'renderCompanyDesign(data.custom_design);',
            'renderCompanyDesign(data.custom_design);\
        renderPlacedSlideshow(data.custom_design, data.hero_images || [], data.slideshow_style || "fade");',
            1,
        )
        html = html.replace(
            '        if (heroes.length) {',
            '        const hasPlacedSlideshow = !!data.custom_design?.canvas?.objects?.some(item => item.assetType === "slideshow");\
        if (heroes.length && !hasPlacedSlideshow) {',
            1,
        )
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
            },
        )

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

    # The Cloudinary and local routers expose the same upload URLs. Register
    # Cloudinary only when its credentials are available; otherwise the local
    # router below stores uploads under static/uploads during development.
    if _cloudinary_configured():
        application.include_router(cloudinary_router)
    application.include_router(router)
    init_db()
    prepare_owner_menu_storage()
    install_owner_menu_fixes()
    ensure_defaults()
    remove_legacy_sample_menu()
    return application


app = create_app()
