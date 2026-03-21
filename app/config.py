from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server Configuration
    APP_NAME: str = "Credit Card Reward System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 3001
    
    # Mock Bank Configuration
    MOCK_BANK_NAME: str = "EcoReward Bank"
    MOCK_BANK_CODE: str = "ERB"
    SETTLEMENT_DELAY_MIN: int = 5000
    SETTLEMENT_DELAY_MAX: int = 10000
    SUCCESS_RATE: float = 0.95
    
    # Merchant Configuration
    MERCHANT_ID: str = "EWASTE_PLATFORM_001"
    API_SECRET_KEY: str = "your-mock-secret-key-here-change-in-production"
    
    # Webhook Configuration
    WEBHOOK_URL: str = "http://localhost:8000/api/webhooks/bank"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()