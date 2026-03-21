import pytest
from app.utils.hashing import compute_payload_hash, hash_to_bytes32

def test_compute_payload_hash_deterministic():
    """Test that the same payload dictionaries always hash to the same value, regardless of key insertion order."""
    payload1 = {
        "device_id": "DEV-123",
        "event_type": "DEVICE_SUBMITTED",
        "submission_timestamp": "2026-03-21T10:00:00Z"
    }
    
    payload2 = {
        "event_type": "DEVICE_SUBMITTED",
        "submission_timestamp": "2026-03-21T10:00:00Z",
        "device_id": "DEV-123"
    }
    
    hash1 = compute_payload_hash(payload1)
    hash2 = compute_payload_hash(payload2)
    
    assert hash1 == hash2

def test_compute_payload_hash_different_values():
    """Test that changing a value produces a different hash."""
    payload1 = {
        "device_id": "DEV-123",
        "event_type": "DEVICE_SUBMITTED"
    }
    
    payload2 = {
        "device_id": "DEV-124",
        "event_type": "DEVICE_SUBMITTED"
    }
    
    hash1 = compute_payload_hash(payload1)
    hash2 = compute_payload_hash(payload2)
    
    assert hash1 != hash2

def test_hash_to_bytes32():
    """Test that the 64-character hex string converts to exactly 32 bytes."""
    payload = {"test": "data"}
    hex_hash = compute_payload_hash(payload)
    
    # 64 hex characters == 32 bytes
    assert len(hex_hash) == 64
    
    byte_hash = hash_to_bytes32(hex_hash)
    assert len(byte_hash) == 32
    assert byte_hash.hex() == hex_hash