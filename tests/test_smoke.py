"""Smoke tests for Round 2 accuracy fixes."""
import sys
from datetime import date
from bill_ocr.models.schemas import BillData, OCRWord
from bill_ocr.services.validator import validate_bill
from bill_ocr.services.spatial import group_words_into_lines, lines_to_text
from bill_ocr.services.extractor import extract_bill_data

errors = []

def check(name, condition, msg=""):
    if condition:
        print(f"  PASS: {name}")
    else:
        print(f"  FAIL: {name} — {msg}")
        errors.append(f"{name}: {msg}")


# ==========================================================================
# Test 1: Validator (regression test — original test case)
# ==========================================================================
print("--- Test 1: Validator amount consistency ---")
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
    "vendor_name": 0.9, "bill_number": 0.9, "bill_date": 0.9,
    "subtotal": 0.9, "tax": 0.9, "discount": 0.9, "total": 0.9,
    "line_items": 0.0, "collection_mode": 0.95, "processing_track": 0.94,
    "device_category": 0.8, "recycler_name": 0.9, "oem_partner": 0.9,
    "recoins_earned": 0.9, "refurbishment_grade": 0.92,
}
checks, needs_review, reasons = validate_bill(data, confidence)
check("amount_consistency", any(c.name == "amount_consistency" and c.passed for c in checks))
check("no_review_needed", not needs_review, str(reasons))


# ==========================================================================
# Test 2: Vendor name uses bbox height (tallest text wins)
# ==========================================================================
print("\n--- Test 2: Vendor name via bbox height ---")
words_vendor = [
    # "ANAND COMMUNICATION" — large bbox (25px tall)
    OCRWord(text="ANAND COMMUNICATION", confidence=0.97,
            bbox=[[10, 10], [400, 10], [400, 45], [10, 45]]),
    # "448 ARJUN NAGAR" — smaller bbox (15px tall)
    OCRWord(text="448 ARJUN NAGAR", confidence=0.95,
            bbox=[[10, 55], [250, 55], [250, 72], [10, 72]]),
    # "Email : kamalthakral24@gmail.com" — same height
    OCRWord(text="Email : kamalthakral24@gmail.com", confidence=0.93,
            bbox=[[350, 55], [700, 55], [700, 72], [350, 72]]),
    # "Name : KAMAL THAKRAL" — right side, small
    OCRWord(text="Name : KAMAL THAKRAL", confidence=0.92,
            bbox=[[500, 10], [700, 10], [700, 28], [500, 28]]),
]
d, _ = extract_bill_data(words_vendor)
check("vendor_is_ANAND", d.vendor_name == "ANAND COMMUNICATION",
      f"got '{d.vendor_name}'")


# ==========================================================================
# Test 3: Consumer name from M/S field
# ==========================================================================
print("\n--- Test 3: Consumer name M/S ---")
words_ms = [
    OCRWord(text="ANAND COMMUNICATION", confidence=0.97,
            bbox=[[10, 10], [400, 10], [400, 45], [10, 45]]),
    OCRWord(text="Customer Detail", confidence=0.90,
            bbox=[[10, 100], [180, 100], [180, 115], [10, 115]]),
    OCRWord(text="Invoice No.", confidence=0.92,
            bbox=[[200, 100], [300, 100], [300, 115], [200, 115]]),
    OCRWord(text="24", confidence=0.91,
            bbox=[[310, 100], [340, 100], [340, 115], [310, 115]]),
    OCRWord(text="Invoice Date", confidence=0.92,
            bbox=[[380, 100], [480, 100], [480, 115], [380, 115]]),
    OCRWord(text="26-May-2022", confidence=0.90,
            bbox=[[490, 100], [600, 100], [600, 115], [490, 115]]),
    OCRWord(text="M/S", confidence=0.92,
            bbox=[[10, 130], [50, 130], [50, 148], [10, 148]]),
    OCRWord(text="MANISH", confidence=0.94,
            bbox=[[60, 130], [160, 130], [160, 148], [60, 148]]),
]
d2, _ = extract_bill_data(words_ms)
check("consumer_is_MANISH", d2.consumer_name == "MANISH",
      f"got '{d2.consumer_name}'")
check("bill_number_24", d2.bill_number == "24",
      f"got '{d2.bill_number}'")
check("bill_date_parsed", d2.bill_date is not None and str(d2.bill_date) == "2022-05-26",
      f"got '{d2.bill_date}'")


# ==========================================================================
# Test 4: Line items with IMEI folding
# ==========================================================================
print("\n--- Test 4: Line items + IMEI folding ---")
words_table = [
    OCRWord(text="ANAND COMMUNICATION", confidence=0.97,
            bbox=[[10, 10], [400, 10], [400, 45], [10, 45]]),
    # Table header
    OCRWord(text="Sr. No.", confidence=0.90,
            bbox=[[10, 200], [70, 200], [70, 215], [10, 215]]),
    OCRWord(text="Name of Product / Service", confidence=0.90,
            bbox=[[80, 200], [300, 200], [300, 215], [80, 215]]),
    OCRWord(text="HSN / SAC", confidence=0.90,
            bbox=[[310, 200], [400, 200], [400, 215], [310, 215]]),
    OCRWord(text="Qty", confidence=0.90,
            bbox=[[410, 200], [440, 200], [440, 215], [410, 215]]),
    OCRWord(text="Rate", confidence=0.90,
            bbox=[[450, 200], [500, 200], [500, 215], [450, 215]]),
    # Product row
    OCRWord(text="1", confidence=0.92,
            bbox=[[10, 230], [20, 230], [20, 248], [10, 248]]),
    OCRWord(text="REDMI 9A (2GB/32GB) NATURE GREEN", confidence=0.94,
            bbox=[[30, 230], [300, 230], [300, 248], [30, 248]]),
    OCRWord(text="1.00", confidence=0.92,
            bbox=[[410, 230], [450, 230], [450, 248], [410, 248]]),
    OCRWord(text="6,355.93", confidence=0.93,
            bbox=[[460, 230], [540, 230], [540, 248], [460, 248]]),
    OCRWord(text="6,355.93", confidence=0.93,
            bbox=[[550, 230], [630, 230], [630, 248], [550, 248]]),
    OCRWord(text="9.00", confidence=0.91,
            bbox=[[640, 230], [680, 230], [680, 248], [640, 248]]),
    OCRWord(text="572.03", confidence=0.92,
            bbox=[[690, 230], [750, 230], [750, 248], [690, 248]]),
    OCRWord(text="9.00", confidence=0.91,
            bbox=[[760, 230], [800, 230], [800, 248], [760, 248]]),
    OCRWord(text="572.03", confidence=0.92,
            bbox=[[810, 230], [870, 230], [870, 248], [810, 248]]),
    OCRWord(text="7,499.99", confidence=0.93,
            bbox=[[880, 230], [960, 230], [960, 248], [880, 248]]),
    # IMEI line 1
    OCRWord(text="IMEI- 861625052866078", confidence=0.89,
            bbox=[[30, 260], [300, 260], [300, 275], [30, 275]]),
    # IMEI line 2
    OCRWord(text="861625052866086", confidence=0.88,
            bbox=[[30, 280], [200, 280], [200, 295], [30, 295]]),
    # Footer
    OCRWord(text="Total", confidence=0.92,
            bbox=[[10, 320], [60, 320], [60, 338], [10, 338]]),
    OCRWord(text="1.00", confidence=0.91,
            bbox=[[410, 320], [450, 320], [450, 338], [410, 338]]),
    OCRWord(text="7,499.99", confidence=0.93,
            bbox=[[880, 320], [960, 320], [960, 338], [880, 338]]),
]
d3, c3 = extract_bill_data(words_table)
check("has_line_items", len(d3.line_items) >= 1, f"got {len(d3.line_items)} items")
if d3.line_items:
    item = d3.line_items[0]
    check("item_has_redmi", "REDMI" in (item.description or "").upper(),
          f"desc='{item.description}'")
    check("item_amount_7499", item.amount == 7499.99,
          f"got {item.amount}")
    check("item_qty_1", item.quantity == 1.0,
          f"got {item.quantity}")
    check("item_rate_6355", item.unit_price == 6355.93,
          f"got {item.unit_price}")
    check("item_has_imeis", len(item.imei_numbers) >= 1,
          f"got {item.imei_numbers}")
    check("imei_not_qty", item.quantity != 861,
          f"qty should not be 861, got {item.quantity}")
    check("model_name_redmi", item.model_name is not None and "redmi" in item.model_name.lower(),
          f"got '{item.model_name}'")
    # Make sure IMEI lines didn't create extra items
    check("no_phantom_imei_items", len(d3.line_items) == 1,
          f"got {len(d3.line_items)} items (expected 1)")


# ==========================================================================
# Test 5: collection_mode/processing_track default to None
# ==========================================================================
print("\n--- Test 5: Defaults are None ---")
d4, _ = extract_bill_data([
    OCRWord(text="Simple Invoice", confidence=0.95,
            bbox=[[10, 10], [200, 10], [200, 40], [10, 40]]),
])
check("collection_mode_none", d4.collection_mode is None,
      f"got '{d4.collection_mode}'")
check("processing_track_none", d4.processing_track is None,
      f"got '{d4.processing_track}'")
check("device_category_none", d4.device_category is None,
      f"got '{d4.device_category}'")


# ==========================================================================
print(f"\n{'='*60}")
if errors:
    print(f"FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
