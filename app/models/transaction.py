from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Transaction(BaseModel):
    id: str
    bank_transaction_id: str
    card_token: str
    card_last4: str
    bank: str
    points: int
    merchant_id: str
    reference_id: str
    status: TransactionStatus = TransactionStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    webhook_sent: bool = False
    webhook_sent_at: Optional[datetime] = None

class Settlement(BaseModel):
    id: str
    transaction_id: str
    status: str
    points: int
    card_last4: str
    settled_at: datetime
    failure_reason: Optional[str] = None

class UserCard(BaseModel):
    card_token: str
    last4: str
    bank: str
    eligible: bool = True
    limit: int = 50000
    cardholder_name: Optional[str] = None
    
class AuditLog(BaseModel):
    id: str
    type: str
    transaction_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)