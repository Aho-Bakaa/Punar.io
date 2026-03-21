"""Simple API-key protection for admin endpoints."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_admin_key(x_admin_key: str = Header(default="")) -> None:
    """Validate the admin API key via ``X-Admin-Key`` header."""

    if x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )
