"""Device Passport event-logging API routes.

Eleven POST endpoints — one per lifecycle event — plus two GET endpoints
for verification and public device passports.

Each POST:
  1. Validates the payload via its Pydantic model.
  2. Inserts a ``DeviceEvent`` row (DB is source of truth).
  3. Fires ``blockchain_service.log_event()`` as a FastAPI background task
     so the blockchain write never blocks the API response.
  4. If the blockchain write fails, the error is captured into the
     ``blockchain_dead_letters`` table for manual retry.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import require_admin_key
from app.db.session import get_session
from app.models.entities import BlockchainDeadLetter, DeviceEvent
from app.schemas.dto import (
    BatchDispatchedPayload,
    DataWipedPayload,
    DeadLetterEntry,
    DeviceBatchedPayload,
    DeviceDroppedOffPayload,
    DeviceGradedPayload,
    DeviceListedPayload,
    DevicePassportResponse,
    DevicePickedUpPayload,
    DeviceRepairedPayload,
    DeviceSoldPayload,
    DeviceSubmittedPayload,
    EprCertificatePayload,
    EventResponse,
    PassportEventEntry,
    RecyclerAcknowledgedPayload,
    VerificationEventEntry,
    VerifyDeviceResponse,
)
from app.services.blockchain_service import BlockchainService
from app.utils.hashing import compute_payload_hash

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["events"])


# ────────────────────────────────────────────────────────────
#  Background task: blockchain write with dead-letter fallback
# ────────────────────────────────────────────────────────────

async def _blockchain_background(
    event_row_id: uuid.UUID,
    device_id: str,
    event_type: str,
    payload_dict: dict[str, Any],
    wallet_role: str | None,
    db_url: str,
) -> None:
    """Write the event on-chain and update the DB row with tx metadata.

    If the blockchain write fails after retries, log to the dead-letter
    queue so it can be manually retried by an admin.
    """

    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    from sqlalchemy.ext.asyncio import async_sessionmaker as _asm

    if settings.environment.lower() == "test":
        return

    engine = _cae(db_url, echo=False)
    session_factory = _asm(engine, expire_on_commit=False)

    try:
        chain = BlockchainService()
        tx_hash, data_hash = await chain.log_event(
            device_id, event_type, payload_dict, wallet_role
        )

        async with session_factory() as session:
            event_row = await session.get(DeviceEvent, event_row_id)
            if event_row:
                event_row.blockchain_tx_hash = tx_hash
                event_row.blockchain_hash = data_hash
                event_row.blockchain_logged_at = datetime.now(timezone.utc)
                await session.commit()

        logger.info(
            "Blockchain write succeeded for %s/%s — tx %s",
            device_id,
            event_type,
            tx_hash,
        )

    except Exception as exc:
        logger.error(
            "Blockchain write FAILED for %s/%s: %s", device_id, event_type, exc
        )
        # Write to dead-letter queue
        async with session_factory() as session:
            session.add(
                BlockchainDeadLetter(
                    device_id=device_id,
                    event_type=event_type,
                    payload_json=payload_dict,
                    wallet_role=wallet_role,
                    error_message=str(exc),
                    retry_count=3,
                    event_row_id=event_row_id,
                )
            )
            await session.commit()

    finally:
        await engine.dispose()


# ────────────────────────────────────────────────────────────
#  Helper: insert event → fire background blockchain task
# ────────────────────────────────────────────────────────────

async def _insert_and_log(
    device_id: str,
    event_type: str,
    payload_dict: dict[str, Any],
    wallet_role: str,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
) -> DeviceEvent:
    """Insert a DeviceEvent row and schedule the blockchain write."""

    actor_wallet: str | None = None
    try:
        chain = BlockchainService()
        actor_wallet = chain._resolve_account(wallet_role).address
    except Exception as exc:
        logger.warning(
            "Could not resolve actor wallet for role %s while queuing %s/%s: %s",
            wallet_role,
            device_id,
            event_type,
            exc,
        )

    event = DeviceEvent(
        device_id=device_id,
        event_type=event_type,
        payload_json=payload_dict,
        actor_wallet=actor_wallet,
        created_at=datetime.now(timezone.utc),
        blockchain_hash=compute_payload_hash(payload_dict),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    background_tasks.add_task(
        _blockchain_background,
        event.id,
        device_id,
        event_type,
        payload_dict,
        wallet_role,
        settings.database_url,
    )

    return event


def _event_response(event: DeviceEvent) -> EventResponse:
    status = "QUEUED"
    if event.blockchain_tx_hash:
        status = "CONFIRMED"
    return EventResponse(
        id=str(event.id),
        device_id=event.device_id,
        event_type=event.event_type,
        blockchain_status=status,
        created_at=event.created_at,
    )


# ════════════════════════════════════════════════════════════
#  EVENT ENDPOINTS (11 POSTs)
# ════════════════════════════════════════════════════════════


@router.post("/events/device-submitted", response_model=EventResponse)
async def device_submitted(
    payload: DeviceSubmittedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 1 — DEVICE_SUBMITTED. Actor: PLATFORM_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_SUBMITTED", payload.model_dump(),
        "PLATFORM_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-dropped-off", response_model=EventResponse)
async def device_dropped_off(
    payload: DeviceDroppedOffPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 2A — DEVICE_DROPPED_OFF. Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_DROPPED_OFF", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-picked-up", response_model=EventResponse)
async def device_picked_up(
    payload: DevicePickedUpPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 2B — DEVICE_PICKED_UP. Actor: AGENT_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_PICKED_UP", payload.model_dump(),
        "AGENT_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-graded", response_model=EventResponse)
async def device_graded(
    payload: DeviceGradedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 3 — DEVICE_GRADED. Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_GRADED", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/data-wiped", response_model=EventResponse)
async def data_wiped(
    payload: DataWipedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 4 — DATA_WIPED. Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DATA_WIPED", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-repaired", response_model=EventResponse)
async def device_repaired(
    payload: DeviceRepairedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 5 — DEVICE_REPAIRED (refurb track). Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_REPAIRED", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-listed", response_model=EventResponse)
async def device_listed(
    payload: DeviceListedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 6 — DEVICE_LISTED (refurb track). Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_LISTED", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-sold", response_model=EventResponse)
async def device_sold(
    payload: DeviceSoldPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 7 — DEVICE_SOLD (refurb track). Actor: PLATFORM_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_SOLD", payload.model_dump(),
        "PLATFORM_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/device-batched", response_model=EventResponse)
async def device_batched(
    payload: DeviceBatchedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 8 — DEVICE_BATCHED_FOR_RECYCLING (scrap track). Actor: PARTNER_WALLET."""
    event = await _insert_and_log(
        payload.device_id, "DEVICE_BATCHED_FOR_RECYCLING", payload.model_dump(),
        "PARTNER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/batch-dispatched", response_model=EventResponse)
async def batch_dispatched(
    payload: BatchDispatchedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 9 — BATCH_DISPATCHED_TO_RECYCLER (batch-level). Actor: PLATFORM_WALLET."""
    event = await _insert_and_log(
        payload.batch_id, "BATCH_DISPATCHED_TO_RECYCLER", payload.model_dump(),
        "PLATFORM_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/recycler-acknowledged", response_model=EventResponse)
async def recycler_acknowledged(
    payload: RecyclerAcknowledgedPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 10 — RECYCLER_ACKNOWLEDGED_RECEIPT (batch-level). Actor: RECYCLER_WALLET."""
    event = await _insert_and_log(
        payload.batch_id, "RECYCLER_ACKNOWLEDGED_RECEIPT", payload.model_dump(),
        "RECYCLER_WALLET", session, background_tasks,
    )
    return _event_response(event)


@router.post("/events/epr-certificate", response_model=EventResponse)
async def epr_certificate(
    payload: EprCertificatePayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """EVENT 11 — EPR_CERTIFICATE_ISSUED (batch-level). Actor: PLATFORM_WALLET."""
    event = await _insert_and_log(
        payload.batch_id, "EPR_CERTIFICATE_ISSUED", payload.model_dump(),
        "PLATFORM_WALLET", session, background_tasks,
    )
    return _event_response(event)


# ════════════════════════════════════════════════════════════
#  VERIFICATION ENDPOINT
# ════════════════════════════════════════════════════════════


@router.get("/verify/{device_id}", response_model=VerifyDeviceResponse)
async def verify_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> VerifyDeviceResponse:
    """Return full device history with per-event verification status.

    For each event stored in the DB, checks whether a matching
    ``blockchain_tx_hash`` exists and whether the stored hash matches
    the recomputed hash of the payload.
    """

    rows = (
        await session.execute(
            select(DeviceEvent)
            .where(DeviceEvent.device_id == device_id)
            .order_by(DeviceEvent.created_at.asc())
        )
    ).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Device not found")

    base_url = settings.polygonscan_base_url.rstrip("/")
    entries: list[VerificationEventEntry] = []

    for row in rows:
        # Determine verification status
        if not row.blockchain_tx_hash:
            status = "NOT_FOUND"
            scan_url = None
        else:
            recomputed = compute_payload_hash(row.payload_json)
            if row.blockchain_hash and recomputed == row.blockchain_hash:
                status = "VERIFIED"
            else:
                status = "HASH_MISMATCH"
            scan_url = f"{base_url}/tx/0x{row.blockchain_tx_hash}" if not row.blockchain_tx_hash.startswith("0x") else f"{base_url}/tx/{row.blockchain_tx_hash}"

        entries.append(
            VerificationEventEntry(
                event_type=row.event_type,
                timestamp=row.created_at,
                tx_hash=row.blockchain_tx_hash,
                polygonscan_url=scan_url,
                verification_status=status,
            )
        )

    return VerifyDeviceResponse(device_id=device_id, events=entries)


# ════════════════════════════════════════════════════════════
#  PUBLIC DEVICE PASSPORT ENDPOINT
# ════════════════════════════════════════════════════════════

# Fields that might leak PII — strip from public view
_PII_FIELDS = {
    "user_id_hash", "imei_hash", "buyer_id_hash",
    "user_digital_signature_hash", "kyc_verified",
    "pickup_latitude", "pickup_longitude",
}


@router.get("/passport/{device_id}", response_model=DevicePassportResponse)
async def device_passport(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> DevicePassportResponse:
    """Public-facing device passport — no auth required.

    Returns a redacted event history (no user PII) with blockchain proof
    links.  This is what the QR code on a sold device points to.
    """

    rows = (
        await session.execute(
            select(DeviceEvent)
            .where(DeviceEvent.device_id == device_id)
            .order_by(DeviceEvent.created_at.asc())
        )
    ).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Device not found")

    base_url = settings.polygonscan_base_url.rstrip("/")
    entries: list[PassportEventEntry] = []

    for row in rows:
        scan_url = None
        if row.blockchain_tx_hash:
            tx = row.blockchain_tx_hash
            scan_url = f"{base_url}/tx/0x{tx}" if not tx.startswith("0x") else f"{base_url}/tx/{tx}"

        entries.append(
            PassportEventEntry(
                event_type=row.event_type,
                timestamp=row.created_at,
                tx_hash=row.blockchain_tx_hash,
                polygonscan_url=scan_url,
                data_hash=row.blockchain_hash,
            )
        )

    return DevicePassportResponse(
        device_id=device_id,
        total_events=len(entries),
        events=entries,
    )


# ════════════════════════════════════════════════════════════
#  ADMIN: DEAD-LETTER QUEUE VIEWER
# ════════════════════════════════════════════════════════════


@router.get("/admin/dead-letters", response_model=list[DeadLetterEntry])
async def list_dead_letters(
    _: None = Depends(require_admin_key),
    session: AsyncSession = Depends(get_session),
) -> list[DeadLetterEntry]:
    """List unresolved blockchain dead-letter entries for admin triage."""

    rows = (
        await session.execute(
            select(BlockchainDeadLetter)
            .where(BlockchainDeadLetter.resolved_at.is_(None))
            .order_by(BlockchainDeadLetter.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    return [
        DeadLetterEntry(
            id=str(r.id),
            device_id=r.device_id,
            event_type=r.event_type,
            error_message=r.error_message,
            retry_count=r.retry_count,
            created_at=r.created_at,
            resolved_at=r.resolved_at,
        )
        for r in rows
    ]


@router.post("/admin/dead-letters/{dead_letter_id}/retry", response_model=EventResponse)
async def retry_dead_letter(
    dead_letter_id: str,
    _: None = Depends(require_admin_key),
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """Retry a failed blockchain write and mark the dead-letter as resolved on success."""

    try:
        dead_letter_uuid = uuid.UUID(dead_letter_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid dead-letter id") from exc

    dead_letter = await session.get(BlockchainDeadLetter, dead_letter_uuid)
    if dead_letter is None:
        raise HTTPException(status_code=404, detail="Dead-letter not found")
    if dead_letter.resolved_at is not None:
        raise HTTPException(status_code=409, detail="Dead-letter already resolved")

    chain = BlockchainService()
    try:
        tx_hash, data_hash = await chain.log_event(
            dead_letter.device_id,
            dead_letter.event_type,
            dead_letter.payload_json,
            dead_letter.wallet_role,
        )
    except Exception as exc:
        dead_letter.retry_count += 1
        dead_letter.error_message = str(exc)
        await session.commit()
        raise HTTPException(status_code=502, detail="Blockchain retry failed") from exc

    event_row: DeviceEvent | None = None
    if dead_letter.event_row_id:
        event_row = await session.get(DeviceEvent, dead_letter.event_row_id)
        if event_row is not None:
            event_row.blockchain_tx_hash = tx_hash
            event_row.blockchain_hash = data_hash
            event_row.blockchain_logged_at = datetime.now(timezone.utc)

    dead_letter.resolved_at = datetime.now(timezone.utc)
    await session.commit()

    if event_row is None:
        raise HTTPException(
            status_code=500,
            detail="Dead-letter resolved but linked event row was not found",
        )

    return _event_response(event_row)
