"""ReCircle Device Passport — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.api.routes.events import router as events_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create database tables on startup (dev convenience)."""

    if settings.environment.lower() == "test":
        yield
        return

    # Import models so Base.metadata knows about them
    import app.models.entities  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created / verified.")
    yield


app = FastAPI(
    title="ReCircle Device Passport API",
    description=(
        "On-chain event logging for the e-waste circular economy platform. "
        "Every device lifecycle event is permanently recorded on Polygon."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(events_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}
