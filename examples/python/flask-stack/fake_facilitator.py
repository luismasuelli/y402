from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request
from web3 import Web3

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

# The x402 version this facilitator pretends to support.
X402_VERSION = 1

# Single supported kind: "exact" on some EVM-style local network string.
SUPPORTED_KINDS: List[Tuple[str, str]] = [
    ("exact", "local"),  # (scheme, network)
]

# Chain / RPC / token config for on-chain settlement
RPC_URL = "http://127.0.0.1:8545"
# PK for address: 0x90F79bf6EB2c4f870365E785982E1f101E93b906 (3rd anvil account)
FACILITATOR_PRIVATE_KEY = "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"
TOKEN_ADDRESS = os.getenv("FACILITATOR_TOKEN_ADDRESS")
CHAIN_ID = 31337

if FACILITATOR_PRIVATE_KEY is None or TOKEN_ADDRESS is None:
    raise RuntimeError(
        "FACILITATOR_PRIVATE_KEY and TOKEN_ADDRESS env vars must be set "
        "for on-chain settlement."
    )

# ---------------------------------------------------------------------
# web3 setup
# ---------------------------------------------------------------------

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"web3 could not connect to RPC_URL={RPC_URL!r}")

FACILITATOR_ACCOUNT = w3.eth.account.from_key(FACILITATOR_PRIVATE_KEY)

# Minimal ABI for ERC-3009 transferWithAuthorization
ERC3009_ABI = [
    {
        "name": "transferWithAuthorization",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
            {"name": "v", "type": "uint8"},
            {"name": "r", "type": "bytes32"},
            {"name": "s", "type": "bytes32"},
        ],
        "outputs": [],
    }
]

TOKEN_CONTRACT = w3.eth.contract(
    address=Web3.to_checksum_address(TOKEN_ADDRESS),
    abi=ERC3009_ABI,
)

# For /settle response
DEFAULT_NETWORK_ID = str(CHAIN_ID)


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------

def _parse_json_body() -> Dict[str, Any]:
    if not request.is_json:
        raise ValueError("Expected application/json body")
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def _decode_payment_header(payment_header: str) -> Dict[str, Any]:
    """
    Decode the paymentHeader: base64(JSON(PaymentPayload)).

    PaymentPayload (per x402 spec):

        {
          "x402Version": number,
          "scheme": string,
          "network": string,
          "payload": { ... }  // scheme-specific
        }
    """
    try:
        raw = base64.b64decode(payment_header)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Decoded payload is not an object")
        return payload
    except Exception as exc:
        raise ValueError(f"Invalid paymentHeader encoding: {exc}") from exc


def _validate_common_request(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Validates the common shape of /verify and /settle requests.

    Returns:
        (payment_payload, payment_requirements)
    """
    # Check version (outer request)
    version = data.get("x402Version")
    if version != X402_VERSION:
        raise ValueError(f"Unsupported x402Version: {version}, expected {X402_VERSION}")

    # Extract & decode paymentHeader
    payment_header = data.get("paymentHeader")
    if not isinstance(payment_header, str):
        raise ValueError("paymentHeader must be a base64-encoded string")

    payment_payload = _decode_payment_header(payment_header)

    # Extract paymentRequirements (this is exactly what your resource server sent in 402 body)
    payment_requirements = data.get("paymentRequirements")
    if not isinstance(payment_requirements, dict):
        raise ValueError("paymentRequirements must be an object")

    # Check scheme/network are supported
    scheme = payment_payload.get("scheme")
    network = payment_payload.get("network")
    if not isinstance(scheme, str) or not isinstance(network, str):
        raise ValueError("payment payload must contain string fields 'scheme' and 'network'")

    if (scheme, network) not in SUPPORTED_KINDS:
        raise ValueError(f"Unsupported (scheme, network): ({scheme}, {network})")

    return payment_payload, payment_requirements


def _split_eip712_signature(sig_hex: str) -> Tuple[int, bytes, bytes]:
    """
    Split a 65-byte EIP-712 signature (0x + 65 bytes) into (v, r, s).

    sig = r (32 bytes) || s (32 bytes) || v (1 byte).
    """
    if not isinstance(sig_hex, str) or not sig_hex.startswith("0x"):
        raise ValueError("signature must be a 0x-prefixed hex string")

    sig_bytes = bytes.fromhex(sig_hex[2:])
    if len(sig_bytes) != 65:
        raise ValueError(f"signature must be 65 bytes, got {len(sig_bytes)} bytes")

    r = sig_bytes[0:32]
    s = sig_bytes[32:64]
    v_byte = sig_bytes[64]

    # Convert to canonical v in {27, 28}
    v = v_byte
    if v in (0, 1):
        v = v + 27

    if v not in (27, 28):
        raise ValueError(f"unexpected v value in signature: {v}")

    return v, r, s


def _execute_eip3009_transfer(auth: Dict[str, Any], signature: str) -> str:
    """
    Execute an EIP-3009 transferWithAuthorization() call on-chain.

    `auth` is the "authorization" object from the x402 exact EVM payload:
        {
          "from": string,
          "to": string,
          "value": string,
          "validAfter": string,
          "validBefore": string,
          "nonce": string (0x... bytes32)
        }

    `signature` is the 0x-prefixed EIP-712 signature over that authorization.
    """
    # Basic extraction & type normalization
    try:
        from_addr = Web3.to_checksum_address(auth["from"])
        to_addr = Web3.to_checksum_address(auth["to"])
        value = int(auth["value"])
        valid_after = int(auth["validAfter"])
        valid_before = int(auth["validBefore"])
        nonce = auth["nonce"]  # bytes32 as 0x-hex or raw 32 bytes
    except KeyError as exc:
        raise ValueError(f"missing authorization field: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"invalid authorization fields: {exc}") from exc

    v, r_bytes, s_bytes = _split_eip712_signature(signature)

    r = "0x" + r_bytes.hex()
    s = "0x" + s_bytes.hex()

    # Build transaction
    nonce_tx = w3.eth.get_transaction_count(FACILITATOR_ACCOUNT.address)

    tx = TOKEN_CONTRACT.functions.transferWithAuthorization(
        from_addr,
        to_addr,
        value,
        valid_after,
        valid_before,
        nonce,
        v,
        r,
        s,
    ).build_transaction(
        {
            "from": FACILITATOR_ACCOUNT.address,
            "nonce": nonce_tx,
            "chainId": CHAIN_ID,
            "gasPrice": w3.eth.gas_price,
        }
    )

    # Optional: estimate gas with a safety margin
    gas_estimate = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_estimate * 12 // 10)  # +20%

    # Sign & send
    signed = w3.eth.account.sign_transaction(tx, private_key=FACILITATOR_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    # You can choose to wait for confirmation or not. For a "dumb" facilitator
    # it's often enough to just return the tx hash.
    # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex()


# ---------------------------------------------------------------------
# Flask app + endpoints
# ---------------------------------------------------------------------

app = Flask(__name__)


@app.get("/health")
def health() -> Any:
    """
    Simple healthcheck. Not strictly part of the spec, but common in real facilitators.
    """
    return jsonify(
        {
            "status": "healthy",
            "service": "dumb-x402-facilitator",
            "rpcConnected": w3.is_connected(),
            "networkId": DEFAULT_NETWORK_ID,
            "token": TOKEN_ADDRESS,
            "facilitatorAddress": FACILITATOR_ACCOUNT.address,
        }
    )


@app.get("/supported")
def supported() -> Any:
    """
    Spec: GET /supported

    Response:
        {
          "kinds": [
            { "scheme": string, "network": string }
          ]
        }
    """
    kinds = [
        {"scheme": scheme, "network": network}
        for (scheme, network) in SUPPORTED_KINDS
    ]
    return jsonify({"kinds": kinds})


@app.post("/verify")
def verify() -> Any:
    """
    Spec: POST /verify

    Request JSON:
        {
          "x402Version": number,
          "paymentHeader": string,           // base64(JSON(PaymentPayload))
          "paymentRequirements": { ... }    // from 402 response
        }

    Response JSON:
        {
          "isValid": boolean,
          "invalidReason": string | null
        }

    This implementation is intentionally dumb:
      - It only checks version and that scheme+network are supported.
      - It decodes paymentHeader to ensure it's syntactically valid JSON.
      - It does NOT simulate the EIP-3009 transfer.
    """
    try:
        data = _parse_json_body()
    except ValueError as exc:
        return jsonify({"isValid": False, "invalidReason": str(exc)}), 400

    try:
        payment_payload, payment_requirements = _validate_common_request(data)
    except ValueError as exc:
        # In /verify, we want a 200 with isValid=false, not a 4xx.
        return jsonify({"isValid": False, "invalidReason": str(exc)}), 200

    # You could optionally add more checks on payment_payload["payload"]
    # here (e.g. expiry window, value vs. paymentRequirements).
    return jsonify({"isValid": True, "invalidReason": None}), 200


@app.post("/settle")
def settle() -> Any:
    """
    Spec: POST /settle

    Request JSON:
        {
          "x402Version": number,
          "paymentHeader": string,
          "paymentRequirements": { ... }
        }

    Response JSON:
        {
          "success": boolean,
          "error": string | null,
          "txHash": string | null,
          "networkId": string | null
        }

    This implementation:
      - Validates the outer x402 wrapper (version, scheme, network).
      - Extracts the exact/EVM payload (signature + authorization).
      - Calls transferWithAuthorization() on the configured ERC-3009 token.
    """
    try:
        data = _parse_json_body()
    except ValueError as exc:
        # For settle, 4xx is fine because the resource server is the caller.
        return jsonify(
            {
                "success": False,
                "errorReason": str(exc),
                "transaction": None,
                "network": None,
            }
        ), 400

    try:
        payment_payload, payment_requirements = _validate_common_request(data)
    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "errorReason": str(exc),
                "transaction": None,
                "network": None,
            }
        ), 200

    inner = payment_payload.get("payload") or {}
    signature = inner.get("signature")
    authorization = inner.get("authorization")

    if not isinstance(signature, str) or not isinstance(authorization, dict):
        return jsonify(
            {
                "success": False,
                "errorReason": "exact/EVM payload must contain 'signature' string and 'authorization' object",
                "transaction": None,
                "network": None,
            }
        ), 200

    try:
        tx_hash_hex = _execute_eip3009_transfer(authorization, signature)
    except Exception as exc:
        # On-chain failure: still 200, but success=false per spec
        return jsonify(
            {
                "success": False,
                "errorReason": f"on-chain error: {exc}",
                "transaction": None,
                "network": None,
            }
        ), 200

    return jsonify(
        {
            "success": True,
            "errorReason": None,
            "transaction": tx_hash_hex,
            "network": DEFAULT_NETWORK_ID,
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9876, debug=True)
