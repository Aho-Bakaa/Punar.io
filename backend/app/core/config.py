"""Runtime settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the Device Passport event-logging backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Core ─────────────────────────────────────────────
    app_name: str = "ReCircle Device Passport API"
    environment: str = "dev"
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        alias="DATABASE_URL",
    )

    # ── Polygon ──────────────────────────────────────────
    polygon_rpc_url: str = Field(default="https://rpc-amoy.polygon.technology", alias="POLYGON_RPC_URL")
    chain_id: int = Field(default=80002, alias="CHAIN_ID")

    # ── Wallet private keys (hex, no 0x prefix) ─────────
    platform_private_key: str = Field(
        default="ac0974bec39a17e36ba4a6b4d238ff944bacb478bed5efcae784d7bf4f2ff80",
        alias="PLATFORM_PRIVATE_KEY",
    )
    partner_wallet_key: str = Field(default="", alias="PARTNER_WALLET_KEY")
    agent_wallet_key: str = Field(default="", alias="AGENT_WALLET_KEY")
    recycler_wallet_key: str = Field(default="", alias="RECYCLER_WALLET_KEY")

    # ── Contract ─────────────────────────────────────────
    contract_address: str = Field(
        default="0x0000000000000000000000000000000000000000",
        alias="CONTRACT_ADDRESS",
    )
    contract_abi_path: str = Field(
        default="contracts/DevicePassport.abi.json",
        alias="CONTRACT_ABI_PATH",
    )

    # ── Auth ─────────────────────────────────────────────
    admin_api_key: str = Field(default="change-me-admin", alias="ADMIN_API_KEY")

    # ── Public URLs ──────────────────────────────────────
    polygonscan_base_url: str = Field(
        default="https://amoy.polygonscan.com",
        alias="POLYGONSCAN_BASE_URL",
    )
    public_base_url: str = Field(
        default="http://localhost:8001",
        alias="PUBLIC_BASE_URL",
    )


settings = Settings()
