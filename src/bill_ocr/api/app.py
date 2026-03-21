from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from bill_ocr.models.schemas import ExtractionResponse
from bill_ocr.services.ocr_engine import _get_ocr_engine, _local_model_dirs
from bill_ocr.services.pipeline import process_bill_image

app = FastAPI(title="Bill OCR API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ocr")
def health_ocr() -> dict[str, str | bool | dict[str, str]]:
    local_dirs = _local_model_dirs()
    try:
        _get_ocr_engine()
        return {
            "status": "ok",
            "ocr_ready": True,
            "local_model_dirs": local_dirs,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "ocr_ready": False,
            "local_model_dirs": local_dirs,
            "error": str(exc),
        }


@app.post("/v1/process-bill", response_model=ExtractionResponse)
async def process_bill(
    image: UploadFile = File(...),
    collection_mode: str | None = Form(default=None),
    processing_track: str | None = Form(default=None),
) -> ExtractionResponse:
    if not image.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    content_type = (image.content_type or "").lower()
    filename = (image.filename or "").lower()
    allowed_types = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/heic",
        "image/heif",
        "application/octet-stream",
    }
    allowed_ext = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif")

    valid_by_type = content_type in allowed_types if content_type else False
    valid_by_ext = filename.endswith(allowed_ext)
    if not (valid_by_type or valid_by_ext):
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported upload type. Send multipart/form-data with an image file "
                "(png/jpg/jpeg/webp/heic)."
            ),
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        return process_bill_image(
            image_bytes=image_bytes,
            declared_collection_mode=collection_mode,
            declared_track=processing_track,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc
