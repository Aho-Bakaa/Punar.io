"""Simple API-key protection for admin endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_admin_key(x_admin_key: str = Header(default="")) -> None:
    """Validate the admin API key via ``X-Admin-Key`` header."""

    if x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )


def require_event_key(wallet_role: str) -> Callable[..., None]:
    """Build a dependency that validates the role-specific event API key."""

    expected_key = settings.event_api_key_for_role(wallet_role)

    async def _require_key(x_actor_key: str = Header(default="")) -> None:
        if x_actor_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid actor key",
            )

    return _require_key
