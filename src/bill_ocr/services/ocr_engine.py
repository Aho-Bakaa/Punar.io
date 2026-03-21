from __future__ import annotations

import os
import tarfile
from functools import lru_cache
from pathlib import Path
from typing import List

from bill_ocr.core.config import settings
from bill_ocr.models.schemas import OCRWord


def _has_model_files(model_dir: Path) -> bool:
    if not model_dir.exists() or not model_dir.is_dir():
        return False
    return any(model_dir.glob("*.pdmodel")) and any(model_dir.glob("*.pdiparams"))


def _extract_if_needed(model_dir: Path) -> None:
    if _has_model_files(model_dir):
        return

    tar_candidates = [
        model_dir.with_suffix(".tar"),
        model_dir / f"{model_dir.name}.tar",
        model_dir.parent / f"{model_dir.name}.tar",
    ]

    for tar_path in tar_candidates:
        if not tar_path.exists():
            continue
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(path=model_dir.parent)
        except (tarfile.ReadError, EOFError, OSError):
            bad_tar = tar_path.with_suffix(tar_path.suffix + ".bad")
            try:
                tar_path.replace(bad_tar)
            except OSError:
                pass
            continue
        break


def _local_model_dirs() -> dict[str, str]:
    home = Path(os.environ.get("PADDLEOCR_HOME", str(Path.home() / ".paddleocr")))
    det_dir_en = home / "whl" / "det" / "en" / "en_PP-OCRv3_det_infer"
    det_dir_ch = home / "whl" / "det" / "ch" / "ch_PP-OCRv3_det_infer"
    rec_dir = home / "whl" / "rec" / "en" / "en_PP-OCRv3_rec_infer"
    cls_dir = home / "whl" / "cls" / "ch_ppocr_mobile_v2.0_cls_infer"

    for model_dir in (det_dir_en, det_dir_ch, rec_dir, cls_dir):
        _extract_if_needed(model_dir)

    kwargs: dict[str, str] = {}
    det_dir = det_dir_en if _has_model_files(det_dir_en) else det_dir_ch
    if _has_model_files(det_dir):
        kwargs["det_model_dir"] = str(det_dir)
    if _has_model_files(rec_dir):
        kwargs["rec_model_dir"] = str(rec_dir)
    if _has_model_files(cls_dir):
        kwargs["cls_model_dir"] = str(cls_dir)
    return kwargs


@lru_cache(maxsize=1)
def _get_ocr_engine():
    # Skip Paddle model-source connectivity checks in restricted/offline environments.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("PADDLEOCR_HOME", str(Path.home() / ".paddleocr"))
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        raise RuntimeError(
            "PaddleOCR backend is unavailable in this environment. "
            "Reinstall compatible paddle packages or use a larger paging file. "
            f"Original error: {exc}"
        ) from exc

    try:
        local_dirs = _local_model_dirs()
        return PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=False,
            show_log=False,
            **local_dirs,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize PaddleOCR models. "
            "Check system memory/pagefile, local model files in ~/.paddleocr, and paddle package compatibility. "
            f"Original error: {exc}"
        ) from exc


def _bbox_overlap(b1: List[List[float]], b2: List[List[float]]) -> float:
    """Return the IoU (intersection-over-union) of two quadrilateral bboxes
    using their axis-aligned bounding rectangles."""
    def _aabb(bbox):
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return min(xs), min(ys), max(xs), max(ys)

    x1a, y1a, x1b, y1b = _aabb(b1)
    x2a, y2a, x2b, y2b = _aabb(b2)

    ix_a = max(x1a, x2a)
    iy_a = max(y1a, y2a)
    ix_b = min(x1b, x2b)
    iy_b = min(y1b, y2b)

    if ix_b <= ix_a or iy_b <= iy_a:
        return 0.0

    intersection = (ix_b - ix_a) * (iy_b - iy_a)
    area1 = (x1b - x1a) * (y1b - y1a)
    area2 = (x2b - x2a) * (y2b - y2a)
    union = area1 + area2 - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def run_ocr(image) -> List[OCRWord]:
    """Run OCR on a single image and return filtered words."""
    result = _get_ocr_engine().ocr(image, cls=True)
    words: List[OCRWord] = []
    for page in result:
        if not page:
            continue
        for line in page:
            bbox = line[0]
            text, conf = line[1][0], float(line[1][1])
            if conf < settings.min_ocr_word_confidence:
                continue
            words.append(OCRWord(text=text.strip(), confidence=conf, bbox=bbox))
    return words


def run_ocr_multipass(images: list) -> List[OCRWord]:
    """Run OCR on multiple image variants and merge results.

    Deduplicates words from different passes using bounding-box IoU.
    Higher-confidence duplicates win.
    """
    all_words: List[OCRWord] = []

    for img in images:
        result = _get_ocr_engine().ocr(img, cls=True)
        for page in result:
            if not page:
                continue
            for line in page:
                bbox = line[0]
                text, conf = line[1][0], float(line[1][1])
                # Use a slightly lower threshold for secondary passes.
                min_conf = settings.min_ocr_word_confidence * 0.7
                if conf < min_conf:
                    continue
                all_words.append(
                    OCRWord(text=text.strip(), confidence=conf, bbox=bbox)
                )

    # Deduplicate: if two words overlap significantly, keep the higher-confidence one.
    if not all_words:
        return []

    # Sort by confidence descending so we greedily keep the best.
    all_words.sort(key=lambda w: w.confidence, reverse=True)
    kept: List[OCRWord] = []
    for w in all_words:
        is_dup = False
        for k in kept:
            if _bbox_overlap(w.bbox, k.bbox) > 0.4:
                is_dup = True
                break
        if not is_dup:
            kept.append(w)

    return kept
