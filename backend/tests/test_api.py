import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
import os

os.environ["ENVIRONMENT"] = "test"

from main import app
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.models.entities import DeviceEvent, BlockchainDeadLetter
from app.core.config import settings
from app.services.blockchain_service import BlockchainService

# Setup an in-memory SQLite database for testing the endpoints
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """Create all tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_health_check():
    """Test the basic health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_device_submitted_endpoint():
    """Test the EVENT 1 (Device Submitted) endpoint."""
    
    payload = {
        "device_id": "TEST-DEV-001",
        "imei_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "device_category": "laptop",
        "brand": "Lenovo",
        "model": "ThinkPad",
        "self_reported_grade": "B",
        "collection_mode": "drop-off",
        "submission_timestamp": "2026-03-21T10:00:00Z",
        "user_id_hash": "a1b2c3d4e5f6g7h8"
    }

    async def _mock_log_event(self, device_id, event_type, payload_dict, wallet_role=None):
        return (
            "0x2222222222222222222222222222222222222222222222222222222222222222",
            "a" * 64,
        )

    original = BlockchainService.log_event
    BlockchainService.log_event = _mock_log_event

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/events/device-submitted", json=payload)
    finally:
        BlockchainService.log_event = original
        
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "TEST-DEV-001"
    assert data["event_type"] == "DEVICE_SUBMITTED"
    assert data["blockchain_status"] in ["QUEUED", "CONFIRMED"]
    assert "id" in data

@pytest.mark.asyncio
async def test_verify_endpoint_404():
    """Test verification endpoint for a non-existent device."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/verify/NON-EXISTENT-DEVICE")
        
    assert response.status_code == 404
    assert response.json() == {"detail": "Device not found"}


@pytest.mark.asyncio
async def test_admin_dead_letters_requires_key():
    """Admin dead-letter endpoint must require the X-Admin-Key header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/admin/dead-letters")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin key"}


@pytest.mark.asyncio
async def test_retry_dead_letter_success_updates_event():
    """Retrying a dead-letter should write tx/hash to the linked DeviceEvent and resolve the dead-letter."""

    async with TestingSessionLocal() as session:
        event = DeviceEvent(
            device_id="TEST-DEV-002",
            event_type="DEVICE_SUBMITTED",
            payload_json={"device_id": "TEST-DEV-002"},
            actor_wallet="0xabc",
            created_at=datetime.now(timezone.utc),
            blockchain_hash="oldhash",
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        dlq = BlockchainDeadLetter(
            device_id=event.device_id,
            event_type=event.event_type,
            payload_json=event.payload_json,
            wallet_role="PLATFORM_WALLET",
            error_message="simulated failure",
            retry_count=3,
            event_row_id=event.id,
        )
        session.add(dlq)
        await session.commit()
        await session.refresh(dlq)

    async def _mock_log_event(self, device_id, event_type, payload_dict, wallet_role=None):
        return (
            "0x1111111111111111111111111111111111111111111111111111111111111111",
            "f" * 64,
        )

    original = BlockchainService.log_event
    BlockchainService.log_event = _mock_log_event

    try:
        headers = {"X-Admin-Key": settings.admin_api_key}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/api/v1/admin/dead-letters/{dlq.id}/retry", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["event_type"] == "DEVICE_SUBMITTED"
        assert body["blockchain_status"] == "CONFIRMED"
    finally:
        BlockchainService.log_event = original

    async with TestingSessionLocal() as session:
        updated_event = await session.get(DeviceEvent, event.id)
        updated_dlq = await session.get(BlockchainDeadLetter, dlq.id)

        assert updated_event is not None
        assert updated_event.blockchain_tx_hash is not None
        assert updated_event.blockchain_hash == "f" * 64

        assert updated_dlq is not None
        assert updated_dlq.resolved_at is not None
