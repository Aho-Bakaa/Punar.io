"""BlockchainService — singleton for all DevicePassport contract interactions.

Handles event logging, history retrieval, and record verification against
the Polygon Amoy chain.  All blockchain writes use exponential-backoff
retries.  Failed writes are caught by the caller and routed to the
dead-letter queue so they never break user-facing API operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.core.config import settings
from app.utils.hashing import compute_payload_hash, hash_to_bytes32
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class BlockchainService:
    """Singleton-style service wrapping web3.py contract operations."""

    _instance: BlockchainService | None = None

    def __new__(cls) -> BlockchainService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        try:
            # ── Web3 provider ────────────────────────────────────
            self.web3 = Web3(
                Web3.HTTPProvider(
                    settings.polygon_rpc_url,
                    request_kwargs={"timeout": 60},
                )
            )
            # Polygon is a PoA chain — inject middleware so extraData > 32 bytes
            # doesn't break block parsing.
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            # ── Wallets ──────────────────────────────────────────
            self.platform_account = self.web3.eth.account.from_key(
                settings.platform_private_key
            )
            self._wallet_map: dict[str, Any] = {
                "PLATFORM_WALLET": self.platform_account,
            }
            if settings.partner_wallet_key:
                self._wallet_map["PARTNER_WALLET"] = (
                    self.web3.eth.account.from_key(settings.partner_wallet_key)
                )
            if settings.agent_wallet_key:
                self._wallet_map["AGENT_WALLET"] = (
                    self.web3.eth.account.from_key(settings.agent_wallet_key)
                )
            if settings.recycler_wallet_key:
                self._wallet_map["RECYCLER_WALLET"] = (
                    self.web3.eth.account.from_key(settings.recycler_wallet_key)
                )

            # ── Contract ─────────────────────────────────────────
            abi_path = Path(settings.contract_abi_path)
            with abi_path.open("r", encoding="utf-8") as fp:
                abi = json.load(fp)

            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(settings.contract_address),
                abi=abi,
            )
        except Exception:
            # Keep singleton reusable if startup fails once (e.g., bad ABI path).
            self._initialised = False
            raise

        self._initialised = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_account(self, wallet_role: str | None = None) -> Any:
        """Return the web3 account for a given wallet role string."""

        if wallet_role is None:
            return self.platform_account
        account = self._wallet_map.get(wallet_role)
        if account is None:
            logger.warning(
                "Wallet role '%s' not configured — falling back to platform wallet.",
                wallet_role,
            )
            raise ValueError(f"Wallet role '{wallet_role}' is not configured.")
        return account

    async def _send_tx(
        self,
        function_call: Any,
        signing_account: Any | None = None,
    ) -> str:
        """Build, sign, broadcast, and wait for a transaction receipt."""

        account = signing_account or self.platform_account

        async def _execute() -> str:
            nonce = await asyncio.to_thread(
                self.web3.eth.get_transaction_count, account.address
            )
            # Use EIP-1559 fee fields for Polygon
            latest_block = await asyncio.to_thread(
                self.web3.eth.get_block, "latest"
            )
            base_fee = latest_block.get("baseFeePerGas", 0)
            max_priority = self.web3.to_wei(30, "gwei")
            max_fee = base_fee * 2 + max_priority

            tx = function_call.build_transaction(
                {
                    "from": account.address,
                    "nonce": nonce,
                    "gas": 300_000,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority,
                    "chainId": settings.chain_id,
                    "type": 2,  # EIP-1559
                }
            )
            signed = account.sign_transaction(tx)
            tx_hash = await asyncio.to_thread(
                self.web3.eth.send_raw_transaction, signed.raw_transaction
            )
            await asyncio.to_thread(
                self.web3.eth.wait_for_transaction_receipt, tx_hash, 120
            )
            return tx_hash.hex()

        return await retry_async(_execute, retries=3, base_delay_seconds=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def log_event(
        self,
        device_id: str,
        event_type: str,
        payload_dict: dict[str, Any],
        wallet_role: str | None = None,
    ) -> tuple[str, str]:
        """Compute payload hash and emit ``EventLogged`` on-chain.

        Parameters
        ----------
        device_id:
            Platform UUID of the device (or batch_id for batch events).
        event_type:
            Canonical event type, e.g. ``"DEVICE_SUBMITTED"``.
        payload_dict:
            The full off-chain payload to hash.
        wallet_role:
            Which registered wallet should sign the tx.  One of
            ``PLATFORM_WALLET``, ``PARTNER_WALLET``, ``AGENT_WALLET``,
            ``RECYCLER_WALLET``.  Defaults to platform wallet.

        Returns
        -------
        A ``(tx_hash, data_hash_hex)`` tuple.
        """

        data_hash_hex = compute_payload_hash(payload_dict)
        data_hash_bytes = hash_to_bytes32(data_hash_hex)

        account = self._resolve_account(wallet_role)
        fn = self.contract.functions.logEvent(device_id, event_type, data_hash_bytes)
        tx_hash = await self._send_tx(fn, signing_account=account)

        logger.info(
            "Logged %s for %s — tx %s", event_type, device_id, tx_hash
        )
        return tx_hash, data_hash_hex

    def _decode_event_log(self, log: Any) -> dict[str, Any]:
        """Decode a single ``EventLogged`` log into a normalised dict."""

        decoded = self.contract.events.EventLogged().process_log(log)
        args = decoded["args"]
        return {
            "device_id": args["deviceId"],
            "event_type": args["eventType"],
            "data_hash": "0x" + args["dataHash"].hex(),
            "actor": args["actor"],
            "timestamp": int(args["timestamp"]),
            "tx_hash": log["transactionHash"].hex(),
            "block_number": log["blockNumber"],
        }

    async def get_event_by_tx_hash(self, tx_hash: str) -> dict[str, Any] | None:
        """Fetch and decode the contract event emitted by a specific tx hash."""

        tx_hash_hex = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
        try:
            receipt = await asyncio.to_thread(
                self.web3.eth.get_transaction_receipt,
                tx_hash_hex,
            )
        except Exception:
            return None

        for log in receipt["logs"]:
            if log["address"].lower() != self.contract.address.lower():
                continue
            try:
                return self._decode_event_log(log)
            except Exception:
                continue

        return None

    async def get_device_history(
        self,
        device_id: str,
        *,
        from_block: int | None = None,
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Query ``eth_getLogs`` for all ``EventLogged`` events matching *device_id*.

        Returns an ordered list of decoded event dicts.
        """

        # The indexed deviceId is a keccak-256 of the ABI-encoded string
        topic_hash = self.web3.keccak(text=device_id)

        event_signature = self.web3.keccak(
            text="EventLogged(string,string,bytes32,address,uint256)"
        )

        query_from_block = 0 if from_block is None else from_block

        raw_logs = await asyncio.to_thread(
            self.web3.eth.get_logs,
            {
                "address": self.contract.address,
                # JSON-RPC topics must be 0x-prefixed hex strings.
                "topics": [
                    self.web3.to_hex(event_signature),
                    self.web3.to_hex(topic_hash),
                ],
                "fromBlock": query_from_block,
                "toBlock": to_block,
            },
        )

        events: list[dict[str, Any]] = []
        for log in raw_logs:
            events.append(self._decode_event_log(log))

        # Sort by block number (chronological)
        events.sort(key=lambda e: e["block_number"])
        return events

    async def verify_record(
        self,
        device_id: str,
        event_type: str,
        payload_dict: dict[str, Any],
        *,
        from_block: int | None = None,
        to_block: int | str = "latest",
    ) -> dict[str, Any]:
        """Re-compute hash and check it against the on-chain record.

        Returns a dict with ``match`` (bool), ``expected_hash``,
        ``on_chain_hash``, and ``tx_hash``.
        """

        expected_hash = compute_payload_hash(payload_dict)
        history = await self.get_device_history(
            device_id,
            from_block=from_block,
            to_block=to_block,
        )

        for event in history:
            if event["event_type"] == event_type:
                on_chain_hex = event["data_hash"]
                # Strip 0x for comparison
                on_chain_clean = on_chain_hex.replace("0x", "")
                return {
                    "match": on_chain_clean == expected_hash,
                    "expected_hash": expected_hash,
                    "on_chain_hash": on_chain_hex,
                    "tx_hash": event["tx_hash"],
                }

        return {
            "match": False,
            "expected_hash": expected_hash,
            "on_chain_hash": None,
            "tx_hash": None,
        }
