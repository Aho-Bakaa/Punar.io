from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..database.mock_db import db

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/transactions", response_model=dict)
async def get_all_transactions(limit: Optional[int] = Query(100, le=1000)):
    transactions = db.get_all_transactions()
    transactions.sort(key=lambda x: x.created_at, reverse=True)
    return {
        "success": True,
        "data": [t.model_dump() for t in transactions[:limit]],
        "total": len(transactions)
    }

@router.delete("/transactions/{transaction_id}", response_model=dict)
async def delete_transaction(transaction_id: str):
    deleted = db.delete_transaction(transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True, "message": "Transaction deleted successfully"}

@router.get("/audit-logs", response_model=dict)
async def get_audit_logs(limit: Optional[int] = Query(100, le=500)):
    logs = db.get_audit_logs(limit)
    return {
        "success": True,
        "data": [log.model_dump() for log in logs],
        "total": len(logs)
    }

@router.get("/dashboard", response_model=dict)
async def get_dashboard_stats():
    transactions = db.get_all_transactions()
    stats = {
        "total_transactions": len(transactions),
        "pending": len([t for t in transactions if t.status == "PENDING"]),
        "settled": len([t for t in transactions if t.status == "SETTLED"]),
        "failed": len([t for t in transactions if t.status == "FAILED"]),
        "cancelled": len([t for t in transactions if t.status == "CANCELLED"]),
        "total_points_issued": sum(t.points for t in transactions if t.status == "SETTLED"),
        "banks": {}
    }
    
    for transaction in transactions:
        if transaction.bank not in stats["banks"]:
            stats["banks"][transaction.bank] = {"count": 0, "points": 0}
        stats["banks"][transaction.bank]["count"] += 1
        if transaction.status == "SETTLED":
            stats["banks"][transaction.bank]["points"] += transaction.points
    
    return {"success": True, "data": stats}