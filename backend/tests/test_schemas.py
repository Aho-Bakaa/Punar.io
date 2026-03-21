import pytest


def test_schema_valid_device_submitted():
    from app.schemas.dto import DeviceSubmittedPayload
    
    payload_dict = {
        "device_id": "DEV-999",
        "imei_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "device_category": "smartphone",
        "brand": "Samsung",
        "model": "Galaxy S23",
        "self_reported_grade": "A",
        "collection_mode": "pickup",
        "submission_timestamp": "2026-03-22T10:00:00Z",
        "user_id_hash": "a1b2c3d4e5f6g7h8"
    }
    
    # This should pass without raising a ValidationError
    obj = DeviceSubmittedPayload(**payload_dict)
    assert obj.device_category == "smartphone"
    assert obj.self_reported_grade == "A"

def test_schema_invalid_enum_rejected():
    from app.schemas.dto import DeviceSubmittedPayload
    from pydantic import ValidationError
    
    payload_dict = {
        "device_id": "DEV-999",
        "imei_hash": "e3b0c4429",
        "device_category": "smart-tv", # Invalid enum value
        "brand": "Samsung",
        "model": "Galaxy S23",
        "self_reported_grade": "A+", # Invalid enum value
        "collection_mode": "delivery", # Invalid enum value
        "submission_timestamp": "2026-03-22",
        "user_id_hash": "a1b2c3d4"
    }
    
    with pytest.raises(ValidationError) as exc_info:
        DeviceSubmittedPayload(**payload_dict)
    
    assert "device_category" in str(exc_info.value)
    assert "self_reported_grade" in str(exc_info.value)
    assert "collection_mode" in str(exc_info.value)

def test_schema_negative_numbers_rejected():
    from app.schemas.dto import DeviceDroppedOffPayload
    from pydantic import ValidationError
    
    payload_dict = {
        "device_id": "DEV-999",
        "partner_shop_id": "SHOP-123",
        "agent_id": "AGENT-456",
        "imei_verified": True,
        "kyc_verified": True,
        "weight_grams": -500, # Invalid: must be positive
        "intake_timestamp": "2026-03-22T10:00:00Z",
        "accessories_included": []
    }
    
    with pytest.raises(ValidationError) as exc_info:
        DeviceDroppedOffPayload(**payload_dict)
        
    assert "weight_grams" in str(exc_info.value)

def test_schema_grading_checklist():
    from app.schemas.dto import DeviceGradedPayload
    from pydantic import ValidationError
    
    payload_dict = {
        "device_id": "DEV-999",
        "partner_shop_id": "SHOP-123",
        "checklist_responses": {
            "powers_on": True,
            "screen_cracked": False,
            "touchscreen_works": True,
            "missing_parts": False,
            "battery_swollen": False,
            "ports_functional": True,
            "wifi_connects": True
        },
        "final_grade": "A",
        "grading_timestamp": "2026-03-22T12:00:00Z",
        "technician_id": "TECH-1"
    }
    
    # Should work
    obj = DeviceGradedPayload(**payload_dict)
    assert obj.checklist_responses.screen_cracked is False
    
    # Missing field in nested model should fail
    del payload_dict["checklist_responses"]["wifi_connects"]
    with pytest.raises(ValidationError):
        DeviceGradedPayload(**payload_dict)
