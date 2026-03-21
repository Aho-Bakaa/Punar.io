import pytest
import asyncio
from app.utils.retry import retry_async

@pytest.mark.asyncio
async def test_retry_success_first_try():
    call_count = 0
    
    async def always_succeeds():
        nonlocal call_count
        call_count += 1
        return "success"
        
    result = await retry_async(always_succeeds, retries=3, base_delay_seconds=0.1)
    
    assert result == "success"
    assert call_count == 1

@pytest.mark.asyncio
async def test_retry_success_after_failure():
    call_count = 0
    
    async def succeeds_on_third_try():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Failed iteration " + str(call_count))
        return "finally"
        
    # Set delays very short for tests
    result = await retry_async(succeeds_on_third_try, retries=3, base_delay_seconds=0.01)
    
    assert result == "finally"
    assert call_count == 3

@pytest.mark.asyncio
async def test_retry_exhaustion():
    call_count = 0
    
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Intentional failure")
        
    with pytest.raises(ValueError) as exc_info:
        await retry_async(always_fails, retries=2, base_delay_seconds=0.01)
        
    assert "Intentional failure" in str(exc_info.value)
    # retries = 2 means 1 initial attempt + 2 retries = 3 total attempts
    assert call_count == 3
