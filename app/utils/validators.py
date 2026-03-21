from typing import Optional
from pydantic import BaseModel, Field, validator

class IssuePointsRequest(BaseModel):
    card_token: str = Field(..., min_length=8, max_length=50)
    points: int = Field(..., gt=0, le=100000)
    merchant_id: str = Field(..., min_length=3)
    reference_id: str = Field(..., min_length=1)
    metadata: Optional[dict] = Field(default_factory=dict)
    
    @validator('card_token')
    def validate_card_token(cls, v):
        if not v.startswith('tok_'):
            raise ValueError('Invalid card token format')
        return v

class CancelTransactionRequest(BaseModel):
    reason: Optional[str] = Field(default="Cancelled by merchant", max_length=200)