// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DevicePassport
 * @notice Event-emission-only contract for the ReCircle e-waste platform.
 *         Every real-world lifecycle action is anchored on-chain as a
 *         SHA-256 hash of the off-chain record.  No state is stored —
 *         events are permanently indexed by Polygon and queryable via
 *         eth_getLogs.
 */
contract DevicePassport {

    /**
     * @notice Emitted every time a lifecycle event is recorded.
     * @param deviceId   Platform UUID of the device (or batch_id for batch events).
     * @param eventType  One of the 11 canonical event-type strings.
     * @param dataHash   SHA-256 hash of the canonical JSON payload.
     * @param actor      Wallet address that signed the transaction.
     * @param timestamp  Block timestamp at the moment of inclusion.
     */
    event EventLogged(
        string indexed deviceId,
        string eventType,
        bytes32 dataHash,
        address actor,
        uint256 timestamp
    );

    /**
     * @notice Record a lifecycle event on-chain.
     * @param deviceId  Platform UUID (or batch_id for batch-level events).
     * @param eventType Canonical event-type string, e.g. "DEVICE_SUBMITTED".
     * @param dataHash  SHA-256 digest of the deterministic JSON payload.
     */
    function logEvent(
        string memory deviceId,
        string memory eventType,
        bytes32 dataHash
    ) public {
        emit EventLogged(
            deviceId,
            eventType,
            dataHash,
            msg.sender,
            block.timestamp
        );
    }
}
