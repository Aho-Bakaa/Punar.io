from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    DeviceProcessRequest, ReportGenerateRequest,
    DashboardResponse, DashboardSummary,
    AnalyzeSingleRequest, AnalyzeBatchRequest
)
from app.database.supabase_client import supabase_repo
from app.services.device_resolver import DeviceResolver
from app.services.weight_calculator import WeightCalculator
from app.services.report_generator import ReportGenerator
from app.services.analysis_engine import AnalysisEngine

app = FastAPI(title="EPR Compliance System - Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stateless analysis engine (uses CSV device_master, no Supabase)
analysis_engine = AnalysisEngine()


# ─── Health ───

@app.get("/")
async def root():
    return {
        "status": "EPR Dashboard API Active",
        "endpoints": {
            "analyze_device": "POST /api/analyze/device",
            "analyze_batch": "POST /api/analyze/batch",
            "process_device": "POST /api/process-device",
            "dashboard_json": "POST /api/dashboard/generate",
            "unprocessed": "GET /api/unprocessed-devices",
            "report_pdf": "POST /api/report/pdf",
            "reports": "GET /api/dashboard/reports"
        }
    }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "epr-compliance-system"}


# ═══════════════════════════════════════════════════════════════
#  NEW: Stateless analysis endpoints for the MongoDB webapp
#  → Send device data in request body, get EPR analysis back
#  → No Supabase reads or writes — the webapp stores its own results
# ═══════════════════════════════════════════════════════════════

@app.post("/api/analyze/device")
async def analyze_device(request: AnalyzeSingleRequest):
    """
    Analyze a single device — the MongoDB webapp sends device data directly.
    Returns: weight data + environmental impact + device resolution info.
    No data is persisted; the caller stores the results.
    """
    device_dict = request.device.model_dump()
    result = await analysis_engine.analyze_single_device(
        device_dict,
        override_channelization=request.override_channelization
    )
    return result


@app.post("/api/analyze/batch")
async def analyze_batch(request: AnalyzeBatchRequest):
    """
    Analyze multiple devices — the MongoDB webapp sends a list of devices.
    Returns: summary + per-device details + state/category breakdowns.
    Equivalent to dashboard/generate but fully stateless.
    """
    devices_list = [d.model_dump() for d in request.devices]

    if not devices_list:
        raise HTTPException(400, "No devices provided")

    result = await analysis_engine.analyze_batch(
        devices_list,
        producer_name=request.producer_name,
        producer_cpcb_reg=request.producer_cpcb_reg or "PENDING-REG",
        reporting_period=request.reporting_period
    )

    if not result["summary"]:
        raise HTTPException(404, "No devices to analyze")

    return result


# ═══════════════════════════════════════════════════════════════
#  EXISTING: Supabase-based endpoints (kept for backward compat)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/unprocessed-devices")
async def get_unprocessed():
    """Get devices waiting to be processed"""
    devices = await supabase_repo.get_unprocessed_devices()
    return {
        "count": len(devices),
        "devices": [{"id": d["id"], "model": d.get("model"), "condition": d.get("condition"), 
                    "brand": d.get("brand")} for d in devices]
    }

@app.post("/api/process-device")
async def process_device(request: DeviceProcessRequest):
    """
    Process single device (returns JSON only, no recoins)
    """
    device = await supabase_repo.get_existing_device(request.device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    
    resolver = DeviceResolver(supabase_repo)
    resolved = await resolver.resolve_device(device)
    
    calc = WeightCalculator()
    channelization = request.override_channelization or calc.determine_channelization(
        device.get('condition', 'Working'),
        device.get('recycler_name')
    )
    
    weight_calc = calc.calculate_accountable_weight(
        resolved['total_weight_kg'],
        device.get('condition', 'Working'),
        channelization
    )
    
    materials = calc.calculate_materials(
        weight_calc['accountable_weight_kg'],
        resolved.get('gold_g_per_ton', 0),
        resolved.get('copper_kg_per_ton', 0)
    )
    
    # Calculate carbon
    carbon_factor = resolved.get('carbon_saved_per_kg', 300)
    carbon_saved = weight_calc['accountable_weight_kg'] * carbon_factor
    
    record = {
        'source_device_id': device['id'],
        'device_master_id': resolved.get('device_master_id'),
        'collection_state': request.collection_state or device.get('collection_state', 'Unknown'),
        'resolved_category': resolved['category_code'],
        'condition_assessment': device.get('condition', 'Working'),
        'channelization_type': channelization,
        'standard_weight_kg': weight_calc['standard_weight_kg'],
        'condition_factor': weight_calc['condition_factor'],
        'accountable_weight_kg': weight_calc['accountable_weight_kg'],
        'estimated_gold_g': materials['gold_g'],
        'estimated_copper_kg': materials['copper_kg'],
        'estimated_lithium_kg': materials.get('lithium_kg', 0),
        'carbon_avoided_kg': carbon_saved
    }
    
    processed_id = await supabase_repo.save_processed_device(record)
    
    return {
        "processed_id": processed_id,
        "device": {
            "id": device['id'],
            "model": resolved['model'],
            "brand": resolved['brand'],
            "category": resolved['category_code']
        },
        "weight_data": {
            "standard_kg": weight_calc['standard_weight_kg'],
            "accountable_kg": weight_calc['accountable_weight_kg'],
            "channelization": channelization
        },
        "environmental_impact": {
            "carbon_avoided_kg": round(carbon_saved, 2),
            "gold_g": materials['gold_g'],
            "copper_kg": materials['copper_kg'],
            "lithium_kg": materials.get('lithium_kg', 0)
        }
    }

@app.post("/api/dashboard/generate", response_model=DashboardResponse)
async def generate_dashboard(request: ReportGenerateRequest):
    """
    Generate JSON dashboard data for your teammate's frontend
    Returns: Summary + Device List + Breakdowns
    """
    generator = ReportGenerator(supabase_repo)
    
    result = await generator.generate_dashboard_data(
        request.producer_name,
        request.producer_cpcb_reg or "PENDING-REG",
        request.reporting_period
    )
    
    if not result["summary"]:
        raise HTTPException(404, "No unprocessed devices found")
    
    return DashboardResponse(
        summary=DashboardSummary(**result["summary"]),
        devices=result["devices"],
        state_breakdown=result["state_breakdown"],
        category_breakdown=result["category_breakdown"]
    )

@app.post("/api/report/pdf")
async def generate_pdf_report(request: ReportGenerateRequest):
    """
    Optional: Generate PDF for CPCB manual upload
    """
    generator = ReportGenerator(supabase_repo)
    
    # First generate dashboard data (processes devices)
    data = await generator.generate_dashboard_data(
        request.producer_name,
        request.producer_cpcb_reg or "PENDING-REG",
        request.reporting_period
    )
    
    if not data["summary"]:
        raise HTTPException(404, "No devices to report")
    
    # Generate PDF
    pdf_path = await generator.generate_pdf_report(data["report_id"], data)
    
    return {
        "report_id": data["report_id"],
        "pdf_url": pdf_path,
        "summary": data["summary"]
    }

@app.get("/api/dashboard/reports")
async def list_reports():
    """Get all generated reports (for dashboard history)"""
    result = supabase_repo.client.table('epr_reports').select('*').order('generated_at', desc=True).execute()
    return {"reports": result.data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)