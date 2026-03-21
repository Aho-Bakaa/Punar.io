from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..services.settlement_service import settlement_service
from ..database.mock_db import db

router = APIRouter(prefix="/api/webhooks/simulate", tags=["Webhook Simulation"])

class SimulateSettlementRequest(BaseModel):
    transaction_id: str
    force_success: bool = True

class SimulateFailureRequest(BaseModel):
    transaction_id: str
    reason: Optional[str] = None

@router.post("/settlement", response_model=dict)
async def simulate_settlement(request: SimulateSettlementRequest):
    transaction = db.get_transaction(request.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    settlement_service.cancel_settlement(request.transaction_id)
    card = db.get_user_card(transaction.card_token)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if request.force_success:
        await settlement_service.process_settlement(
            request.transaction_id, transaction.points, card
        )
        status_result = "SETTLED"
    else:
        settlement_data = {
            "transaction_id": request.transaction_id,
            "status": "FAILED",
            "points": transaction.points,
            "card_last4": card.last4,
            "failure_reason": "Manually triggered failure"
        }
        db.create_settlement(settlement_data)
        db.update_transaction(request.transaction_id, {
            "status": "FAILED",
            "settled_at": settlement_data["settled_at"],
            "failure_reason": settlement_data["failure_reason"]
        })
        await settlement_service._send_webhook(request.transaction_id, False, settlement_data)
        status_result = "FAILED"
    
    return {
        "success": True,
        "message": f"Settlement simulated for {request.transaction_id}",
        "status": status_result
    }

@router.post("/failure", response_model=dict)
async def simulate_failure(request: SimulateFailureRequest):
    transaction = db.get_transaction(request.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    settlement_service.cancel_settlement(request.transaction_id)
    db.update_transaction(request.transaction_id, {
        "status": "FAILED",
        "failure_reason": request.reason or "Manual failure simulation"
    })
    
    return {
        "success": True,
        "message": f"Transaction {request.transaction_id} marked as failed"
    }