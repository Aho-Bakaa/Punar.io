import hmac
import hashlib
import json
from typing import Dict, Any

def generate_signature(payload: Dict[str, Any], secret_key: str) -> str:
    sorted_payload = dict(sorted(payload.items()))
    stringified = json.dumps(sorted_payload, separators=(',', ':'))
    
    return hmac.new(
        secret_key.encode('utf-8'),
        stringified.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_signature(payload: Dict[str, Any], signature: str, secret_key: str) -> bool:
    expected_signature = generate_signature(payload, secret_key)
    return hmac.compare_digest(signature, expected_signature)