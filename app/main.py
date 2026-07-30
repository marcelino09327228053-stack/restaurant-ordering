"""FastAPI entrypoint for restaurant table ordering."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.db import init_db
from app.repository import ensure_defaults
from app.router import router


def create_app() -> FastAPI:
    application = FastAPI(title="Restaurant Ordering")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/")
    async def home():
        return FileResponse("login.html")

    @application.get("/login")
    async def login_page():
        return FileResponse("login.html")

    @application.get("/order")
    async def order_page():
        return FileResponse("order.html")

    @application.get("/cashier")
    async def cashier_page():
        return FileResponse("cashier.html")

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    application.include_router(router)
    init_db()
    ensure_defaults()
    return application


app = create_app()
