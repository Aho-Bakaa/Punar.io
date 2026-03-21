from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]


class LineItem(BaseModel):
    description: str = ""
    product_name: Optional[str] = None
    model_name: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    hsn_code: Optional[str] = None
    imei_numbers: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class BillData(BaseModel):
    vendor_name: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[date] = None
    currency: str = "INR"
    consumer_name: Optional[str] = None
    gstin: Optional[str] = None
    customer_gstin: Optional[str] = None
    device_category: Optional[
        Literal["SMARTPHONE", "LAPTOP", "TABLET", "PERIPHERAL"]
    ] = None
    collection_mode: Optional[Literal["DROP_OFF", "PICKUP"]] = None
    processing_track: Optional[Literal["REFURB", "SCRAP"]] = None
    refurbishment_grade: Optional[Literal["A", "B", "C", "SCRAP"]] = None
    recycler_name: Optional[str] = None
    oem_partner: Optional[str] = None
    recoins_earned: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    line_items: List[LineItem] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str


class ExtractionResponse(BaseModel):
    data: BillData
    field_confidence: dict[str, float]
    checks: List[ValidationCheck]
    needs_manual_review: bool
    review_reasons: List[str]
    request_context: dict[str, str]
