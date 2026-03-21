from __future__ import annotations

from typing import List

from bill_ocr.core.config import settings
from bill_ocr.models.schemas import BillData, ValidationCheck


REQUIRED_FIELDS = ["vendor_name", "bill_number", "bill_date", "total"]


def validate_bill(data: BillData, confidence: dict[str, float]) -> tuple[List[ValidationCheck], bool, list[str]]:
    checks: List[ValidationCheck] = []
    review_reasons: list[str] = []

    for field in REQUIRED_FIELDS:
        present = getattr(data, field) is not None
        checks.append(
            ValidationCheck(
                name=f"required_{field}",
                passed=present,
                message="present" if present else "missing",
            )
        )
        if not present:
            review_reasons.append(f"Missing required field: {field}")

    mode_ok = data.collection_mode in {"DROP_OFF", "PICKUP"}
    checks.append(
        ValidationCheck(
            name="collection_mode_detected",
            passed=mode_ok,
            message="detected" if mode_ok else "not detected",
        )
    )
    if not mode_ok and data.collection_mode is not None:
        review_reasons.append("Collection mode is unrecognised")

    track_ok = data.processing_track in {"REFURB", "SCRAP"}
    checks.append(
        ValidationCheck(
            name="processing_track_detected",
            passed=track_ok,
            message="detected" if track_ok else "not detected",
        )
    )
    if not track_ok and data.processing_track is not None:
        review_reasons.append("Processing track is unrecognised")

    if data.processing_track == "SCRAP":
        recycler_ok = bool(data.recycler_name)
        checks.append(
            ValidationCheck(
                name="scrap_recycler_present",
                passed=recycler_ok,
                message="present" if recycler_ok else "missing",
            )
        )
        if not recycler_ok:
            review_reasons.append("SCRAP track bill should include recycler details")

    if data.processing_track == "REFURB" and data.refurbishment_grade is not None:
        grade_ok = data.refurbishment_grade in {"A", "B"}
        checks.append(
            ValidationCheck(
                name="refurb_grade_valid",
                passed=grade_ok,
                message="valid" if grade_ok else f"unexpected grade {data.refurbishment_grade}",
            )
        )
        if not grade_ok:
            review_reasons.append("REFURB track usually requires Grade A or B")

    # -- Amount consistency: subtotal + tax - discount ≈ total --
    if data.subtotal is not None and data.tax is not None and data.total is not None:
        discount = data.discount or 0.0
        expected = data.subtotal + data.tax - discount
        ok = abs(expected - data.total) <= settings.amount_tolerance
        checks.append(
            ValidationCheck(
                name="amount_consistency",
                passed=ok,
                message=(
                    "consistent"
                    if ok
                    else f"expected ~{expected:.2f}, found {data.total:.2f}"
                ),
            )
        )
        if not ok:
            review_reasons.append("Totals are inconsistent")

    # -- CGST + SGST ≈ Total Tax --
    if data.cgst is not None and data.sgst is not None and data.tax is not None:
        gst_sum = round(data.cgst + data.sgst, 2)
        ok = abs(gst_sum - data.tax) <= settings.amount_tolerance
        checks.append(
            ValidationCheck(
                name="gst_breakdown_consistency",
                passed=ok,
                message=(
                    "consistent"
                    if ok
                    else f"CGST({data.cgst}) + SGST({data.sgst}) = {gst_sum}, tax = {data.tax}"
                ),
            )
        )
        if not ok:
            review_reasons.append("GST breakdown does not match total tax")

    if data.line_items and data.total is not None:
        line_sum = sum(i.amount or 0.0 for i in data.line_items)
        ok = abs(line_sum - data.total) <= max(settings.amount_tolerance, 3.0)
        checks.append(
            ValidationCheck(
                name="line_item_sum_check",
                passed=ok,
                message=(
                    "consistent" if ok else f"line sum {line_sum:.2f} differs from total {data.total:.2f}"
                ),
            )
        )
        if not ok:
            review_reasons.append("Line-item sum mismatch")

    for name, score in confidence.items():
        if score < settings.min_field_confidence and name != "line_items":
            review_reasons.append(f"Low confidence on {name}: {score:.2f}")

    needs_manual_review = len(review_reasons) > 0
    return checks, needs_manual_review, sorted(set(review_reasons))
