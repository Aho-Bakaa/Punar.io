"""Spatial line reconstruction for OCR word fragments.

PaddleOCR often returns individual word/phrase bounding boxes that need
to be assembled into logical *lines* before structured field extraction
can work reliably.  This module clusters OCR words by vertical position
and sorts them left-to-right to reconstruct the reading order.
"""

from __future__ import annotations

from typing import List

from bill_ocr.models.schemas import OCRWord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mid_y(word: OCRWord) -> float:
    """Return the vertical midpoint of a word's bounding box."""
    ys = [pt[1] for pt in word.bbox]
    return (min(ys) + max(ys)) / 2.0


def _min_x(word: OCRWord) -> float:
    """Return the leftmost x-coordinate of a word's bounding box."""
    return min(pt[0] for pt in word.bbox)


def _height(word: OCRWord) -> float:
    ys = [pt[1] for pt in word.bbox]
    return max(ys) - min(ys)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def group_words_into_lines(
    words: List[OCRWord],
    y_overlap_ratio: float = 0.5,
) -> List[List[OCRWord]]:
    """Cluster *words* into horizontal lines based on Y-overlap.

    Two words are considered part of the same line when the vertical
    distance between their midpoints is less than ``y_overlap_ratio``
    times the average height of the two words.

    Returns a list of lines, each line being a list of :class:`OCRWord`
    sorted left-to-right.  Lines themselves are sorted top-to-bottom.
    """
    if not words:
        return []

    # Sort by vertical position first (top to bottom).
    sorted_words = sorted(words, key=_mid_y)

    lines: List[List[OCRWord]] = []
    current_line: List[OCRWord] = [sorted_words[0]]

    for word in sorted_words[1:]:
        # Compare with the *average* mid-y of the current line cluster.
        avg_mid_y = sum(_mid_y(w) for w in current_line) / len(current_line)
        avg_h = sum(_height(w) for w in current_line) / len(current_line)
        h = _height(word)
        threshold = y_overlap_ratio * max(avg_h, h, 1.0)

        if abs(_mid_y(word) - avg_mid_y) <= threshold:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]

    if current_line:
        lines.append(current_line)

    # Sort words within each line left-to-right.
    for line in lines:
        line.sort(key=_min_x)

    return lines


def lines_to_text(lines: List[List[OCRWord]]) -> List[str]:
    """Join each spatial line's words into a single string."""
    result: List[str] = []
    for line in lines:
        text = " ".join(w.text for w in line if w.text)
        if text.strip():
            result.append(text.strip())
    return result
