"""API routes for customer ordering and cashier board."""

import io
import json
import os
import re
from pathlib import Path
from uuid import uuid4

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app import repository as repo
from app.menu_editor import MenuAppearance, validate_menu_upload
from app.auth import create_access_token, create_owner_token, require_cashier, require_owner
from app.mail import smtp_configured
from app.network import connection_info, room_join_url, table_order_url

router = APIRouter(prefix="/api", tags=["restaurant"])
UPLOAD_ROOT = Path("static/uploads")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@router.get("/connection")
def lan_connection():
    """LAN base URL for QR codes (same Wi‑Fi works without internet)."""
    return connection_info()


@router.get("/qr")
def qr_code(data: str | None = None, table: str | None = None, room: str | None = None):
    """Generate a QR image. Prefer table= or room= so URL uses LAN IP."""
    if room:
        payload = room_join_url(room.strip())
    elif table:
        payload = table_order_url(table.strip())
    elif data:
        payload = data
    else:
        raise HTTPException(status_code=400, detail="Provide room=, table=, or data=.")
    if len(payload) > 512:
        raise HTTPException(status_code=400, detail="Invalid QR data.")
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#111827", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class EmailStartRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)


class EmailVerifyRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    code: str = Field(min_length=6, max_length=6)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=5000)


class OwnerNameUpdate(BaseModel):
    restaurant_name: str = Field(min_length=1, max_length=80)


class OwnerSiteUpdate(BaseModel):
    restaurant_name: str | None = Field(default=None, min_length=1, max_length=80)
    about_text: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    hero_images: list[str] | None = None
    slideshow_style: str | None = Field(default=None, max_length=20)
    custom_design: dict | None = None


class OrderItemCreate(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)
    customer_note: str = Field(default="", max_length=500)
    payment_method_id: int | None = Field(default=None, gt=0)
    payment_reference: str = Field(default="", max_length=120)


class StatusUpdate(BaseModel):
    status: str


class MenuItemCreate(BaseModel):
    background_color: str = Field(default="#17171b", pattern=r"^#[0-9a-fA-F]{6}$")
    category: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    price: float = Field(gt=0, le=1_000_000)
    image_url: str = Field(default="", max_length=500)


class AvailabilityUpdate(BaseModel):
    available: bool


class ImageUpdate(BaseModel):
    image_url: str = Field(default="", max_length=500)


class TableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    qr_caption: str = Field(default="", max_length=120)


class QrCaptionUpdate(BaseModel):
    qr_caption: str = Field(min_length=1, max_length=120)


class TableCaptionUpdate(BaseModel):
    qr_caption: str = Field(default="", max_length=120)


class TableMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=500)
    reply_to_id: int | None = None


class TableMessageReaction(BaseModel):
    reaction: str = Field(default="", max_length=8)


class OpsRoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    room_type: str = Field(default="custom", max_length=40)
    qr_caption: str = Field(default="", max_length=120)


class RoomMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=500)
    sender_name: str = Field(default="", max_length=40)


class PaymentMethodCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    account_name: str = Field(default="", max_length=120)
    account_number_masked: str = Field(default="", max_length=80)
    qr_image_url: str = Field(min_length=1, max_length=500)
    instructions: str = Field(default="", max_length=300)
    sort_order: int = Field(default=0, ge=0, le=10_000)


class PaymentMethodActiveUpdate(BaseModel):
    active: bool


class PaymentStatusUpdate(BaseModel):
    status: str


@router.post("/login")
def login(body: LoginRequest):
    if not repo.authenticate_cashier(body.password):
        raise HTTPException(status_code=401, detail="Incorrect cashier password.")
    return {"token": create_access_token(), "restaurant": repo.get_settings()}


@router.post("/auth/email/start")
def start_email_login(body: EmailStartRequest):
    try:
        return repo.request_email_code(body.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/email/verify")
def verify_email_login(body: EmailVerifyRequest):
    try:
        result = repo.verify_email_code(body.email, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    owner = result["owner"]
    token = create_owner_token(owner["id"], owner["email"])
    return {
        "token": token,
        "owner": owner,
        "is_new": result["is_new"],
        "smtp_configured": smtp_configured(),
    }


@router.get("/auth/google/config")
def google_login_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    return {"enabled": bool(client_id), "client_id": client_id}


@router.post("/auth/google")
def google_login(body: GoogleLoginRequest):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured yet.")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        identity = id_token.verify_oauth2_token(body.credential, google_requests.Request(), client_id)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google login could not be verified.") from exc
    email = str(identity.get("email") or "").strip().lower()
    if not email or not identity.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified.")
    result = repo.get_or_create_owner_by_email(email)
    owner = result["owner"]
    return {"token": create_owner_token(owner["id"], owner["email"]), "owner": owner, "is_new": result["is_new"]}


@router.get("/owner/me")
def owner_me(owner=Depends(require_owner)):
    data = repo.get_owner(owner["owner_id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Owner not found.")
    return data


@router.patch("/owner/me")
def owner_update_name(body: OwnerNameUpdate, owner=Depends(require_owner)):
    try:
        data = repo.update_owner_restaurant_name(owner["owner_id"], body.restaurant_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data is None:
        raise HTTPException(status_code=404, detail="Owner not found.")
    return data


@router.patch("/owner/site")
def owner_update_site(body: OwnerSiteUpdate, owner=Depends(require_owner)):
    try:
        data = repo.update_owner_site(
            owner["owner_id"],
            restaurant_name=body.restaurant_name,
            about_text=body.about_text,
            logo_url=body.logo_url,
            hero_images=body.hero_images,
            slideshow_style=body.slideshow_style,
            custom_design=body.custom_design,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data is None:
        raise HTTPException(status_code=404, detail="Owner not found.")
    return data


@router.patch("/owner/menu-appearance")
def save_menu_appearance(body: MenuAppearance, owner=Depends(require_owner)):
    site = repo.get_owner(owner["owner_id"])
    if site is None:
        raise HTTPException(404, "Owner not found.")
    design = dict(site.get("custom_design") or {})
    design["menuTheme"] = body.model_dump()
    return repo.update_owner_site(owner["owner_id"], custom_design=design)


@router.post("/owner/upload")
async def owner_upload(
    kind: str = Form(...),
    file: UploadFile = File(...),
    owner=Depends(require_owner),
):
    kind = (kind or "").strip().lower()
    if kind not in {"logo", "hero", "menu", "payment", "design", "design_video", "menu_display", "menu_video", "menu_background"}:
        raise HTTPException(status_code=400, detail="Invalid upload kind.")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    video_types = {"video/mp4": ".mp4", "video/webm": ".webm"}
    ext = video_types.get(content_type) if kind in {"design_video", "menu_video"} else ALLOWED_IMAGE_TYPES.get(content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported image or video format.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    max_bytes = None if kind in {"design_video", "menu_video", "menu_display", "menu_background"} else MAX_UPLOAD_BYTES
    if max_bytes is not None and len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail="File is too large.")

    if kind in {"menu_display", "menu_video", "menu_background"}:
        validate_menu_upload(raw, content_type)

    owner_id = int(owner["owner_id"])
    folder = UPLOAD_ROOT / str(owner_id)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{kind}-{uuid4().hex}{ext}"
    path = folder / filename
    path.write_bytes(raw)
    url = f"/static/uploads/{owner_id}/{filename}"

    site = repo.get_owner(owner_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Owner not found.")

    if kind == "logo":
        site = repo.update_owner_site(owner_id, logo_url=url)
    elif kind == "hero":
        heroes = list(site.get("hero_images") or [])
        heroes.append(url)
        site = repo.update_owner_site(owner_id, hero_images=heroes[:20])

    return {"url": url, "owner": site}


@router.get("/public/site/{slug}")
def public_site(slug: str):
    owner = repo.get_owner_by_slug(slug)
    if owner is None:
        raise HTTPException(status_code=404, detail="Restaurant page not found.")
    menu = repo.list_owner_menu(owner["id"])
    tables = repo.list_owner_tables(owner["id"])
    return {
        "restaurant_name": owner["restaurant_name"],
        "slug": owner["slug"],
        "logo_url": owner.get("logo_url") or "",
        "about_text": owner.get("about_text") or "",
        "hero_images": owner.get("hero_images") or [],
        "custom_design": {k: v for k, v in (owner.get("custom_design") or {}).items() if k != "editorDraft"},
        "slideshow_style": owner.get("slideshow_style") or "fade",
        "menu": [item for item in menu if item.get("available")],
        "tables": tables,
    }


@router.get("/owner/menu")
def owner_menu(owner=Depends(require_owner)):
    return repo.list_owner_menu(owner["owner_id"])


@router.post("/owner/menu", status_code=201)
def owner_add_menu(body: MenuItemCreate, owner=Depends(require_owner)):
    item = repo.create_owner_menu_item(
        owner["owner_id"],
        body.category,
        body.name,
        body.description,
        body.price,
        body.image_url,
        background_color=body.background_color,
    )
    if item is None:
        raise HTTPException(status_code=409, detail="A menu item with that name already exists.")
    return item


@router.patch("/owner/menu/{item_id}")
def owner_edit_menu(item_id: int, body: MenuItemCreate, owner=Depends(require_owner)):
    try:
        item = repo.update_owner_menu_item(owner["owner_id"], item_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.patch("/owner/menu/{item_id}/image")
def owner_set_menu_image(item_id: int, body: ImageUpdate, owner=Depends(require_owner)):
    item = repo.set_owner_menu_item_image(owner["owner_id"], item_id, body.image_url)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.delete("/owner/menu/{item_id}", status_code=204)
def owner_delete_menu_item(item_id: int, owner=Depends(require_owner)):
    if not repo.delete_owner_menu_item(owner["owner_id"], item_id):
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return Response(status_code=204)


@router.get("/owner/tables")
def owner_tables(owner=Depends(require_owner)):
    tables = repo.list_owner_tables(owner["owner_id"])
    for table in tables:
        table["order_url"] = table_order_url(table["access_code"])
        table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return tables


@router.post("/owner/tables", status_code=201)
def owner_add_table(body: TableCreate, owner=Depends(require_owner)):
    table = repo.create_owner_table(owner["owner_id"], body.name, body.qr_caption)
    if table is None:
        raise HTTPException(status_code=409, detail="A table with that name already exists.")
    table["order_url"] = table_order_url(table["access_code"])
    table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return table


@router.patch("/owner/tables/{table_id}/caption")
def owner_update_table_caption(
    table_id: int, body: TableCaptionUpdate, owner=Depends(require_owner)
):
    try:
        table = repo.update_owner_table_qr_caption(
            owner["owner_id"], table_id, body.qr_caption
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found.")
    table["order_url"] = table_order_url(table["access_code"])
    table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return table


@router.delete("/owner/tables/{table_id}", status_code=204)
def owner_delete_table(table_id: int, owner=Depends(require_owner)):
    if not repo.archive_owner_table(owner["owner_id"], table_id):
        raise HTTPException(status_code=404, detail="Table not found.")
    return Response(status_code=204)


@router.get("/owner/payment-methods")
def owner_payment_methods(owner=Depends(require_owner)):
    return repo.list_payment_methods(owner["owner_id"])


@router.post("/owner/payment-methods", status_code=201)
def owner_add_payment_method(body: PaymentMethodCreate, owner=Depends(require_owner)):
    return repo.create_payment_method(
        owner["owner_id"],
        body.provider,
        body.account_name,
        body.account_number_masked,
        body.qr_image_url,
        body.instructions,
        body.sort_order,
    )


@router.patch("/owner/payment-methods/{method_id}/active")
def owner_toggle_payment_method(
    method_id: int, body: PaymentMethodActiveUpdate, owner=Depends(require_owner)
):
    method = repo.set_payment_method_active(owner["owner_id"], method_id, body.active)
    if method is None:
        raise HTTPException(status_code=404, detail="Payment QR not found.")
    return method


@router.delete("/owner/payment-methods/{method_id}", status_code=204)
def owner_delete_payment_method(method_id: int, owner=Depends(require_owner)):
    if not repo.delete_payment_method(owner["owner_id"], method_id):
        raise HTTPException(status_code=404, detail="Payment QR not found.")
    return Response(status_code=204)


@router.get("/public/{access_code}/menu")
def public_menu(access_code: str):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    return {
        "restaurant_name": table["restaurant_name"],
        "table_name": table["name"],
        "menu_theme": ((repo.get_owner(table["owner_id"]) or {}).get("custom_design", {}).get("menuTheme", {}) if table.get("owner_id") else {}),
        "items": repo.list_menu(available_only=True),
        "payment_methods": (
            repo.list_payment_methods(table["owner_id"], active_only=True)
            if table.get("owner_id") is not None
            else []
        ),
    }


@router.post("/public/{access_code}/orders", status_code=201)
def place_order(access_code: str, body: OrderCreate):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    try:
        return repo.create_order(
            table,
            [item.model_dump() for item in body.items],
            body.customer_note,
            body.payment_method_id,
            body.payment_reference,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/public/{access_code}/orders/{order_number}")
def public_order_status(access_code: str, order_number: str):
    order = repo.get_public_order(access_code, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.post("/public/{access_code}/orders/{order_number}/payment-proof")
async def upload_payment_proof(
    access_code: str,
    order_number: str,
    file: UploadFile = File(...),
):
    order = repo.get_public_order(access_code, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_IMAGE_TYPES.get(content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="Payment proof must be JPG, PNG, WEBP, or GIF.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty payment proof.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Payment proof is too large (max 8MB).")
    folder = UPLOAD_ROOT / "payments" / str(order["id"])
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"proof-{uuid4().hex}{ext}"
    path = folder / filename
    path.write_bytes(raw)
    return repo.set_order_payment_proof(
        order["id"], f"/static/uploads/payments/{order['id']}/{filename}"
    )


@router.get("/public/{access_code}/messages")
def public_list_messages(access_code: str, after_id: int = 0):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    return {
        "table_id": table["id"],
        "table_name": table["name"],
        "menu_theme": ((repo.get_owner(table["owner_id"]) or {}).get("custom_design", {}).get("menuTheme", {}) if table.get("owner_id") else {}),
        "messages": repo.list_table_messages(table["id"], after_id=max(0, after_id)),
    }


@router.post("/public/{access_code}/messages", status_code=201)
def public_send_message(access_code: str, body: TableMessageCreate):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    try:
        return repo.add_table_message(table["id"], "customer", body.body, body.reply_to_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/public/{access_code}/messages/image", status_code=201)
async def public_send_message_image(
    access_code: str,
    file: UploadFile = File(...),
    body: str = Form(""),
    reply_to_id: int | None = Form(None),
):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_IMAGE_TYPES.get(content_type)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Chat photo must be JPG, PNG, WEBP, or GIF.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Chat photo is too large (max 8MB).")

    folder = UPLOAD_ROOT / "chat" / str(table["id"])
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"chat-{uuid4().hex}{ext}"
    path = folder / filename
    path.write_bytes(raw)

    image_url = f"/static/uploads/chat/{table['id']}/{filename}"

    try:
        return repo.add_table_message(
            table["id"],
            "customer",
            body,
            reply_to_id,
            image_url=image_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/public/{access_code}/messages/{message_id}")
def public_edit_message(access_code: str, message_id: int, body: TableMessageCreate):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    try:
        message = repo.update_table_message(table["id"], message_id, "customer", body.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if message is None:
        raise HTTPException(status_code=404, detail="Customer message not found.")
    return message


@router.delete("/public/{access_code}/messages/{message_id}")
def public_delete_message(access_code: str, message_id: int):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    if not repo.delete_table_message(table["id"], message_id, "customer"):
        raise HTTPException(status_code=404, detail="Customer message not found.")
    return {"deleted": True}


@router.patch("/public/{access_code}/messages/{message_id}/reaction")
def public_react_to_message(access_code: str, message_id: int, body: TableMessageReaction):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    try:
        message = repo.set_table_message_reaction(table["id"], message_id, body.reaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    return message


@router.get("/messages/threads")
def cashier_message_threads(_=Depends(require_cashier)):
    return repo.list_message_threads()


@router.get("/tables/{table_id}/messages")
def cashier_list_messages(table_id: int, after_id: int = 0, _=Depends(require_cashier)):
    table = repo.get_table_by_id(table_id)
    if table is None or not table.get("active"):
        raise HTTPException(status_code=404, detail="Table not found.")
    return {
        "table_id": table["id"],
        "table_name": table["name"],
        "menu_theme": ((repo.get_owner(table["owner_id"]) or {}).get("custom_design", {}).get("menuTheme", {}) if table.get("owner_id") else {}),
        "messages": repo.list_table_messages(table_id, after_id=max(0, after_id)),
    }


@router.post("/tables/{table_id}/messages", status_code=201)
def cashier_send_message(
    table_id: int, body: TableMessageCreate, _=Depends(require_cashier)
):
    table = repo.get_table_by_id(table_id)
    if table is None or not table.get("active"):
        raise HTTPException(status_code=404, detail="Table not found.")
    try:
        return repo.add_table_message(table_id, "cashier", body.body, body.reply_to_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/tables/{table_id}/messages/{message_id}/reaction")
def cashier_react_to_message(
    table_id: int, message_id: int, body: TableMessageReaction, _=Depends(require_cashier)
):
    table = repo.get_table_by_id(table_id)
    if table is None or not table.get("active"):
        raise HTTPException(status_code=404, detail="Table not found.")
    try:
        message = repo.set_table_message_reaction(table_id, message_id, body.reaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    return message


@router.get("/orders")
def cashier_orders(status: str | None = None, _=Depends(require_cashier)):
    if status and status not in repo.ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status.")
    return repo.list_orders(status)


@router.patch("/orders/{order_id}/status")
def change_order_status(
    order_id: int, body: StatusUpdate, _=Depends(require_cashier)
):
    if body.status not in repo.ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status.")
    order, error = repo.update_order_status(order_id, body.status)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Order not found.")
    if error == "invalid_transition":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order from {order['status']} to {body.status}.",
        )
    return order


@router.patch("/orders/{order_id}/payment-status")
def change_payment_status(
    order_id: int, body: PaymentStatusUpdate, _=Depends(require_cashier)
):
    try:
        order = repo.update_payment_status(order_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.get("/menu")
def manage_menu(_=Depends(require_cashier)):
    return repo.list_menu()


@router.post("/menu", status_code=201)
def add_menu_item(body: MenuItemCreate, _=Depends(require_cashier)):
    item = repo.create_menu_item(
        body.category, body.name, body.description, body.price, body.image_url
    )
    if item is None:
        raise HTTPException(status_code=409, detail="A menu item with that name already exists.")
    return item


@router.patch("/menu/{item_id}/image")
def change_image(item_id: int, body: ImageUpdate, _=Depends(require_cashier)):
    item = repo.set_menu_item_image(item_id, body.image_url)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.patch("/menu/{item_id}/availability")
def change_availability(
    item_id: int, body: AvailabilityUpdate, _=Depends(require_cashier)
):
    item = repo.set_menu_item_availability(item_id, body.available)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.get("/tables")
def manage_tables(_=Depends(require_cashier)):
    info = connection_info()
    settings = repo.get_settings()
    tables = repo.list_tables()
    for table in tables:
        table["order_url"] = table_order_url(table["access_code"])
        table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return {"connection": info, "settings": settings, "tables": tables}


@router.post("/tables", status_code=201)
def add_table(body: TableCreate, _=Depends(require_cashier)):
    table = repo.create_table(body.name, body.qr_caption)
    if table is None:
        raise HTTPException(status_code=409, detail="A table with that name already exists.")
    table["order_url"] = table_order_url(table["access_code"])
    table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return table


@router.patch("/settings/qr-caption")
def update_default_qr_caption(body: QrCaptionUpdate, _=Depends(require_cashier)):
    try:
        return repo.update_qr_caption(body.qr_caption)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/tables/{table_id}/caption")
def update_table_caption(
    table_id: int, body: TableCaptionUpdate, _=Depends(require_cashier)
):
    try:
        table = repo.update_table_qr_caption(table_id, body.qr_caption)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found.")
    table["order_url"] = table_order_url(table["access_code"])
    table["qr_url"] = f"/api/qr?table={table['access_code']}"
    return table


def _decorate_room(room: dict) -> dict:
    room = dict(room)
    room["join_url"] = room_join_url(room["access_code"])
    room["qr_url"] = f"/api/qr?room={room['access_code']}"
    return room


@router.get("/rooms")
def cashier_list_rooms(_=Depends(require_cashier)):
    info = connection_info()
    settings = repo.get_settings()
    rooms = [_decorate_room(room) for room in repo.list_ops_rooms()]
    return {"connection": info, "settings": settings, "rooms": rooms}


@router.post("/rooms", status_code=201)
def cashier_create_room(body: OpsRoomCreate, _=Depends(require_cashier)):
    try:
        room = repo.create_ops_room(body.name, body.room_type, body.qr_caption)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if room is None:
        raise HTTPException(status_code=409, detail="A room with that name already exists.")
    return _decorate_room(room)


@router.patch("/rooms/{room_id}/caption")
def cashier_update_room_caption(
    room_id: int, body: TableCaptionUpdate, _=Depends(require_cashier)
):
    try:
        room = repo.update_ops_room_caption(room_id, body.qr_caption)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    return _decorate_room(room)


@router.get("/rooms/threads")
def cashier_room_threads(_=Depends(require_cashier)):
    return repo.list_ops_room_threads()


@router.get("/rooms/{room_id}/messages")
def cashier_room_messages(room_id: int, after_id: int = 0, _=Depends(require_cashier)):
    room = repo.get_ops_room_by_id(room_id)
    if room is None or not room.get("active"):
        raise HTTPException(status_code=404, detail="Room not found.")
    return {
        "room": _decorate_room(room),
        "messages": repo.list_room_messages(room_id, after_id=max(0, after_id)),
    }


@router.post("/rooms/{room_id}/messages", status_code=201)
def cashier_send_room_message(
    room_id: int, body: RoomMessageCreate, _=Depends(require_cashier)
):
    room = repo.get_ops_room_by_id(room_id)
    if room is None or not room.get("active"):
        raise HTTPException(status_code=404, detail="Room not found.")
    try:
        return repo.add_room_message(room_id, "cashier", body.body, "Cashier")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/public/rooms/{access_code}")
def public_room_info(access_code: str):
    room = repo.get_ops_room_by_code(access_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive room QR.")
    return {
        "id": room["id"],
        "name": room["name"],
        "room_type": room["room_type"],
        "display_caption": room["display_caption"],
        "restaurant_name": repo.get_settings()["restaurant_name"],
    }


@router.get("/public/rooms/{access_code}/messages")
def public_room_messages(access_code: str, after_id: int = 0):
    room = repo.get_ops_room_by_code(access_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive room QR.")
    return {
        "room_id": room["id"],
        "room_name": room["name"],
        "messages": repo.list_room_messages(room["id"], after_id=max(0, after_id)),
    }


@router.post("/public/rooms/{access_code}/messages", status_code=201)
def public_send_room_message(access_code: str, body: RoomMessageCreate):
    room = repo.get_ops_room_by_code(access_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive room QR.")
    try:
        return repo.add_room_message(
            room["id"], "member", body.body, body.sender_name or "Staff"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class TableBillSelection(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=1000)


@router.get("/table-bills")
def table_bills(_=Depends(require_cashier)):
    return repo.list_table_bills()


@router.post("/table-bills/{table_id}/pay")
def pay_table_bill(table_id: int, body: TableBillSelection, _=Depends(require_cashier)):
    return repo.settle_table_orders(table_id, body.order_ids)


@router.post("/table-bills/{table_id}/close")
def close_bill(table_id: int, body: TableBillSelection, _=Depends(require_cashier)):
    return repo.close_table_bill(table_id, body.order_ids)
