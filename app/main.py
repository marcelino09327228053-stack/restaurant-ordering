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
from app.db import init_db
from app.mail import send_security_email
from app.repository import ensure_defaults
from app.router import router


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
        # Keep legacy controls because the studio moves and reuses them. Hide the
        # old shell during boot, and add the small navigation compatibility layer
        # without duplicating the large owner editor file.
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
          // A locked owner session stays on the device, but the editor cannot be
          // reopened until the owner verifies the account again.
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

          // Compatibility guard for the legacy iframe onload handler. The owner
          // page references this name even in builds where the helper is absent.
          window.sendMenuPreviewTheme = window.sendMenuPreviewTheme || function () {};
        </script>
        """
        html = html.replace("<title>Site Builder</title>", "<title>Design Your Page · MB Business Hub</title>", 1)
        html = html.replace(
            '<button class="btn" id="menuPhonePreview" type="button" aria-pressed="false" onclick="toggleMenuPhonePreview()">Phone preview</button>',
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

    # This route is intentionally registered before app.router's /api/owner/me.
    # A stale owner JWT can survive a database migration and still decode even
    # though its owner row no longer exists. Return 401 so the existing frontend
    # clears that token and sends the user through owner login again.
    @application.get("/api/owner/me")
    async def owner_me_guard(owner=Depends(require_owner)):
        data = repo.get_owner(owner["owner_id"])
        if data is None:
            raise HTTPException(status_code=401, detail="Owner session is stale. Please log in again.")
        return data

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
                # Never trap the user in a session because email delivery failed.
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

    # Register persistent Cloudinary upload routes before the legacy local-file
    # routes so Render uses Cloudinary while the rest of the API remains unchanged.
    application.include_router(cloudinary_router)
    application.include_router(router)
    init_db()
    ensure_defaults()
    return application


app = create_app()
