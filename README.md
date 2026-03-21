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

### Example request

```powershell
curl -X POST "http://127.0.0.1:8000/v1/process-bill" ^
  -F "image=@sample_bill.jpg" ^
  -F "collection_mode=PICKUP" ^
  -F "processing_track=REFURB"
```

Webapp note:

- Send `multipart/form-data` using `FormData`.
- Do not manually set the `Content-Type` header in fetch/axios; let the browser set it with boundary.
- Supported file extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.heic`, `.heif`.

## Troubleshooting (Windows + PaddleOCR)

If you see DLL or scipy import errors (for example `_cobyla` / paging file too small):

```powershell
pip uninstall -y paddleocr paddlepaddle scipy scikit-learn
pip install --no-cache-dir "numpy<2.0.0" "opencv-python==4.6.0.66" "paddlepaddle==2.6.2" "paddleocr==2.7.3"
```

If memory pressure persists, increase Windows virtual memory (paging file), then restart terminal and server.

If requests return 503 due model download/init issues, pre-download and prewarm models:

```powershell
$env:PADDLEOCR_HOME="$HOME\.paddleocr"
python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', show_log=False); print('Paddle models ready')"
```

Manual model path support in this app:

- `~/.paddleocr/whl/det/en/en_PP-OCRv3_det_infer`
- `~/.paddleocr/whl/rec/en/en_PP-OCRv3_rec_infer`
- `~/.paddleocr/whl/cls/ch_ppocr_mobile_v2.0_cls_infer`

If `.tar` files are present in those directories, the service auto-extracts them on startup.

If a model archive is corrupted or partially downloaded, it will be renamed to `.bad` automatically.
Re-download that tar file and retry.

Use OCR diagnostic endpoint:

- `GET /health/ocr`
- returns `ocr_ready` and the exact backend error string when initialization fails

## Next accuracy upgrades

- Add vendor-specific templates for top supplier layouts.
- Add table structure recovery for complex line-item grids.
- Add active learning loop from manual review corrections.
- Add optional LLM fallback only for unresolved fields.
