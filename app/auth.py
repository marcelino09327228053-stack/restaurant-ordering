"""Cashier and owner authentication helpers."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "restaurant-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token() -> str:
    payload = {
        "sub": "cashier",
        "role": "cashier",
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_owner_token(owner_id: int, email: str) -> str:
    payload = {
        "sub": f"owner:{owner_id}",
        "role": "owner",
        "owner_id": owner_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        return jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc


def require_cashier(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    payload = _decode(credentials)
    if payload.get("role") != "cashier" and payload.get("sub") != "cashier":
        raise HTTPException(status_code=401, detail="Invalid token.")


def require_owner(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    payload = _decode(credentials)
    if payload.get("role") != "owner" or not payload.get("owner_id"):
        raise HTTPException(status_code=401, detail="Owner login required.")
    return payload


def require_pos(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Accept an existing owner session or the separate staff cashier session."""
    payload = _decode(credentials)
    if payload.get("role") == "owner":
        from app.repository import get_owner

        payload = require_owner(credentials)
        if get_owner(payload["owner_id"]) is None:
            raise HTTPException(status_code=401, detail="Owner login required.")
        return payload
    require_cashier(credentials)
    return payload
