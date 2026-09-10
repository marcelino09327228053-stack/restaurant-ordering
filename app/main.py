"""FastAPI entrypoint for restaurant table ordering."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
        return FileResponse("owner.html")

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

    application.include_router(router)
    init_db()
    ensure_defaults()
    return application


app = create_app()
