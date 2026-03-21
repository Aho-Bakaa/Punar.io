"""Pydantic request/response schemas for all Device Passport event types.

Each event payload is a strict Pydantic model so serialisation is deterministic,
validation is automatic, and integration with the webapp is type-safe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════
#  EVENT PAYLOAD MODELS (one per event type)
# ════════════════════════════════════════════════════════════


class DeviceSubmittedPayload(BaseModel):
    """EVENT 1 — DEVICE_SUBMITTED (actor: PLATFORM_WALLET)."""

    device_id: str
    imei_hash: str
    device_category: Literal["smartphone", "laptop", "tablet", "other"]
    brand: str
    model: str
    self_reported_grade: Literal["A", "B", "C", "Scrap"]
    collection_mode: Literal["drop-off", "pickup"]
    submission_timestamp: str
    user_id_hash: str


class DeviceDroppedOffPayload(BaseModel):
    """EVENT 2A — DEVICE_DROPPED_OFF (actor: PARTNER_WALLET)."""

    device_id: str
    partner_shop_id: str
    agent_id: str
    imei_verified: bool
    kyc_verified: bool
    weight_grams: float = Field(gt=0)
    intake_timestamp: str
    accessories_included: list[str] = Field(default_factory=list)


class DevicePickedUpPayload(BaseModel):
    """EVENT 2B — DEVICE_PICKED_UP (actor: AGENT_WALLET)."""

    device_id: str
    agent_id: str
    pickup_latitude: float
    pickup_longitude: float
    imei_verified: bool
    kyc_verified: bool
    weight_grams: float = Field(gt=0)
    pickup_timestamp: str
    user_digital_signature_hash: str


class GradingChecklist(BaseModel):
    """Structured checklist responses for the grading event."""

    powers_on: bool
    screen_cracked: bool
    touchscreen_works: bool
    missing_parts: bool
    battery_swollen: bool
    ports_functional: bool
    wifi_connects: bool


class DeviceGradedPayload(BaseModel):
    """EVENT 3 — DEVICE_GRADED (actor: PARTNER_WALLET)."""

    device_id: str
    partner_shop_id: str
    checklist_responses: GradingChecklist
    final_grade: Literal["A", "B", "C", "Scrap"]
    grading_timestamp: str
    technician_id: str


class DataWipedPayload(BaseModel):
    """EVENT 4 — DATA_WIPED (actor: PARTNER_WALLET)."""

    device_id: str
    wipe_tool_used: str
    wipe_standard: str
    wipe_passes: int = Field(ge=1)
    wipe_success: bool
    technician_id: str
    wipe_timestamp: str
    wipe_certificate_document_hash: str


class DeviceRepairedPayload(BaseModel):
    """EVENT 5 — DEVICE_REPAIRED, refurb track only (actor: PARTNER_WALLET)."""

    device_id: str
    repairs_performed: list[str]
    parts_source: Literal["OEM", "aftermarket", "harvested"]
    repair_duration_hours: float = Field(ge=0)
    technician_id: str
    repair_timestamp: str


class DeviceListedPayload(BaseModel):
    """EVENT 6 — DEVICE_LISTED, refurb track only (actor: PARTNER_WALLET)."""

    device_id: str
    listing_id: str
    final_grade: Literal["A", "B", "C"]
    listed_price_inr: float = Field(gt=0)
    battery_health_pct: float = Field(ge=0, le=100)
    warranty_days: int = Field(ge=0)
    listing_timestamp: str


class DeviceSoldPayload(BaseModel):
    """EVENT 7 — DEVICE_SOLD, refurb track only (actor: PLATFORM_WALLET)."""

    device_id: str
    listing_id: str
    sale_price_inr: float = Field(gt=0)
    buyer_id_hash: str
    recoins_redeemed: float = Field(ge=0)
    platform_commission_inr: float = Field(ge=0)
    sale_timestamp: str


class DeviceBatchedPayload(BaseModel):
    """EVENT 8 — DEVICE_BATCHED_FOR_RECYCLING, scrap track (actor: PARTNER_WALLET)."""

    device_id: str
    batch_id: str
    device_category: Literal["smartphone", "laptop", "tablet", "other"]
    weight_grams: float = Field(gt=0)
    batching_timestamp: str
    partner_shop_id: str


class BatchDispatchedPayload(BaseModel):
    """EVENT 9 — BATCH_DISPATCHED_TO_RECYCLER, batch-level (actor: PLATFORM/PARTNER)."""

    batch_id: str
    recycler_id: str
    recycler_name: str
    total_weight_kg: float = Field(gt=0)
    device_count: int = Field(gt=0)
    device_ids: list[str]
    procurement_invoice_number: str
    dispatch_timestamp: str
    transport_agent_id: str


class RecyclerAcknowledgedPayload(BaseModel):
    """EVENT 10 — RECYCLER_ACKNOWLEDGED_RECEIPT, batch-level (actor: RECYCLER_WALLET)."""

    batch_id: str
    recycler_id: str
    received_weight_kg: float = Field(gt=0)
    weight_certificate_hash: str
    cpcb_procurement_entry_id: str
    receipt_timestamp: str


class EprCertificatePayload(BaseModel):
    """EVENT 11 — EPR_CERTIFICATE_ISSUED, batch-level (actor: PLATFORM_WALLET)."""

    batch_id: str
    epr_certificate_id: str
    certificate_weight_kg: float = Field(gt=0)
    oem_recipient_id: str
    certificate_date: str
    collection_fee_inr: float = Field(ge=0)


# ════════════════════════════════════════════════════════════
#  RESPONSE MODELS
# ════════════════════════════════════════════════════════════


class EventResponse(BaseModel):
    """Returned after every POST /events/* call."""

    id: str
    device_id: str
    event_type: str
    blockchain_status: Literal["QUEUED", "CONFIRMED", "FAILED"]
    created_at: datetime


class VerificationEventEntry(BaseModel):
    """Single event inside the verification response."""

    event_type: str
    timestamp: datetime
    tx_hash: str | None
    polygonscan_url: str | None
    verification_status: Literal["VERIFIED", "HASH_MISMATCH", "NOT_FOUND"]


class VerifyDeviceResponse(BaseModel):
    """GET /verify/{device_id} response."""

    device_id: str
    events: list[VerificationEventEntry]


class PassportEventEntry(BaseModel):
    """Single event inside the public device passport (no PII)."""

    event_type: str
    timestamp: datetime
    tx_hash: str | None
    polygonscan_url: str | None
    data_hash: str | None


class DevicePassportResponse(BaseModel):
    """GET /passport/{device_id} response."""

    device_id: str
    total_events: int
    events: list[PassportEventEntry]


class DeadLetterEntry(BaseModel):
    """Admin view of a failed blockchain write."""

    id: str
    device_id: str
    event_type: str
    error_message: str
    retry_count: int
    created_at: datetime
    resolved_at: datetime | None
