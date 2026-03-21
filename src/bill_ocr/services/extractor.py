"""Structured field extraction from OCR words.

Uses **spatial line reconstruction** so that fields split across multiple
OCR word-fragments are correctly associated.  Understands Indian GST
invoice patterns and extracts electronic-device specific info (IMEI,
model name, product name, HSN).
"""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, List

from dateutil import parser as date_parser

from bill_ocr.core.config import settings
from bill_ocr.models.schemas import BillData, LineItem, OCRWord
from bill_ocr.services.spatial import group_words_into_lines, lines_to_text

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

AMOUNT_RE = re.compile(
    r"(?:rs\.?|inr|usd|eur|\$|€|₹)?\s*"
    r"([0-9]{1,3}(?:[,][0-9]{2,3})*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
DATE_HINT_RE = re.compile(r"\bdate\b|invoice\s*date|bill\s*date", re.IGNORECASE)
BILL_NO_HINT_RE = re.compile(r"invoice\s*(?:no\.?|number)|bill\s*(?:no\.?|number)", re.IGNORECASE)
SUBTOTAL_HINT_RE = re.compile(r"sub\s*total|taxable\s*(?:amount|value)", re.IGNORECASE)
TAX_HINT_RE = re.compile(r"total\s*tax|tax\s*amount", re.IGNORECASE)
CGST_HINT_RE = re.compile(r"\bcgst\b|c\.?g\.?s\.?t|add\s*:\s*cgst", re.IGNORECASE)
SGST_HINT_RE = re.compile(r"\bsgst\b|s\.?g\.?s\.?t|add\s*:\s*sgst", re.IGNORECASE)
IGST_HINT_RE = re.compile(r"\bigst\b|i\.?g\.?s\.?t|add\s*:\s*igst", re.IGNORECASE)
TOTAL_HINT_RE = re.compile(
    r"total\s*amount\s*after\s*tax|grand\s*total|net\s*(?:amount|total|payable)|"
    r"amount\s*payable|bill\s*amount",
    re.IGNORECASE,
)
# "Total" alone — very weak, used only as a last resort
WEAK_TOTAL_RE = re.compile(r"^\s*total\s*$", re.IGNORECASE)
DISCOUNT_HINT_RE = re.compile(r"discount", re.IGNORECASE)
RECOINS_RE = re.compile(r"recoins?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
GRADE_RE = re.compile(r"grade\s*[:\-]?\s*([ABC]|scrap)", re.IGNORECASE)
GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2})\b")
IMEI_RE = re.compile(r"\b(\d{15})\b")
INVOICE_NO_RE = re.compile(r"invoice\s*no\.?", re.IGNORECASE)
INVOICE_DATE_RE = re.compile(r"invoice\s*date", re.IGNORECASE)
MS_RE = re.compile(r"\bm\s*/\s*s\b", re.IGNORECASE)
CONSUMER_NAME_RE = re.compile(
    r"(?:customer|buyer|bill\s*to|sold\s*to)\s*(?:name)?\s*[:\-]?\s*(.*)",
    re.IGNORECASE,
)
HSN_SAC_RE = re.compile(r"\bhsn\b|\bsac\b", re.IGNORECASE)

# Electronic device model patterns (Redmi 9A, Samsung Galaxy M31, etc.)
DEVICE_MODEL_RE = re.compile(
    r"((?:redmi|poco|realme|samsung|galaxy|iphone|ipad|macbook|nokia|"
    r"motorola|moto|vivo|oppo|oneplus|lenovo|dell|hp|asus|acer|mi|note)\s*"
    r"[\w\d\s/\-\(\)]+)",
    re.IGNORECASE,
)

DEVICE_HINTS = {
    "SMARTPHONE": ["smartphone", "phone", "mobile", "iphone", "android", "redmi",
                    "samsung", "vivo", "oppo", "oneplus", "realme", "poco", "galaxy",
                    "nokia", "motorola", "moto", "mi"],
    "LAPTOP": ["laptop", "notebook", "macbook", "dell", "hp", "lenovo", "asus", "acer"],
    "TABLET": ["tablet", "ipad"],
    "PERIPHERAL": ["mouse", "keyboard", "headphone", "earphone", "charger", "adapter"],
}

OEM_HINTS = ["samsung", "hp", "xiaomi", "redmi", "apple", "dell", "lenovo", "asus",
             "acer", "vivo", "oppo", "oneplus", "realme", "poco", "motorola", "nokia"]
RECYCLER_HINTS = ["attero", "e-parisaraa", "e parisaraa", "recycler"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fuzzy_contains(line: str, keywords: list[str], threshold: int = 86) -> bool:
    line_lower = line.lower()
    for token in re.split(r"\W+", line_lower):
        if not token:
            continue
        for kw in keywords:
            if token == kw:
                return True
            score = int(SequenceMatcher(None, token, kw).ratio() * 100)
            if score >= threshold:
                return True
    return False


def _parse_amount(text: str) -> Optional[float]:
    """Extract the *last* monetary amount in *text*."""
    matches = list(AMOUNT_RE.finditer(text))
    if not matches:
        return None
    num = matches[-1].group(1).replace(",", "")
    try:
        v = float(num)
        return v if v > 0 else None
    except ValueError:
        return None


def _parse_all_amounts(text: str) -> list[float]:
    """Return *all* numeric amounts found in text."""
    results = []
    for m in AMOUNT_RE.finditer(text):
        num = m.group(1).replace(",", "")
        try:
            v = float(num)
            if v > 0:
                results.append(v)
        except ValueError:
            pass
    return results


def _parse_date(text: str):
    try:
        dt = date_parser.parse(text, dayfirst=True, fuzzy=True)
        if dt.year < 1990 or dt.year > datetime.utcnow().year + 1:
            return None
        return dt.date()
    except Exception:
        return None


def _right_of_label(line: str, label_re: re.Pattern) -> str:
    """Return everything to the right of a matched label on the same line."""
    m = label_re.search(line)
    if not m:
        return ""
    return line[m.end():].strip().lstrip(":").lstrip("-").strip()


def _clean_bill_number(raw: str) -> str:
    """Clean up extracted bill/invoice number."""
    cleaned = re.sub(r"^[:\-.\s]+", "", raw)
    tokens = cleaned.split()
    if tokens:
        return tokens[0].strip(".,;:")
    return cleaned.strip()


def _bbox_height(word: OCRWord) -> float:
    """Return the height of a word's bounding box (proxy for font size)."""
    ys = [pt[1] for pt in word.bbox]
    return max(ys) - min(ys)


def _is_imei_line(text: str) -> bool:
    """Check if a line is essentially just IMEI numbers."""
    cleaned = re.sub(r"imei[\s:\-]*", "", text, flags=re.IGNORECASE).strip()
    # Line is mostly 15-digit numbers
    digits_only = re.sub(r"[^0-9]", "", cleaned)
    return len(digits_only) >= 15 and len(digits_only) / max(len(cleaned.replace(" ", "")), 1) > 0.8


def _extract_imeis(text: str) -> list[str]:
    """Extract all IMEI numbers from text."""
    return IMEI_RE.findall(text)


def _is_amount_like_line(lower: str) -> bool:
    """Check if a line is a known amount-label line that should NOT be a line item."""
    for pat in [SUBTOTAL_HINT_RE, TAX_HINT_RE, CGST_HINT_RE, SGST_HINT_RE,
                IGST_HINT_RE, TOTAL_HINT_RE, DISCOUNT_HINT_RE, WEAK_TOTAL_RE]:
        if pat.search(lower):
            return True
    # Also skip "total in words", bank details etc.
    if re.search(r"total\s*in\s*words|bank\s*detail|terms|condition|gst\s*payable|reverse\s*charge|certified", lower):
        return True
    return False


# ---------------------------------------------------------------------------
# Vendor name extraction using bbox height as font-size proxy
# ---------------------------------------------------------------------------

def _extract_vendor_name(
    spatial_lines: list[list[OCRWord]],
    lines: list[str],
) -> tuple[Optional[str], float]:
    """Find the vendor/business name — typically the tallest text near the top."""
    if not spatial_lines:
        return None, 0.0

    # Only consider the top portion of the document (first ~30% of Y range).
    all_ys = [pt[1] for line in spatial_lines for w in line for pt in w.bbox]
    if not all_ys:
        return None, 0.0
    min_y, max_y = min(all_ys), max(all_ys)
    top_cutoff = min_y + (max_y - min_y) * 0.20  # top 20%

    best_text = ""
    best_height = 0.0

    for line_words in spatial_lines:
        # Average Y of this line
        avg_y = sum(sum(pt[1] for pt in w.bbox) / len(w.bbox) for w in line_words) / len(line_words)
        if avg_y > top_cutoff:
            continue

        # Average height of words in this line
        avg_h = sum(_bbox_height(w) for w in line_words) / len(line_words)
        line_text = " ".join(w.text for w in line_words if w.text).strip()

        # Skip very short lines, email addresses, phone numbers, pure numbers
        if len(line_text) < 3:
            continue
        if "@" in line_text or re.match(r"^\d[\d\s\-]+$", line_text):
            continue
        if re.search(r"name\s*:|phone\s*:|email\s*:|gstin|gst\s*no", line_text, re.IGNORECASE):
            continue

        if avg_h > best_height:
            best_height = avg_h
            best_text = line_text

    if best_text:
        return best_text, 0.80

    # Fallback: first long-ish text in top lines
    for text in lines[:3]:
        if len(text.strip()) > 3 and "@" not in text:
            return text.strip(), 0.55

    return None, 0.0


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_bill_data(words: list[OCRWord]) -> tuple[BillData, dict[str, float]]:
    """Extract structured bill data using spatial line reconstruction."""

    spatial_lines = group_words_into_lines(words)
    lines = lines_to_text(spatial_lines)

    data = BillData(currency=settings.default_currency)
    confidence: dict[str, float] = {
        "vendor_name": 0.0,
        "bill_number": 0.0,
        "bill_date": 0.0,
        "subtotal": 0.0,
        "tax": 0.0,
        "discount": 0.0,
        "total": 0.0,
        "line_items": 0.0,
        "collection_mode": 0.0,
        "processing_track": 0.0,
        "device_category": 0.0,
        "recycler_name": 0.0,
        "oem_partner": 0.0,
        "recoins_earned": 0.0,
        "refurbishment_grade": 0.0,
    }

    found_total_amount_after_tax = False
    found_taxable_amount = False
    cgst_val: Optional[float] = None
    sgst_val: Optional[float] = None

    # ---- Vendor name (bbox-height heuristic) ----
    vendor, vendor_conf = _extract_vendor_name(spatial_lines, lines)
    if vendor:
        data.vendor_name = vendor
        confidence["vendor_name"] = vendor_conf

    # ---- GSTIN ----
    full_text = " ".join(lines)
    gstin_matches = GSTIN_RE.findall(full_text)
    if gstin_matches:
        data.gstin = gstin_matches[0]
        if len(gstin_matches) > 1:
            data.customer_gstin = gstin_matches[1]

    # ---- Per-line extraction ----
    for idx, line in enumerate(lines):
        lower = line.lower()

        # -- Collection mode --
        if "drop off" in lower or "drop-off" in lower:
            data.collection_mode = "DROP_OFF"
            confidence["collection_mode"] = 0.92
        elif "pickup" in lower or "pick up" in lower:
            data.collection_mode = "PICKUP"
            confidence["collection_mode"] = 0.92

        # -- Processing track --
        if "refurb" in lower or "grade a" in lower or "grade b" in lower:
            data.processing_track = "REFURB"
            confidence["processing_track"] = max(confidence["processing_track"], 0.88)
        if "scrap" in lower or "grade c" in lower:
            data.processing_track = "SCRAP"
            confidence["processing_track"] = max(confidence["processing_track"], 0.9)

        # -- Refurbishment grade --
        grade_match = GRADE_RE.search(lower)
        if grade_match:
            grade = grade_match.group(1).upper()
            data.refurbishment_grade = "SCRAP" if grade == "SCRAP" else grade
            confidence["refurbishment_grade"] = 0.9

        # -- Device category --
        if data.device_category is None:
            for category, hints in DEVICE_HINTS.items():
                if _fuzzy_contains(lower, hints):
                    data.device_category = category
                    confidence["device_category"] = 0.86
                    break

        # -- OEM partner --
        if not data.oem_partner:
            for oem in OEM_HINTS:
                if oem in lower:
                    data.oem_partner = oem.upper()
                    confidence["oem_partner"] = 0.84
                    break

        # -- Recycler --
        if not data.recycler_name:
            for recycler in RECYCLER_HINTS:
                if recycler in lower:
                    data.recycler_name = line.strip()
                    confidence["recycler_name"] = 0.86
                    break

        # -- ReCoins --
        recoins_match = RECOINS_RE.search(line)
        if recoins_match:
            data.recoins_earned = float(recoins_match.group(1))
            confidence["recoins_earned"] = 0.9

        # -- Invoice / Bill number (spatial-aware) --
        if not data.bill_number and BILL_NO_HINT_RE.search(lower):
            rest = _right_of_label(line, BILL_NO_HINT_RE)
            if rest:
                data.bill_number = _clean_bill_number(rest)
                confidence["bill_number"] = 0.85
            elif idx + 1 < len(lines):
                data.bill_number = _clean_bill_number(lines[idx + 1])
                confidence["bill_number"] = 0.7

        if not data.bill_number and INVOICE_NO_RE.search(lower):
            rest = _right_of_label(line, INVOICE_NO_RE)
            if rest:
                data.bill_number = _clean_bill_number(rest)
                confidence["bill_number"] = 0.85

        # -- Invoice / Bill date (spatial-aware) --
        if not data.bill_date and (INVOICE_DATE_RE.search(lower) or DATE_HINT_RE.search(lower)):
            # Try the label-specific right-of extraction first
            for pat in [INVOICE_DATE_RE, DATE_HINT_RE]:
                rest = _right_of_label(line, pat)
                if rest:
                    parsed = _parse_date(rest)
                    if parsed:
                        data.bill_date = parsed
                        confidence["bill_date"] = 0.88
                        break
            if not data.bill_date:
                parsed = _parse_date(line)
                if parsed:
                    data.bill_date = parsed
                    confidence["bill_date"] = 0.82
            if not data.bill_date and idx + 1 < len(lines):
                parsed = _parse_date(lines[idx + 1])
                if parsed:
                    data.bill_date = parsed
                    confidence["bill_date"] = 0.72

        # -- Consumer / Customer name --
        if not data.consumer_name:
            # M/S is the standard Indian business invoice prefix for buyer
            if MS_RE.search(lower):
                # Get content after "M/S" but STOP at any other label
                rest = _right_of_label(line, MS_RE)
                if rest:
                    # The rest might contain "MANISH Address Arjun Nagar..."
                    # Take only up to the first known label or newline-equivalent
                    # Simple: take first word/name (capitalized words)
                    name_part = re.split(
                        r"\b(?:address|phone|gstin|place|invoice|date|detail)\b",
                        rest,
                        flags=re.IGNORECASE,
                    )[0].strip()
                    if name_part:
                        data.consumer_name = name_part
                        confidence.setdefault("consumer_name", 0.82)
            elif CONSUMER_NAME_RE.search(lower):
                m = CONSUMER_NAME_RE.search(line)
                if m and m.group(1).strip():
                    data.consumer_name = m.group(1).strip()
                    confidence.setdefault("consumer_name", 0.78)

        # ---- Amount fields (specific patterns first) ----

        # "Total Amount After Tax" / "Net Amount" / "Amount Payable"
        if re.search(r"total\s*amount\s*after\s*tax|net\s*(?:amount|payable)|amount\s*payable", lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.total = amt
                confidence["total"] = 0.95
                found_total_amount_after_tax = True
            continue

        # "Taxable Amount" / "Taxable Value" (subtotal before GST)
        if re.search(r"taxable\s*(?:amount|value)", lower) and not re.search(r"sr|no|name|product|service", lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.subtotal = amt
                confidence["subtotal"] = 0.92
                found_taxable_amount = True
            continue

        # CGST
        if CGST_HINT_RE.search(lower) and not re.search(r"sr|no|name|product|%\s*amount", lower):
            amt = _parse_amount(line)
            if amt is not None:
                cgst_val = amt
                data.cgst = amt
            continue

        # SGST
        if SGST_HINT_RE.search(lower) and not re.search(r"sr|no|name|product|%\s*amount", lower):
            amt = _parse_amount(line)
            if amt is not None:
                sgst_val = amt
                data.sgst = amt
            continue

        # "Total Tax"
        if TAX_HINT_RE.search(lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.tax = amt
                confidence["tax"] = 0.90
            continue

        # Generic subtotal
        if not found_taxable_amount and SUBTOTAL_HINT_RE.search(lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.subtotal = amt
                confidence["subtotal"] = 0.88
            continue

        # Discount
        if DISCOUNT_HINT_RE.search(lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.discount = amt
                confidence["discount"] = 0.8
            continue

        # Generic "total" only as fallback
        if not found_total_amount_after_tax and TOTAL_HINT_RE.search(lower):
            amt = _parse_amount(line)
            if amt is not None:
                data.total = amt
                confidence["total"] = 0.88

    # ---- Derive tax from CGST + SGST if not directly found ----
    if data.tax is None and cgst_val is not None and sgst_val is not None:
        data.tax = round(cgst_val + sgst_val, 2)
        confidence["tax"] = 0.88

    # ---- Line-item extraction ----
    _extract_line_items(spatial_lines, lines, data, confidence)

    # ---- Track inference ----
    if data.processing_track is None and data.refurbishment_grade:
        if data.refurbishment_grade in {"A", "B"}:
            data.processing_track = "REFURB"
            confidence["processing_track"] = max(confidence["processing_track"], 0.82)
        elif data.refurbishment_grade in {"C", "SCRAP"}:
            data.processing_track = "SCRAP"
            confidence["processing_track"] = max(confidence["processing_track"], 0.84)

    return data, confidence


# ---------------------------------------------------------------------------
# Line-item extraction
# ---------------------------------------------------------------------------

TABLE_HEADER_RE = re.compile(
    r"sr\.?\s*no|s\.?\s*no|name\s*of\s*product|description|particulars|\bitem\b",
    re.IGNORECASE,
)

TABLE_FOOTER_RE = re.compile(
    r"^\s*total\s+\d|^total\s*$|sub\s*total|total\s*in\s*words|taxable\s*amount|"
    r"bank\s*detail|terms\s*and|gst\s*payable",
    re.IGNORECASE,
)


def _extract_line_items(
    spatial_lines: list[list[OCRWord]],
    lines: list[str],
    data: BillData,
    confidence: dict[str, float],
) -> None:
    """Extract product rows from the table region.

    Strategy:
    1. Locate the table header row (Sr No / Name of Product / ...).
    2. Locate the table footer (Total row, or Taxable Amount summary).
    3. Within the table body, identify *primary product rows* (rows starting
       with a serial number) vs *continuation rows* (IMEI lines, sub-info).
    4. Continuation rows get folded into the preceding primary row.
    """
    # Find table boundaries.
    header_idx: Optional[int] = None
    footer_idx: Optional[int] = None

    for i, line in enumerate(lines):
        if header_idx is None and TABLE_HEADER_RE.search(line):
            header_idx = i
        elif header_idx is not None and TABLE_FOOTER_RE.search(line):
            footer_idx = i
            break

    if header_idx is None:
        return  # No table found — skip line item extraction entirely.

    end = footer_idx if footer_idx is not None else len(lines)
    body_lines = lines[header_idx + 1 : end]

    # Skip sub-header rows (%, Amount column labels)
    filtered: list[str] = []
    for bl in body_lines:
        stripped = bl.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        # Skip pure column-header repetitions
        if re.fullmatch(r"[%\s]+|amount|qty|rate|total", lower):
            continue
        filtered.append(stripped)

    if not filtered:
        return

    # Group rows: a "primary" row starts with a serial number (1, 2, 3…)
    # or contains a clearly identifiable product name. Continuation rows
    # are IMEI lines or lines without a leading serial number.
    items_raw: list[dict] = []
    current_item: Optional[dict] = None

    for row_text in filtered:
        lower = row_text.lower()

        # Skip amount-label lines that leaked into the table region
        if _is_amount_like_line(lower):
            continue

        # Check if this is a primary row (starts with a serial number)
        sr_match = re.match(r"^\s*(\d{1,3})\s+", row_text)
        is_imei = _is_imei_line(row_text)

        if sr_match and not is_imei:
            # Start of a new item
            if current_item:
                items_raw.append(current_item)
            current_item = {
                "text": row_text,
                "continuation": [],
                "imeis": _extract_imeis(row_text),
            }
        elif is_imei:
            # IMEI continuation row
            imeis = _extract_imeis(row_text)
            if current_item:
                current_item["imeis"].extend(imeis)
                current_item["continuation"].append(row_text)
            else:
                # Orphan IMEI line — still create an item record
                current_item = {
                    "text": "",
                    "continuation": [row_text],
                    "imeis": imeis,
                }
        elif current_item:
            # Other continuation (e.g. extended product description)
            current_item["continuation"].append(row_text)
            current_item["imeis"].extend(_extract_imeis(row_text))
        else:
            # First row without serial number — treat as primary
            current_item = {
                "text": row_text,
                "continuation": [],
                "imeis": _extract_imeis(row_text),
            }

    if current_item:
        items_raw.append(current_item)

    # Now parse each grouped item into a LineItem.
    for item_raw in items_raw:
        primary = item_raw["text"]
        full_desc = primary
        for cont in item_raw["continuation"]:
            # Don't include pure-IMEI lines in the description
            if not _is_imei_line(cont):
                full_desc += " " + cont

        amounts = _parse_all_amounts(primary)

        # -- Parse structured columns from the primary row --
        # Typical Indian invoice columns:
        # [SrNo] [ProductName] [HSN] [Qty] [Rate] [TaxableValue] [CGST%] [CGSTAmt] [SGST%] [SGSTAmt] [Total]
        # The amounts extracted are ordered left-to-right.

        qty: Optional[float] = None
        unit_price: Optional[float] = None
        total_amt: Optional[float] = None
        hsn: Optional[str] = None

        if len(amounts) >= 5:
            # Full row with percentages: qty, rate, taxable, pct, amt, pct, amt, total
            # Filter: qty is usually 1-1000, rate is moderate, percentages < 100
            qty = amounts[0] if amounts[0] <= 10000 else None
            unit_price = amounts[1] if len(amounts) > 1 else None
            total_amt = amounts[-1]  # Last column is total
        elif len(amounts) >= 3:
            qty = amounts[0] if amounts[0] <= 10000 else None
            unit_price = amounts[1]
            total_amt = amounts[-1]
        elif len(amounts) == 2:
            unit_price = amounts[0]
            total_amt = amounts[1]
        elif len(amounts) == 1:
            total_amt = amounts[0]

        # -- HSN code: 4-8 digit number that appears after product name --
        # It's NOT an amount (not in the amounts list) or is typically the
        # first standalone number that doesn't match qty/rate patterns.
        hsn_candidates = re.findall(r"\b(\d{4,8})\b", primary)
        for cand in hsn_candidates:
            try:
                cand_float = float(cand)
                # HSN is an integer code (no decimals in string), and typically
                # 4-8 digits, not matching any amount we've already extracted
                if "." not in cand and cand_float not in amounts:
                    hsn = cand
                    break
            except ValueError:
                hsn = cand
                break

        # -- Build description (strip numbers, keep product name) --
        desc_parts: list[str] = []
        for token in full_desc.split():
            if re.fullmatch(r"\d{1,3}", token):
                continue  # Skip serial number, small numbers
            if re.fullmatch(r"[0-9,.\-]+", token):
                continue  # Skip pure numeric
            if re.fullmatch(r"(?:rs\.?|inr|₹|\$|€)", token, re.IGNORECASE):
                continue
            desc_parts.append(token)
        description = " ".join(desc_parts).strip() or full_desc.strip()

        # -- Product/model name --
        product_name: Optional[str] = None
        model_name: Optional[str] = None
        model_match = DEVICE_MODEL_RE.search(full_desc)
        if model_match:
            model_name = model_match.group(1).strip()
            product_name = model_name

        item = LineItem(
            description=description,
            product_name=product_name,
            model_name=model_name,
            quantity=qty,
            unit_price=unit_price,
            amount=total_amt,
            hsn_code=hsn,
            imei_numbers=item_raw["imeis"],
            confidence=0.75,
        )
        data.line_items.append(item)

    if data.line_items:
        confidence["line_items"] = (
            sum(i.confidence for i in data.line_items) / len(data.line_items)
        )
