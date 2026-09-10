"""Email confirmation-number (OTP) helpers."""

import os
import random
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

OTP_MINUTES = int(os.getenv("OTP_MINUTES", "10"))
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@restaurant.local")
APP_NAME = os.getenv("RESTAURANT_NAME", "Bite & Brew Ordering")


def generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def otp_expiry_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=OTP_MINUTES)).isoformat()


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_confirmation_email(to_email: str, code: str) -> None:
    """Send confirmation number. Falls back to console when SMTP is not set."""
    subject = f"{APP_NAME} confirmation number"
    body = (
        f"Your confirmation number is: {code}\n\n"
        f"Enter this code on the website to open your menu setup.\n"
        f"It expires in {OTP_MINUTES} minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )

    if not smtp_configured():
        print(f"[DEV OTP] {to_email} -> {code}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
