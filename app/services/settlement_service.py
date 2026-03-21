import asyncio
import random
import httpx
from datetime import datetime
from typing import Optional
from ..config import settings
from ..database.mock_db import db
from ..utils.logger import logger
from ..utils.signatures import generate_signature

class SettlementService:
    def __init__(self):
        self.scheduled_jobs: dict = {}
        self.success_rate = settings.SUCCESS_RATE
        self.min_delay = settings.SETTLEMENT_DELAY_MIN / 1000
        self.max_delay = settings.SETTLEMENT_DELAY_MAX / 1000
        
    async def schedule_settlement(self, transaction_id: str, points: int, card):
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"Scheduling settlement for {transaction_id} in {delay:.2f} seconds")
        
        task = asyncio.create_task(
            self._process_settlement_delayed(transaction_id, points, card, delay)
        )
        self.scheduled_jobs[transaction_id] = task
        task.add_done_callback(lambda t: self.scheduled_jobs.pop(transaction_id, None))
        return task
    
    async def _process_settlement_delayed(self, transaction_id: str, points: int, card, delay: float):
        await asyncio.sleep(delay)
        await self.process_settlement(transaction_id, points, card)
    
    async def process_settlement(self, transaction_id: str, points: int, card):
        try:
            is_success = random.random() < self.success_rate
            transaction = db.get_transaction(transaction_id)
            
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found")
                return
            
            if transaction.status != "PENDING":
                logger.info(f"Transaction {transaction_id} already {transaction.status}, skipping")
                return
            
            settlement_data = {
                "transaction_id": transaction_id,
                "status": "SUCCESS" if is_success else "FAILED",
                "points": points,
                "card_last4": card.last4,
                "failure_reason": None if is_success else self._get_random_failure_reason()
            }
            
            db.create_settlement(settlement_data)
            db.update_transaction(transaction_id, {
                "status": "SETTLED" if is_success else "FAILED",
                "settled_at": datetime.utcnow(),
                "failure_reason": settlement_data["failure_reason"]
            })
            
            logger.info(f"Transaction {transaction_id} settled: {'SUCCESS' if is_success else 'FAILED'}")
            await self._send_webhook(transaction_id, is_success, settlement_data)
            
        except Exception as e:
            logger.error(f"Error processing settlement for {transaction_id}: {e}")
            await self._handle_settlement_failure(transaction_id, points, card)
    
    async def _handle_settlement_failure(self, transaction_id: str, points: int, card):
        transaction = db.get_transaction(transaction_id)
        if not transaction:
            return
        
        retry_count = transaction.retry_count + 1
        db.update_transaction(transaction_id, {"retry_count": retry_count})
        
        if retry_count <= 3:
            backoff_delay = min(30, 2 ** retry_count * 5)
            logger.info(f"Rescheduling {transaction_id} in {backoff_delay}s (attempt {retry_count})")
            await asyncio.sleep(backoff_delay)
            await self.process_settlement(transaction_id, points, card)
        else:
            db.update_transaction(transaction_id, {
                "status": "FAILED",
                "failure_reason": "Max retries exceeded"
            })
            logger.error(f"Transaction {transaction_id} failed after {retry_count} retries")
    
    async def _send_webhook(self, transaction_id: str, is_success: bool, settlement_data: dict):
        if not settings.WEBHOOK_URL:
            logger.warning("No webhook URL configured")
            return
        
        transaction = db.get_transaction(transaction_id)
        if not transaction:
            return
        
        payload = {
            "event": "points_settled" if is_success else "points_failed",
            "transaction_id": transaction.id,
            "bank_transaction_id": transaction.bank_transaction_id,
            "reference_id": transaction.reference_id,
            "points": transaction.points,
            "status": "SETTLED" if is_success else "FAILED",
            "settlement_time": settlement_data["settled_at"].isoformat() if is_success else None,
            "failure_reason": settlement_data.get("failure_reason"),
            "card_last4": transaction.card_last4,
            "bank": transaction.bank
        }
        
        signature = generate_signature(payload, settings.API_SECRET_KEY)
        
        try:
            logger.info(f"Sending webhook for {transaction_id}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.WEBHOOK_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Bank-Code": settings.MOCK_BANK_CODE
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Webhook sent successfully for {transaction_id}")
                    db.update_transaction(transaction_id, {
                        "webhook_sent": True,
                        "webhook_sent_at": datetime.utcnow()
                    })
                else:
                    logger.warning(f"Webhook returned {response.status_code} for {transaction_id}")
                    
        except Exception as e:
            logger.error(f"Failed to send webhook for {transaction_id}: {e}")
            await asyncio.sleep(10)
            await self._send_webhook(transaction_id, is_success, settlement_data)
    
    def cancel_settlement(self, transaction_id: str):
        if transaction_id in self.scheduled_jobs:
            self.scheduled_jobs[transaction_id].cancel()
            del self.scheduled_jobs[transaction_id]
            logger.info(f"Cancelled settlement for {transaction_id}")
    
    def _get_random_failure_reason(self) -> str:
        reasons = [
            "Insufficient reward points balance",
            "Card not eligible for this merchant",
            "Transaction limit exceeded",
            "Card reported lost/stolen",
            "Technical error at bank end",
            "Duplicate transaction detected"
        ]
        return random.choice(reasons)

settlement_service = SettlementService()