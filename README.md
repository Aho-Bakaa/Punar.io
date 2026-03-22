# OCR Bills - PaddleOCR Pipeline

This project implements a production-ready baseline for extracting structured bill data from uploaded bill photos.

## Accuracy-first design

- PaddleOCR-first extraction with confidence scores and bounding boxes.
- Image preprocessing for photo quality issues (deskew, denoise, contrast).
- Two-stage extraction: deterministic field parsing + confidence-aware normalization.
- Financial validation checks (subtotal + tax - discount ~= total, line-item sum checks).
- Manual review flags for low-confidence or inconsistent output.

## Features in this implementation

- API endpoint for single image bill extraction.
- Structured JSON output.
- Core fields plus line items.
- Reverse-logistics fields: collection mode, refurb/scrap track, grade, device category.
- Partner fields: recycler name, OEM mention, and ReCoins extraction when present.
- Confidence and validation report in the response.

## Quick start (Windows PowerShell)

1. Create and activate a virtual environment.
2. Install dependencies.
3. Start API server.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn bill_ocr.api.app:app --reload
```

For lower memory environments on Windows, prefer running without reload:

```powershell
uvicorn bill_ocr.api.app:app
```

## API

- POST `/v1/process-bill`
  - multipart form-data with file key: `image`
  - optional form fields:
    - `collection_mode`: `DROP_OFF` or `PICKUP`
    - `processing_track`: `REFURB` or `SCRAP`
  - returns: extraction JSON, confidence map, validation checks, review flags, and request context


## Future accuracy upgrades

- Add vendor-specific templates for top supplier layouts.
- Add table structure recovery for complex line-item grids.
- Add active learning loop from manual review corrections.
- Add optional LLM fallback only for unresolved fields.
