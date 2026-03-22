# Device Passport API (FastAPI + Polygon Amoy)

This repository implements a blockchain-anchored event logging backend for the ReCircle device lifecycle flow.

The API stores full event payloads in SQL and anchors deterministic SHA-256 payload hashes on Polygon Amoy through the `DevicePassport` smart contract.

## What This Codebase Contains

- FastAPI backend for device and batch lifecycle events.
- SQLAlchemy async models for event history and blockchain dead-letter retries.
- Web3 service for on-chain writes and verification reads.
- Solidity contract that emits immutable indexed event logs.
- Hardhat deployment scripts for Polygon Amoy.
- Docker compose setup for backend + PostgreSQL.
- Test suite for API/security/hash/retry behavior.

## High-Level Flow

1. Client calls an event endpoint with JSON payload and role-specific actor key.
2. API validates payload with Pydantic.
3. API inserts event row in DB immediately.
4. API returns response (`QUEUED` or `CONFIRMED` if tx is already attached).
5. Background task writes event hash on-chain.
6. On success, tx hash and blockchain hash are persisted.
7. On failure, a dead-letter entry is created for admin retry.

## Repository Layout

```text
data_sec/
    contracts/
        DevicePassport.sol
        DevicePassport.abi.json
    scripts/
        deploy.js
    backend/
        main.py
        requirements.txt
        Dockerfile
        app/
            api/routes/events.py
            core/config.py
            core/security.py
            db/base.py
            db/session.py
            models/entities.py
            schemas/dto.py
            services/blockchain_service.py
            utils/hashing.py
            utils/retry.py
        tests/
            test_api.py
            test_hashing.py
            test_retry.py
            test_schemas.py
            conftest.py
    hardhat.config.js
    docker-compose.yml
    package.json
```

## Stack

- API: FastAPI + Uvicorn
- Validation: Pydantic v2
- DB: SQLAlchemy async (`asyncpg` for Postgres, `aiosqlite` for local SQLite)
- Blockchain: web3.py
- Contract tooling: Hardhat + ethers
- Tests: pytest + pytest-asyncio

## Smart Contract Summary

Contract: `contracts/DevicePassport.sol`

- Stores owner and authorized caller addresses.
- Emits `EventLogged(deviceId, eventType, dataHash, actor, timestamp)`.
- Does not store lifecycle state, only emits immutable logs.
- Only authorized callers can emit events.
- Owner can grant/revoke caller authorization.

## API Base URL and Docs

- Local default: `http://127.0.0.1:8001` (or your chosen port)
- Health: `GET /health`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Authentication Model

### Required headers

- Event endpoints: `X-Actor-Key`
- Admin endpoints: `X-Admin-Key`

### Key-to-role mapping

Configured in environment variables:

- `PLATFORM_EVENT_API_KEY` -> `PLATFORM_WALLET`
- `PARTNER_EVENT_API_KEY` -> `PARTNER_WALLET`
- `AGENT_EVENT_API_KEY` -> `AGENT_WALLET`
- `RECYCLER_EVENT_API_KEY` -> `RECYCLER_WALLET`
- `ADMIN_API_KEY` -> admin operations

## Endpoints

### Public

- `GET /health`
- `GET /api/v1/verify/{device_id}`
- `GET /api/v1/passport/{device_id}`

### Event write endpoints (all `POST`, all require `X-Actor-Key`)

- `/api/v1/events/device-submitted` -> platform key
- `/api/v1/events/device-dropped-off` -> partner key
- `/api/v1/events/device-picked-up` -> agent key
- `/api/v1/events/device-graded` -> partner key
- `/api/v1/events/data-wiped` -> partner key
- `/api/v1/events/device-repaired` -> partner key
- `/api/v1/events/device-listed` -> partner key
- `/api/v1/events/device-sold` -> platform key
- `/api/v1/events/device-batched` -> partner key
- `/api/v1/events/batch-dispatched` -> platform key
- `/api/v1/events/recycler-acknowledged` -> recycler key
- `/api/v1/events/epr-certificate` -> platform key

### Admin

- `GET /api/v1/admin/dead-letters` (requires `X-Admin-Key`)
- `POST /api/v1/admin/dead-letters/{dead_letter_id}/retry` (requires `X-Admin-Key`)

## Request Payload Contracts

All payloads are defined in `backend/app/schemas/dto.py`.

### 1) `device-submitted`

```json
{
    "device_id": "string",
    "imei_hash": "string",
    "device_category": "smartphone|laptop|tablet|other",
    "brand": "string",
    "model": "string",
    "self_reported_grade": "A|B|C|Scrap",
    "collection_mode": "drop-off|pickup",
    "submission_timestamp": "string",
    "user_id_hash": "string"
}
```

### 2) `device-dropped-off`

```json
{
    "device_id": "string",
    "partner_shop_id": "string",
    "agent_id": "string",
    "imei_verified": true,
    "kyc_verified": true,
    "weight_grams": 100.0,
    "intake_timestamp": "string",
    "accessories_included": ["charger"]
}
```

### 3) `device-picked-up`

```json
{
    "device_id": "string",
    "agent_id": "string",
    "pickup_latitude": 0.0,
    "pickup_longitude": 0.0,
    "imei_verified": true,
    "kyc_verified": true,
    "weight_grams": 100.0,
    "pickup_timestamp": "string",
    "user_digital_signature_hash": "string"
}
```

### 4) `device-graded`

```json
{
    "device_id": "string",
    "partner_shop_id": "string",
    "checklist_responses": {
        "powers_on": true,
        "screen_cracked": false,
        "touchscreen_works": true,
        "missing_parts": false,
        "battery_swollen": false,
        "ports_functional": true,
        "wifi_connects": true
    },
    "final_grade": "A|B|C|Scrap",
    "grading_timestamp": "string",
    "technician_id": "string"
}
```

### 5) `data-wiped`

```json
{
    "device_id": "string",
    "wipe_tool_used": "string",
    "wipe_standard": "string",
    "wipe_passes": 1,
    "wipe_success": true,
    "technician_id": "string",
    "wipe_timestamp": "string",
    "wipe_certificate_document_hash": "string"
}
```

### 6) `device-repaired`

```json
{
    "device_id": "string",
    "repairs_performed": ["string"],
    "parts_source": "OEM|aftermarket|harvested",
    "repair_duration_hours": 1.5,
    "technician_id": "string",
    "repair_timestamp": "string"
}
```

### 7) `device-listed`

```json
{
    "device_id": "string",
    "listing_id": "string",
    "final_grade": "A|B|C",
    "listed_price_inr": 1000,
    "battery_health_pct": 95,
    "warranty_days": 30,
    "listing_timestamp": "string"
}
```

### 8) `device-sold`

```json
{
    "device_id": "string",
    "listing_id": "string",
    "sale_price_inr": 900,
    "buyer_id_hash": "string",
    "recoins_redeemed": 0,
    "platform_commission_inr": 0,
    "sale_timestamp": "string"
}
```

### 9) `device-batched`

```json
{
    "device_id": "string",
    "batch_id": "string",
    "device_category": "smartphone|laptop|tablet|other",
    "weight_grams": 100.0,
    "batching_timestamp": "string",
    "partner_shop_id": "string"
}
```

### 10) `batch-dispatched`

```json
{
    "batch_id": "string",
    "recycler_id": "string",
    "recycler_name": "string",
    "total_weight_kg": 10.0,
    "device_count": 5,
    "device_ids": ["DEV-1", "DEV-2"],
    "procurement_invoice_number": "string",
    "dispatch_timestamp": "string",
    "transport_agent_id": "string"
}
```

### 11) `recycler-acknowledged`

```json
{
    "batch_id": "string",
    "recycler_id": "string",
    "received_weight_kg": 9.5,
    "weight_certificate_hash": "string",
    "cpcb_procurement_entry_id": "string",
    "receipt_timestamp": "string"
}
```

### 12) `epr-certificate`

```json
{
    "batch_id": "string",
    "epr_certificate_id": "string",
    "certificate_weight_kg": 9.5,
    "oem_recipient_id": "string",
    "certificate_date": "string",
    "collection_fee_inr": 0
}
```

## Standard Event Response

```json
{
    "id": "uuid",
    "device_id": "string",
    "event_type": "DEVICE_SUBMITTED",
    "blockchain_status": "QUEUED|CONFIRMED|FAILED",
    "created_at": "2026-03-22T01:21:48.149625"
}
```

## Environment Variables

`backend/app/core/config.py` loads env from `.env` and `../.env`.

### Core

- `ENVIRONMENT` (default `dev`)
- `DATABASE_URL`

### Polygon

- `POLYGON_RPC_URL`
- `CHAIN_ID` (default `80002`)

### Wallet private keys (hex without `0x`)

- `PLATFORM_PRIVATE_KEY`
- `PARTNER_WALLET_KEY`
- `AGENT_WALLET_KEY`
- `RECYCLER_WALLET_KEY`

### Contract

- `CONTRACT_ADDRESS`
- `CONTRACT_ABI_PATH`

### API keys

- `PLATFORM_EVENT_API_KEY`
- `PARTNER_EVENT_API_KEY`
- `AGENT_EVENT_API_KEY`
- `RECYCLER_EVENT_API_KEY`
- `ADMIN_API_KEY`

### Public links

- `POLYGONSCAN_BASE_URL`
- `PUBLIC_BASE_URL`

## Recommended `.env` Example (Local, No Docker)

```env
ENVIRONMENT=dev
DATABASE_URL=sqlite+aiosqlite:///./backend/recircle.db

POLYGON_RPC_URL=https://rpc-amoy.polygon.technology
CHAIN_ID=80002

PLATFORM_PRIVATE_KEY=replace_me
PARTNER_WALLET_KEY=
AGENT_WALLET_KEY=
RECYCLER_WALLET_KEY=

CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
CONTRACT_ABI_PATH=C:/absolute/path/to/data_sec/contracts/DevicePassport.abi.json

PLATFORM_EVENT_API_KEY=replace_me
PARTNER_EVENT_API_KEY=replace_me
AGENT_EVENT_API_KEY=replace_me
RECYCLER_EVENT_API_KEY=replace_me
ADMIN_API_KEY=replace_me

POLYGONSCAN_BASE_URL=https://amoy.polygonscan.com
PUBLIC_BASE_URL=http://localhost:8005
```

Note: using an absolute `CONTRACT_ABI_PATH` prevents cwd-related path issues.

## Run Locally (No Docker)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8005 --env-file C:/absolute/path/to/data_sec/.env
```

## Run with Docker Compose

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8001`
- DB: Postgres exposed on host `5433`

## Expose via Cloudflare Tunnel

Temporary tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:8005
```

Named tunnel (recommended for stable hostnames):

```powershell
cloudflared tunnel login
cloudflared tunnel create recircle-api
cloudflared tunnel route dns recircle-api api.yourdomain.com
```

`~/.cloudflared/config.yml` example:

```yaml
tunnel: recircle-api
credentials-file: C:\Users\<user>\.cloudflared\<tunnel-id>.json

ingress:
    - hostname: api.yourdomain.com
        service: http://127.0.0.1:8005
    - service: http_status:404
```

Start:

```powershell
cloudflared tunnel run recircle-api
```

## Smart Contract Build and Deploy

```bash
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network amoy
```

Then update `.env` with deployed `CONTRACT_ADDRESS`.

## Test Commands

Run backend tests:

```bash
cd backend
python run_tests.py
```

or

```bash
cd backend
pytest -v tests/
```

## Important Runtime Behavior

- Event endpoints return quickly even if blockchain transaction settles later.
- Successful API response can still be followed by background blockchain failure.
- Background failure writes to `blockchain_dead_letters` for admin retry.
- `GET /api/v1/verify/{device_id}` validates DB event data against on-chain logs.
- `GET /api/v1/passport/{device_id}` provides public event timeline and proof links.

## Troubleshooting

### 401 Invalid actor key

- Wrong key for endpoint role.
- Missing `X-Actor-Key` header.
- API restarted with different env than expected.

### 422 Unprocessable Entity

- Malformed JSON body.
- Missing required payload fields.
- Enum/type mismatch (for example wrong `device_category`).

### 404 Not Found for custom event routes

- Endpoint is not implemented.
- Check against documented endpoint list above.

### DB startup error (`getaddrinfo failed`)

- `DATABASE_URL` host is invalid/unreachable.
- For local no-Docker runs, prefer SQLite URL shown above.

### Blockchain init/runtime failures

- `CONTRACT_ABI_PATH` invalid or relative to wrong cwd.
- Bad contract address or RPC URL.
- Missing signer key for requested role.

## Security Notes

- Never commit real private keys or production API keys.
- Rotate any key that was shared in logs or chat.
- Use separate keys and wallets for dev/stage/prod.
- Restrict admin key usage to trusted systems only.

## Current Scope

This repository is focused on event logging, verification, and device passport exposure.
It does not implement OCR flows or marketplace orchestration endpoints.
