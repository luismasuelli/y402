from __future__ import annotations
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Literal, Optional, TypeVar
from ...core.types.errors import ConditionalDependencyError


try:
    import streamlit as st
    from streamlit_browser_web3 import WalletHandler
except ImportError as exc:
    raise ConditionalDependencyError(
        "Streamlit support requires streamlit and streamlit-browser-web3."
    ) from exc


from ...core.types.requirements import PaymentRequirements
from ...core.types.responses import x402PaymentRequiredResponse
from ..common import (
    DEFAULT_CHAIN_ID_BY_NAME,
    SUPPORTED_X402_VERSIONS,
    PaymentError,
    PaymentSelectorCallable,
    UnsupportedSchemeException,
    decode_x_payment_networks,
    encode_payment,
)


ResponseT = TypeVar("ResponseT")
RequestStatus = Literal["success", "pending", "error"]
AccountSelectorCallable = Callable[[WalletHandler], str]


@dataclass(frozen=True)
class StreamlitRequestResult(Generic[ResponseT]):
    status: RequestStatus
    response: Optional[ResponseT] = None
    error: Optional[str] = None
    payment_requirements: Optional[PaymentRequirements] = None


@dataclass(frozen=True)
class StreamlitPaymentFlowResult:
    status: RequestStatus
    payment_header: Optional[str] = None
    error: Optional[str] = None
    payment_requirements: Optional[PaymentRequirements] = None


class StreamlitWalletNotConnectedError(PaymentError):
    """
    Raised when a payment flow needs an injected wallet but none is connected.
    """


def _state_key() -> str:
    return "y402:streamlit:payment_flows"


def _state() -> Dict[str, Dict[str, Any]]:
    if _state_key() not in st.session_state:
        st.session_state[_state_key()] = {}
    return st.session_state[_state_key()]


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}
    if isinstance(value, PaymentRequirements):
        return value.model_dump(mode="json", by_alias=True)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def make_request_fingerprint(
    method: str,
    url: str,
    *,
    params: Any = None,
    headers: Any = None,
    content: Any = None,
    data: Any = None,
    json_data: Any = None,
) -> str:
    """
    Creates a stable fingerprint for a request invocation so the same
    Streamlit key can be reused safely across reruns.
    """

    return json.dumps(
        {
            "method": method.upper(),
            "url": url,
            "params": params,
            "headers": headers,
            "content": content,
            "data": data,
            "json": json_data,
        },
        sort_keys=True,
        default=_json_default,
    )


class StreamlitY402Client:
    """
    Coordinates a y402 payment flow across Streamlit reruns by delegating the
    signature step to a browser wallet through streamlit-browser-web3.
    """

    def __init__(
        self,
        wallet: WalletHandler,
        payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
        chain_id_by_name: Optional[Dict[str, int]] = None,
        account_selector: Optional[AccountSelectorCallable] = None,
    ):
        self.wallet = wallet
        self.chain_id_by_name = {**DEFAULT_CHAIN_ID_BY_NAME, **(chain_id_by_name or {})}
        self._payment_requirements_selector = (
            payment_requirements_selector or self.default_payment_requirements_selector
        )
        self._account_selector = account_selector or self.default_account_selector

    @staticmethod
    def default_payment_requirements_selector(
        accepts: list[PaymentRequirements],
    ) -> PaymentRequirements:
        for payment_requirements in accepts:
            if payment_requirements.scheme == "exact":
                return payment_requirements
        raise UnsupportedSchemeException("No supported payment scheme found")

    def select_payment_requirements(
        self, accepts: list[PaymentRequirements]
    ) -> PaymentRequirements:
        return self._payment_requirements_selector(accepts)

    @staticmethod
    def default_account_selector(wallet: WalletHandler) -> str:
        if not wallet.accounts:
            raise StreamlitWalletNotConnectedError(
                "Connect a browser wallet before selecting an account."
            )
        return wallet.accounts[0]

    def select_account(self) -> str:
        account = self._account_selector(self.wallet)
        if account not in self.wallet.accounts:
            raise StreamlitWalletNotConnectedError(
                f"The selected account '{account}' is not available in the connected wallet."
            )
        return account

    def clear_flow(self, key: str) -> None:
        flow = _state().pop(key, None)
        if flow:
            self.wallet.forget(flow["wallet_request_key"])

    def process_402_response(
        self,
        *,
        key: str,
        request_fingerprint: str,
        response_body: Any,
        x_payment_networks: Optional[str],
    ) -> StreamlitPaymentFlowResult:
        """
        Starts or resumes a wallet-backed payment flow for a 402 response.
        """

        self._ensure_wallet_connected()
        flow = self._get_flow(key, request_fingerprint)
        if flow is None:
            flow = self._create_flow(
                key=key,
                request_fingerprint=request_fingerprint,
                response_body=response_body,
                x_payment_networks=x_payment_networks,
            )
        return self._process_existing_flow(key, flow)

    def resume_payment_flow(
        self, *, key: str, request_fingerprint: str
    ) -> Optional[StreamlitPaymentFlowResult]:
        """
        Resumes a previously-started payment flow for the same request.
        """

        flow = self._get_flow(key, request_fingerprint)
        if flow is None:
            return None
        self._ensure_wallet_connected()
        return self._process_existing_flow(key, flow)

    def _process_existing_flow(
        self, key: str, flow: Dict[str, Any]
    ) -> StreamlitPaymentFlowResult:
        if flow["expires_at"] <= time.time():
            self.clear_flow(key)
            return StreamlitPaymentFlowResult(
                status="error",
                error="The pending payment authorization expired. Start the request again.",
                payment_requirements=PaymentRequirements(**flow["payment_requirements"]),
            )

        if flow.get("payment_header"):
            return StreamlitPaymentFlowResult(
                status="success",
                payment_header=flow["payment_header"],
                payment_requirements=PaymentRequirements(**flow["payment_requirements"]),
            )

        status, result = self.wallet.request(
            "eth_signTypedData_v4",
            [flow["account"], json.dumps(flow["typed_data"])],
            key=flow["wallet_request_key"],
        )
        if status == "pending":
            return StreamlitPaymentFlowResult(
                status="pending",
                payment_requirements=PaymentRequirements(**flow["payment_requirements"]),
            )
        if status == "error":
            self.clear_flow(key)
            return StreamlitPaymentFlowResult(
                status="error",
                error=str(result),
                payment_requirements=PaymentRequirements(**flow["payment_requirements"]),
            )

        payment_header = self._build_signed_header(flow, str(result))
        flow["payment_header"] = payment_header
        return StreamlitPaymentFlowResult(
            status="success",
            payment_header=payment_header,
            payment_requirements=PaymentRequirements(**flow["payment_requirements"]),
        )

    def _ensure_wallet_connected(self) -> None:
        if not self.wallet.available:
            raise StreamlitWalletNotConnectedError(
                "window.ethereum is not available in this browser."
            )
        if not self.wallet.connected or not self.wallet.accounts:
            raise StreamlitWalletNotConnectedError(
                "Connect a browser wallet before starting a y402 payment flow."
            )

    def _create_flow(
        self,
        *,
        key: str,
        request_fingerprint: str,
        response_body: Any,
        x_payment_networks: Optional[str],
    ) -> Dict[str, Any]:
        payment_response = x402PaymentRequiredResponse(**response_body)
        if payment_response.x402_version not in SUPPORTED_X402_VERSIONS:
            raise PaymentError(
                f"Unsupported x402 version: {payment_response.x402_version}"
            )

        try:
            y402_chain_id_by_name = (
                decode_x_payment_networks(x_payment_networks)
                if x_payment_networks
                else None
            )
        except Exception:
            y402_chain_id_by_name = None

        payment_requirements = self.select_payment_requirements(payment_response.accepts)
        account = self.select_account()
        authorization = self._make_authorization(payment_requirements)
        typed_data = self._make_typed_data(
            payment_requirements=payment_requirements,
            authorization=authorization,
            y402_chain_id_by_name=y402_chain_id_by_name,
        )

        flow = {
            "request_fingerprint": request_fingerprint,
            "wallet_request_key": f"y402:streamlit:sign:{key}",
            "x402_version": payment_response.x402_version,
            "payment_requirements": payment_requirements.model_dump(mode="json"),
            "authorization": authorization,
            "typed_data": typed_data,
            "account": account,
            "payment_header": None,
            "expires_at": int(authorization["validBefore"]),
        }
        _state()[key] = flow
        return flow

    def _get_flow(
        self, key: str, request_fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        flow = _state().get(key)
        if not flow:
            return None
        if flow["request_fingerprint"] == request_fingerprint:
            return flow
        if flow.get("payment_header"):
            self.clear_flow(key)
            return None
        raise PaymentError(
            f"Streamlit payment key `{key}` is already associated to a different pending request."
        )

    def _make_typed_data(
        self,
        *,
        payment_requirements: PaymentRequirements,
        authorization: Dict[str, str],
        y402_chain_id_by_name: Optional[Dict[str, int]],
    ) -> Dict[str, Any]:
        chain_id_by_name = {**self.chain_id_by_name, **(y402_chain_id_by_name or {})}
        if payment_requirements.network not in chain_id_by_name:
            raise PaymentError(
                f"The network '{payment_requirements.network}' is not known among the configured networks."
            )

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            },
            "primaryType": "TransferWithAuthorization",
            "domain": {
                "name": payment_requirements.extra["name"],
                "version": payment_requirements.extra["version"],
                "chainId": int(chain_id_by_name[payment_requirements.network]),
                "verifyingContract": payment_requirements.asset,
            },
            "message": {
                "from": authorization["from"],
                "to": authorization["to"],
                "value": authorization["value"],
                "validAfter": int(authorization["validAfter"]),
                "validBefore": int(authorization["validBefore"]),
                "nonce": f"0x{authorization['nonce']}",
            },
        }

    def _build_signed_header(self, flow: Dict[str, Any], signature: str) -> str:
        signature = signature if signature.startswith("0x") else f"0x{signature}"
        authorization = dict(flow["authorization"])
        authorization["nonce"] = f"0x{authorization['nonce']}"
        return encode_payment(
            {
                "x402Version": flow["x402_version"],
                "scheme": flow["payment_requirements"]["scheme"],
                "network": flow["payment_requirements"]["network"],
                "payload": {
                    "signature": signature,
                    "authorization": authorization,
                },
            }
        )

    def _make_authorization(
        self, payment_requirements: PaymentRequirements
    ) -> Dict[str, str]:
        now = int(time.time())
        return {
            "from": self.select_account(),
            "to": payment_requirements.pay_to,
            "value": payment_requirements.max_amount_required,
            "validAfter": str(now - 60),
            "validBefore": str(now + payment_requirements.max_timeout_seconds),
            "nonce": secrets.token_hex(32),
        }
