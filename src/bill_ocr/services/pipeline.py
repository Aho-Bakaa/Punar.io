from __future__ import annotations

from typing import Optional

from bill_ocr.models.schemas import ExtractionResponse
from bill_ocr.services.extractor import extract_bill_data
from bill_ocr.services.image_preprocess import get_preprocessed_images
from bill_ocr.services.ocr_engine import run_ocr_multipass
from bill_ocr.services.validator import validate_bill


def process_bill_image(
    image_bytes: bytes,
    declared_collection_mode: Optional[str] = None,
    declared_track: Optional[str] = None,
) -> ExtractionResponse:
    # Get multiple preprocessed variants of the image.
    images = get_preprocessed_images(image_bytes)

    # Multi-pass OCR across all image variants with deduplication.
    ocr_words = run_ocr_multipass(images)

    data, confidence = extract_bill_data(ocr_words)

    if declared_collection_mode and data.collection_mode is None:
        upper_mode = declared_collection_mode.strip().upper()
        if upper_mode in {"DROP_OFF", "PICKUP"}:
            data.collection_mode = upper_mode
            confidence["collection_mode"] = max(confidence.get("collection_mode", 0.0), 0.7)

    if declared_track and data.processing_track is None:
        upper_track = declared_track.strip().upper()
        if upper_track in {"REFURB", "SCRAP"}:
            data.processing_track = upper_track
            confidence["processing_track"] = max(confidence.get("processing_track", 0.0), 0.7)

    checks, needs_review, reasons = validate_bill(data, confidence)

    return ExtractionResponse(
        data=data,
        field_confidence=confidence,
        checks=checks,
        needs_manual_review=needs_review,
        review_reasons=reasons,
        request_context={
            "declared_collection_mode": declared_collection_mode or "",
            "declared_track": declared_track or "",
        },
    )
