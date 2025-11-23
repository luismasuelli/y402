import base64
import json
import secrets
import time
from typing import Callable, Optional, List, Dict, Any, TypedDict
from eth_account import Account
from ..core.types.default_data import KNOWN_NETWORKS_AND_TOKENS
from ..core.types.requirements import PaymentRequirements


# This library only understands, for clients, the v1 of this protocol.
SUPPORTED_X402_VERSIONS = [1]


# A mapping with the default networks and their id.
DEFAULT_CHAIN_ID_BY_NAME = {
    key: value["chain_id"] for key, value in KNOWN_NETWORKS_AND_TOKENS
}


# Define type for the payment requirements selector.
PaymentSelectorCallable = Callable[
    # Args are: accepts, network_filter, scheme_filter.
    [List[PaymentRequirements], Optional[str], Optional[str]],
    PaymentRequirements,
]


class PaymentHeader(TypedDict):
    x402Version: int
    scheme: str
    network: str
    payload: dict[str, Any]


class PaymentError(Exception):
    """
    Base class for payment-related errors.
    """


class PaymentAmountExceededError(PaymentError):
    """
    Raised when payment amount exceeds maximum allowed value.
    """


class MissingRequestConfigError(PaymentError):
    """
    Raised when request configuration is missing.
    """


class PaymentAlreadyAttemptedError(PaymentError):
    """
    Raised when payment has already been attempted.
    """


class UnsupportedSchemeException(PaymentError):
    """
    Raised when the scheme of a payment is not supported in this library.
    """


def encode_payment(payment_payload: Dict[str, Any]) -> str:
    """
    Encode a payment payload into a base64 string, handling HexBytes and other non-serializable types.
    """

    from hexbytes import HexBytes

    def default(obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "hex"):
            return obj.hex()
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    data = json.dumps(payment_payload, default=default)
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("utf-8")


def sign_payment_header(
    account: Account, payment_requirements: PaymentRequirements, header: PaymentHeader,
    chain_id_by_name: Dict[str, int]
) -> str:
    """
    Sign a payment header using the account's private key.
    """

    auth = header["payload"]["authorization"]

    nonce_bytes = bytes.fromhex(auth["nonce"])

    typed_data = {
        "types": {
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ]
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": payment_requirements.extra["name"],
            "version": payment_requirements.extra["version"],
            "chainId": int(chain_id_by_name[payment_requirements.network]),
            "verifyingContract": payment_requirements.asset,
        },
        "message": {
            "from": auth["from"],
            "to": auth["to"],
            "value": int(auth["value"]),
            "validAfter": int(auth["validAfter"]),
            "validBefore": int(auth["validBefore"]),
            "nonce": nonce_bytes,
        },
    }

    signed_message = account.sign_typed_data(
        domain_data=typed_data["domain"],
        message_types=typed_data["types"],
        message_data=typed_data["message"],
    )
    signature = signed_message.signature.hex()
    if not signature.startswith("0x"):
        signature = f"0x{signature}"

    header["payload"]["signature"] = signature

    header["payload"]["authorization"]["nonce"] = f"0x{auth['nonce']}"

    encoded = encode_payment(header)
    return encoded


def decode_x_payment_response(header: str) -> Dict[str, Any]:
    """
    Decodes the X-PAYMENT-RESPONSE header.

    Args:
        header: The X-PAYMENT-RESPONSE header to decode.

    Returns:
        The decoded payment response containing:
        - success: bool
        - transaction: str (hex)
        - network: str
        - payer: str (address)
    """

    decoded = base64.b64decode(header).decode("utf-8")
    return json.loads(decoded)


class X402Client:
    """
    Base client for handling x402 payments.
    """

    def __init__(
        self,
        account: Account,
        payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
        chain_id_by_name: Optional[Dict[str, int]] = None
    ):
        """
        Initialize the x402 client.

        Args:
            account: eth_account.Account instance for signing payments.
            payment_requirements_selector: Optional custom selector for payment requirements.
            chain_id_by_name: An optional mapping of extra networks to map (useful when there
                              are more networks to be used by the server). This is useful for
                              when the remote x402 server implements custom networks and does
                              not implement y402, for y402 implementations will tell another
                              way to establish that mapping to y402-compatible clients (like
                              this one).
        """

        self.account = account
        self.chain_id_by_name = {**DEFAULT_CHAIN_ID_BY_NAME, **(chain_id_by_name or {})}
        self._payment_requirements_selector = (
            payment_requirements_selector or self.default_payment_requirements_selector
        )

    @staticmethod
    def default_payment_requirements_selector(
        accepts: List[PaymentRequirements],
        network_filter: Optional[str] = None,
        scheme_filter: Optional[str] = None
    ) -> PaymentRequirements:
        """Select payment requirements from the list of accepted requirements.

        Args:
            accepts: List of accepted payment requirements
            network_filter: Optional network to filter by
            scheme_filter: Optional scheme to filter by

        Returns:
            Selected payment requirements (PaymentRequirements instance from x402.types)

        Raises:
            UnsupportedSchemeException: If no supported scheme is found
            PaymentAmountExceededError: If payment amount exceeds max_value
        """

        for paymentRequirements in accepts:
            scheme = paymentRequirements.scheme
            network = paymentRequirements.network

            # Check scheme filter
            if scheme_filter and scheme != scheme_filter:
                continue

            # Check network filter
            if network_filter and network != network_filter:
                continue

            if scheme == "exact":
                return paymentRequirements

        raise UnsupportedSchemeException("No supported payment scheme found")

    def select_payment_requirements(
        self,
        accepts: List[PaymentRequirements],
        network_filter: Optional[str] = None,
        scheme_filter: Optional[str] = None,
    ) -> PaymentRequirements:
        """
        Select payment requirements using the configured selector.

        Args:
            accepts: List of accepted payment requirements (PaymentRequirements models)
            network_filter: Optional network to filter by
            scheme_filter: Optional scheme to filter by

        Returns:
            Selected payment requirements (PaymentRequirements instance from x402.types)

        Raises:
            UnsupportedSchemeException: If no supported scheme is found
            PaymentAmountExceededError: If payment amount exceeds max_value
        """

        return self._payment_requirements_selector(
            accepts, network_filter, scheme_filter
        )

    def create_payment_header(
        self,
        payment_requirements: PaymentRequirements,
        x402_version: int = SUPPORTED_X402_VERSIONS[-1],
    ) -> str:
        """
        Create a payment header for the given requirements.

        Args:
            payment_requirements: Selected payment requirements
            x402_version: x402 protocol version

        Returns:
            Signed payment header
        """

        unsigned_header = {
            "x402Version": x402_version,
            "scheme": payment_requirements.scheme,
            "network": payment_requirements.network,
            "payload": {
                "signature": None,
                "authorization": {
                    "from": self.account.address,
                    "to": payment_requirements.pay_to,
                    "value": payment_requirements.max_amount_required,
                    "validAfter": str(int(time.time()) - 60),  # 60 seconds before
                    "validBefore": str(
                        int(time.time()) + payment_requirements.max_timeout_seconds
                    ),
                    "nonce": self.generate_nonce(),
                },
            },
        }

        signed_header = sign_payment_header(
            self.account,
            payment_requirements,
            unsigned_header,
            self.chain_id_by_name
        )
        return signed_header

    def generate_nonce(self):
        """
        Generate a random nonce (32 bytes = 64 hex chars)

        Returns:
            The generated nonce.
        """

        return secrets.token_hex(32)
