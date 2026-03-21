from datetime import datetime
from typing import Dict, Any, List
from ..config import settings
from ..database.mock_db import db
from ..utils.logger import logger
from .settlement_service import settlement_service

class BankService:
    
    async def issue_reward_points(
        self, 
        card_token: str, 
        points: int, 
        merchant_id: str, 
        reference_id: str, 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        
        try:
            card = db.get_user_card(card_token)
            if not card:
                return {
                    "success": False,
                    "error": "INVALID_CARD",
                    "message": "Card not found or invalid"
                }
            
            if not card.eligible:
                return {
                    "success": False,
                    "error": "CARD_NOT_ELIGIBLE",
                    "message": "This card is not eligible for reward points"
                }
            
            if points > card.limit:
                return {
                    "success": False,
                    "error": "LIMIT_EXCEEDED",
                    "message": f"Points exceed card limit of {card.limit}"
                }
            
            existing = db.get_transaction_by_reference(reference_id)
            if existing:
                return {
                    "success": True,
                    "data": {
                        "transaction_id": existing.id,
                        "bank_transaction_id": existing.bank_transaction_id,
                        "status": existing.status,
                        "message": "Transaction already exists",
                        "card_last4": card.last4,
                        "bank": card.bank,
                        "is_duplicate": True
                    }
                }
            
            transaction_data = {
                "card_token": card_token,
                "card_last4": card.last4,
                "bank": card.bank,
                "points": points,
                "merchant_id": merchant_id,
                "reference_id": reference_id,
                "metadata": metadata or {}
            }
            
            transaction = db.create_transaction(transaction_data)
            logger.info(f"Points request created: {transaction.id} for {points} points")
            
            await settlement_service.schedule_settlement(transaction.id, points, card)
            
            return {
                "success": True,
                "data": {
                    "transaction_id": transaction.id,
                    "bank_transaction_id": transaction.bank_transaction_id,
                    "status": transaction.status,
                    "message": "Points request submitted successfully",
                    "estimated_settlement_time": self._get_estimated_settlement_time(),
                    "card_last4": card.last4,
                    "bank": card.bank
                }
            }
            
        except Exception as e:
            logger.error(f"Error issuing reward points: {e}")
            return {
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": "An internal error occurred"
            }
    
    async def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        transaction = db.get_transaction(transaction_id)
        
        if not transaction:
            return {
                "success": False,
                "error": "TRANSACTION_NOT_FOUND",
                "message": "Transaction not found"
            }
        
        settlement = db.get_settlement(transaction_id)
        
        return {
            "success": True,
            "data": {
                "transaction_id": transaction.id,
                "bank_transaction_id": transaction.bank_transaction_id,
                "status": transaction.status,
                "points": transaction.points,
                "card_last4": transaction.card_last4,
                "bank": transaction.bank,
                "created_at": transaction.created_at.isoformat(),
                "settled_at": transaction.settled_at.isoformat() if transaction.settled_at else None,
                "failure_reason": transaction.failure_reason,
                "reference_id": transaction.reference_id,
                "settlement_details": settlement.model_dump() if settlement else None
            }
        }
    
    async def cancel_transaction(self, transaction_id: str, reason: str = None) -> Dict[str, Any]:
        transaction = db.get_transaction(transaction_id)
        
        if not transaction:
            return {
                "success": False,
                "error": "TRANSACTION_NOT_FOUND",
                "message": "Transaction not found"
            }
        
        if transaction.status != "PENDING":
            return {
                "success": False,
                "error": "INVALID_STATUS",
                "message": f"Cannot cancel transaction in {transaction.status} status"
            }
        
        settlement_service.cancel_settlement(transaction_id)
        db.update_transaction(transaction_id, {
            "status": "CANCELLED",
            "failure_reason": reason or "Cancelled by merchant"
        })
        
        logger.info(f"Transaction {transaction_id} cancelled: {reason}")
        
        return {
            "success": True,
            "data": {
                "transaction_id": transaction.id,
                "status": "CANCELLED",
                "message": "Transaction cancelled successfully"
            }
        }
    
    def _get_estimated_settlement_time(self) -> Dict[str, Any]:
        avg_delay = (settings.SETTLEMENT_DELAY_MIN + settings.SETTLEMENT_DELAY_MAX) / 2000
        return {
            "milliseconds": avg_delay * 1000,
            "human_readable": f"{avg_delay:.1f} seconds",
            "min": f"{settings.SETTLEMENT_DELAY_MIN / 1000}s",
            "max": f"{settings.SETTLEMENT_DELAY_MAX / 1000}s"
        }
    
    def get_supported_banks(self) -> List[Dict[str, Any]]:
        return db.get_supported_banks()

bank_service = BankService()