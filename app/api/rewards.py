from fastapi import APIRouter, HTTPException, status
from ..services.bank_service import bank_service
from ..utils.validators import IssuePointsRequest, CancelTransactionRequest
from ..config import settings

router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

@router.post("/issue", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def issue_points(request: IssuePointsRequest):
    if request.merchant_id != settings.MERCHANT_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid merchant ID"
        )
    
    result = await bank_service.issue_reward_points(
        card_token=request.card_token,
        points=request.points,
        merchant_id=request.merchant_id,
        reference_id=request.reference_id,
        metadata=request.metadata
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )
    
    return result

@router.get("/transaction/{transaction_id}", response_model=dict)
async def get_transaction_status(transaction_id: str):
    result = await bank_service.get_transaction_status(transaction_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result
        )
    
    return result

@router.post("/transaction/{transaction_id}/cancel", response_model=dict)
async def cancel_transaction(transaction_id: str, request: CancelTransactionRequest = None):
    reason = request.reason if request else None
    result = await bank_service.cancel_transaction(transaction_id, reason)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )
    
    return result

@router.get("/banks", response_model=dict)
async def get_supported_banks():
    banks = bank_service.get_supported_banks()
    return {"success": True, "data": banks}