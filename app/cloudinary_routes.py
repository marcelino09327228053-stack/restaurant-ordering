"""Cloudinary-backed upload routes for persistent media storage."""

import io
import os

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app import repository as repo
from app.menu_editor import validate_menu_upload
from app.auth import require_owner

router = APIRouter(prefix="/api", tags=["restaurant-media"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def _cloudinary_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in (
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
        )
    )


def _configure_cloudinary() -> None:
    if not _cloudinary_configured():
        raise HTTPException(status_code=503, detail="Media storage is not configured.")
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"].strip(),
        api_key=os.environ["CLOUDINARY_API_KEY"].strip(),
        api_secret=os.environ["CLOUDINARY_API_SECRET"].strip(),
        secure=True,
    )


def _upload(raw: bytes, *, folder: str, resource_type: str = "image") -> str:
    _configure_cloudinary()
    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(raw),
            folder=folder,
            resource_type=resource_type,
            unique_filename=True,
            overwrite=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Media upload failed. Please try again.") from exc
    url = str(result.get("secure_url") or "")
    if not url:
        raise HTTPException(status_code=502, detail="Media upload failed. Please try again.")
    return url


@router.post("/owner/upload")
async def owner_upload_cloudinary(
    kind: str = Form(...),
    file: UploadFile = File(...),
    owner=Depends(require_owner),
):
    kind = (kind or "").strip().lower()
    if kind not in {"logo", "hero", "menu", "payment", "design", "design_video", "menu_display", "menu_video", "menu_background"}:
        raise HTTPException(status_code=400, detail="Invalid upload kind.")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    is_video = kind in {"design_video", "menu_video"}
    ext = VIDEO_TYPES.get(content_type) if is_video else ALLOWED_IMAGE_TYPES.get(content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported image or video format.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    max_bytes = None if is_video or kind in {"menu_display", "menu_background"} else MAX_UPLOAD_BYTES
    if max_bytes is not None and len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail="File is too large.")

    if kind in {"menu_display", "menu_video", "menu_background"}:
        validate_menu_upload(raw, content_type)

    owner_id = int(owner["owner_id"])
    site = repo.get_owner(owner_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Owner not found.")

    url = _upload(
        raw,
        folder=f"restaurant-ordering/{owner_id}/{kind}",
        resource_type="video" if is_video else "image",
    )

    if kind == "logo":
        site = repo.update_owner_site(owner_id, logo_url=url)
    elif kind == "hero":
        heroes = list(site.get("hero_images") or [])
        heroes.append(url)
        site = repo.update_owner_site(owner_id, hero_images=heroes[:20])

    return {"url": url, "owner": site}


@router.post("/public/{access_code}/orders/{order_number}/payment-proof")
async def upload_payment_proof_cloudinary(
    access_code: str,
    order_number: str,
    file: UploadFile = File(...),
):
    order = repo.get_public_order(access_code, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Payment proof must be JPG, PNG, WEBP, or GIF.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty payment proof.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Payment proof is too large (max 8MB).")

    url = _upload(raw, folder=f"restaurant-ordering/payments/{order['id']}")
    return repo.set_order_payment_proof(order["id"], url)
