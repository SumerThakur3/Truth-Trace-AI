"""Normalize and build MySQL connection URLs for local dev and cloud hosts."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus, urlparse, urlunparse

from app.core.config import get_settings


def is_render() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def is_hosted_mysql_url(url: str) -> bool:
    patterns = ["aivencloud.com", "planetscale", "railway.app", "supabase", "render.com"]
    return any(p in url for p in patterns)


def resolve_database_url() -> str:
    """Return a clean mysql+aiomysql URL from env (supports Aiven/Render formats)."""
    settings = get_settings()
    url = (settings.database_url or "").strip()

    # Render: build from individual vars if DATABASE_URL still points to localhost
    if _is_localhost_url(url) and is_render():
        built = _build_from_mysql_parts()
        if built:
            return built

    if not url:
        built = _build_from_mysql_parts()
        if built:
            return built
        return "mysql+aiomysql://root:root@localhost:3306/truthtrace"

    return normalize_database_url(url)


def normalize_database_url(url: str) -> str:
    """Convert provider URLs to SQLAlchemy async aiomysql format."""
    url = url.strip()

    # Common Aiven / provider prefixes
    for prefix in (
        "mysql+aiomysql://",
        "mysql+pymysql://",
        "mysql://",
        "MYSQL://",
    ):
        if url.lower().startswith(prefix.lower()):
            if prefix.lower() == "mysql://":
                url = "mysql+aiomysql://" + url[len("mysql://") :]
            elif prefix == "MYSQL://":
                url = "mysql+aiomysql://" + url[len("MYSQL://") :]
            break

    parsed = urlparse(url)

    # Strip ?ssl-mode=REQUIRED etc. — SSL is configured via connect_args
    clean = urlunparse(
        (
            parsed.scheme or "mysql+aiomysql",
            parsed.netloc,
            parsed.path or "/defaultdb",
            "",
            "",
            "",
        )
    )

    if not clean.startswith("mysql+aiomysql://"):
        raise ValueError(
            "DATABASE_URL must use mysql+aiomysql:// scheme. "
            "Example: mysql+aiomysql://user:pass@host:port/defaultdb"
        )

    return clean


def _is_localhost_url(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


def _build_from_mysql_parts() -> str | None:
    """Build URL from MYSQL_HOST, MYSQL_USER, etc. (Render-friendly)."""
    host = os.getenv("MYSQL_HOST", "").strip()
    user = os.getenv("MYSQL_USER", "").strip()
    password = os.getenv("MYSQL_PASSWORD", "").strip()
    database = os.getenv("MYSQL_DATABASE", "defaultdb").strip() or "defaultdb"
    port = os.getenv("MYSQL_PORT", "3306").strip() or "3306"

    if not host or not user:
        return None

    safe_user = quote_plus(user)
    safe_pass = quote_plus(password)
    return f"mysql+aiomysql://{safe_user}:{safe_pass}@{host}:{port}/{database}"


def database_host_hint(url: str) -> str:
    """Safe host label for logs/health (no credentials)."""
    try:
        parsed = urlparse(url.replace("mysql+pymysql://", "mysql://").replace("mysql+aiomysql://", "mysql://"))
        return parsed.hostname or "unknown"
    except Exception:
        return "unknown"


@lru_cache
def get_resolved_db_url() -> str:
    return resolve_database_url()
