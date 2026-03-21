from datetime import date

from bill_ocr.models.schemas import BillData
from bill_ocr.services.validator import validate_bill


def test_amount_consistency_passes():
    data = BillData(
        vendor_name="ABC Store",
        bill_number="INV-1",
        bill_date=date(2026, 3, 20),
        collection_mode="DROP_OFF",
        processing_track="REFURB",
        refurbishment_grade="A",
        subtotal=100.0,
        tax=18.0,
        total=118.0,
        line_items=[],
    )
    confidence = {
        "vendor_name": 0.9,
        "bill_number": 0.9,
        "bill_date": 0.9,
        "subtotal": 0.9,
        "tax": 0.9,
        "discount": 0.9,
        "total": 0.9,
        "line_items": 0.0,
        "collection_mode": 0.95,
        "processing_track": 0.94,
        "device_category": 0.8,
        "recycler_name": 0.9,
        "oem_partner": 0.9,
        "recoins_earned": 0.9,
        "refurbishment_grade": 0.92,
    }

    checks, needs_review, reasons = validate_bill(data, confidence)
    assert any(c.name == "amount_consistency" and c.passed for c in checks)
    assert not needs_review
    assert reasons == []
