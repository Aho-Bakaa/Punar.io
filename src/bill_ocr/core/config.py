from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime settings for OCR and validation thresholds."""

    min_ocr_word_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    min_field_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    amount_tolerance: float = Field(default=1.5, ge=0.0)
    default_currency: str = "INR"


settings = Settings()
