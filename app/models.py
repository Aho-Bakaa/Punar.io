from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class DeviceProcessRequest(BaseModel):
    device_id: str
    collection_state: Optional[str] = "Unknown"
    override_channelization: Optional[str] = None

class ReportGenerateRequest(BaseModel):
    producer_name: str
    producer_cpcb_reg: Optional[str] = "PENDING-REG"
    reporting_period: str  # Q1-2026

class DashboardSummary(BaseModel):
    # Core metrics
    total_devices: int
    total_weight_kg: float
    refurbishment_weight_kg: float
    recycling_weight_kg: float
    
    # CPCB Compliance metrics
    target_required_kg: float  # 70% of total
    compliance_percentage: float
    
    # Environmental impact
    carbon_avoided_kg: float
    total_gold_g: float
    total_copper_kg: float
    total_lithium_kg: float
    
    # Metadata
    producer_name: str
    reporting_period: str
    generated_at: datetime
    
class DeviceDetail(BaseModel):
    id: str
    source_device_id: str
    model: str
    brand: str
    category_code: str
    condition: str
    channelization_type: str
    accountable_weight_kg: float
    collection_state: str
    estimated_gold_g: float
    estimated_copper_kg: float
    processed_at: datetime

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    devices: List[DeviceDetail]
    state_breakdown: Dict[str, dict]
    category_breakdown: Dict[str, dict]


# ─── New models for stateless /api/analyze/* endpoints ───

class DeviceInput(BaseModel):
    """Single device sent by the MongoDB webapp for EPR analysis."""
    device_id: str
    model: Optional[str] = None
    brand: Optional[str] = None
    device_type: Optional[str] = None
    imei: Optional[str] = None
    condition: Optional[str] = "Working"
    collection_state: Optional[str] = "Unknown"
    recycler_name: Optional[str] = None

class AnalyzeSingleRequest(BaseModel):
    """POST /api/analyze/device — analyze one device."""
    device: DeviceInput
    override_channelization: Optional[str] = None

class AnalyzeBatchRequest(BaseModel):
    """POST /api/analyze/batch — analyze multiple devices + get dashboard."""
    devices: List[DeviceInput]
    producer_name: str
    producer_cpcb_reg: Optional[str] = "PENDING-REG"
    reporting_period: str  # e.g. "Q1-2026"