"""Detect local LAN URLs so table QR codes work without internet."""

from __future__ import annotations

import os
import socket
from urllib.parse import urlsplit


def preferred_lan_ip() -> str:
    """Best guess at this machine's WiFi / LAN IPv4 address."""
    forced = (os.getenv("PUBLIC_BASE_URL") or os.getenv("LAN_IP") or "").strip()
    if forced:
        if "://" in forced:
            host = forced.split("://", 1)[1].split("/", 1)[0]
            return host.split(":")[0]
        return forced.split(":")[0]

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.168.0.1", 1))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    return "127.0.0.1"


def connection_info(port: int | None = None) -> dict:
    port = int(port or os.getenv("PORT", "8030"))
    public_base = (os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    if public_base:
        parsed = urlsplit(public_base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("PUBLIC_BASE_URL must be a full http:// or https:// URL.")
        return {
            "mode": "online", "base_url": public_base,
            "lan_ip": parsed.hostname, "port": parsed.port or (443 if parsed.scheme == "https" else 80),
            "lan_base": public_base, "local_base": f"http://127.0.0.1:{port}",
            "offline_ready": False,
            "hint": "Online website: customers can scan using mobile data or any Wi-Fi with internet.",
        }
    lan_ip = preferred_lan_ip()
    lan_base = f"http://{lan_ip}:{port}"
    local_base = f"http://127.0.0.1:{port}"
    return {
        "mode": "local", "base_url": lan_base,
        "lan_ip": lan_ip,
        "port": port,
        "lan_base": lan_base,
        "local_base": local_base,
        "offline_ready": not lan_ip.startswith("127."),
        "hint": (
            "Phones must join the same WiFi as this computer. "
            "No internet needed - only the local restaurant network."
            if not lan_ip.startswith("127.")
            else "Could not detect WiFi IP. Open cashier via your PC's LAN IP, or set LAN_IP in .env."
        ),
    }


def table_order_url(access_code: str, port: int | None = None) -> str:
    base = connection_info(port)["lan_base"].rstrip("/")
    return f"{base}/order?table={access_code}"


def room_join_url(access_code: str, port: int | None = None) -> str:
    base = connection_info(port)["lan_base"].rstrip("/")
    return f"{base}/join/{access_code}"
