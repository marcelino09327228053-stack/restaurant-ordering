"""FastAPI entrypoint for restaurant table ordering."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.cloudinary_routes import router as cloudinary_router
from app.db import init_db
from app.repository import ensure_defaults
from app.router import router


def create_app() -> FastAPI:
    application = FastAPI(title="Restaurant Ordering")

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
        return FileResponse("order.html")

    @application.get("/login")
    async def login_page():
        return FileResponse("login.html")

    @application.get("/order")
    async def order_page():
        return FileResponse("order.html")

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
        </style>
        """
        cleanup_script = '<script src="/static/owner-ui-cleanup.js"></script>'
        html = html.replace("</head>", f"{boot_guard}</head>", 1)
        html = html.replace("</body>", f"{cleanup_script}</body>", 1)
        return HTMLResponse(html)

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
