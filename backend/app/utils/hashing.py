"""Deterministic SHA-256 hashing for event payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Return the hex SHA-256 digest of a canonically-serialised payload.

    The payload dict is serialised to JSON with sorted keys, no extra
    whitespace, and UTF-8 encoding.  This guarantees deterministic output
    so that the same logical payload always produces the same hash —
    critical for on-chain verification.
    """

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_to_bytes32(hex_digest: str) -> bytes:
    """Convert a 64-char hex SHA-256 digest to a 32-byte value for Solidity ``bytes32``."""

    return bytes.fromhex(hex_digest)
