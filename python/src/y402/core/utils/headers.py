import base64
import json
from typing import Dict, Any, Tuple
from ...core.types.client import PaymentPayload
from ...core.types.setup import Y402Setup
from .signature import check_signature


def is_browser_request(headers: Dict[str, Any]) -> bool:
    """
    Determine if request is from a browser vs API client.

    Args:
        headers: Dictionary of request headers (case-insensitive keys).

    Returns:
        True if request appears to be from a browser, False otherwise.
    """

    headers_lower = {k.lower(): v for k, v in headers.items()}
    accept_header = headers_lower.get("accept", "")
    user_agent = headers_lower.get("user-agent", "")

    if "text/html" in accept_header and "Mozilla" in user_agent:
        return True

    return False


def decode_payment_header(payment_header: str) -> PaymentPayload:
    """
    Decodes a payment header.

    Args:
        payment_header: The contents of the payment header.

    Returns:
        The parsed payment payload.
    """

    return PaymentPayload(**json.loads(base64.b64decode(payment_header).decode("utf-8")))


def validate_payment_asset(
    network: str,
    payment_payload: PaymentPayload,
    payment_asset_header: str,
    merged_setup: Y402Setup
) -> Tuple[str, str, bool]:
    """
    Validates whether the asset in the payment asset header is valid or not.

    Args:
        network: The involved chosen network.
        payment_payload: The provided payment payload.
        payment_asset_header: The contents of the payment asset header.
        merged_setup: The current merged setup.

    Returns:
        A tuple (code, address, True) or ("", "", False).
    """

    token_codes = merged_setup.list_tokens(network)
    chain_id = merged_setup.get_chain_id(network)
    payment_asset_header = payment_asset_header.lower()

    for code in token_codes:
        name, _, address, version, _ = merged_setup.get_token_metadata(network, code)
        if check_signature(name, version, chain_id, address,
                           payment_payload.payload.authorization,
                           payment_payload.payload.signature) and \
                (not payment_asset_header or payment_asset_header == address.lower()):
            return code, address, True
    return "", "", False
