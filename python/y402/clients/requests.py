from typing import Optional, Dict
import requests
import copy
import json
from requests.adapters import HTTPAdapter
from eth_account import Account
from .common import (
    Y402Client,
    PaymentError,
    PaymentSelectorCallable, decode_x_payment_networks,
)
from ..core.types.responses import x402PaymentRequiredResponse


class y402HTTPAdapter(HTTPAdapter):
    """
    HTTP adapter for handling x402 payment required responses.
    """

    def __init__(self, client: Y402Client, **kwargs):
        """
        Initialize the adapter with an x402Client.

        Args:
            client: x402Client instance for handling payments.
            **kwargs: Additional arguments to pass to HTTPAdapter.
        """

        super().__init__(**kwargs)
        self.client = client
        self._is_retry = False

    def send(self, request, **kwargs):
        """
        Send a request with payment handling for 402 responses.

        Args:
            request: The PreparedRequest being sent.
            **kwargs: Additional arguments to pass to the adapter.

        Returns:
            Response object.
        """

        if self._is_retry:
            self._is_retry = False
            return super().send(request, **kwargs)

        response = super().send(request, **kwargs)

        if response.status_code != 402:
            return response

        try:
            # Save the content before we parse it to avoid consuming it.
            content = copy.deepcopy(response.content)

            # Parse the JSON content without using response.json() which consumes it.
            data = json.loads(content.decode("utf-8"))
            payment_response = x402PaymentRequiredResponse(**data)

            # Get the X-Payment-Networks response.
            x_payment_networks = response.headers.get("X-Payment-Networks")
            try:
                y402_chain_id_by_name = decode_x_payment_networks(x_payment_networks) if x_payment_networks else None
            except:
                y402_chain_id_by_name = None

            # Select payment requirements.
            selected_requirements = self.client.select_payment_requirements(
                payment_response.accepts
            )

            # Create payment header.
            payment_header = self.client.create_payment_header(
                selected_requirements, payment_response.x402_version, y402_chain_id_by_name
            )

            # Mark as retry and add payment header.
            self._is_retry = True
            request.headers["X-Payment"] = payment_header
            request.headers["Access-Control-Expose-Headers"] = "X-Payment-Response, X-Payment-Networks"

            retry_response = super().send(request, **kwargs)

            # Copy the retry response data to the original response.
            response.status_code = retry_response.status_code
            response.headers = retry_response.headers
            response._content = retry_response.content
            return response
        except PaymentError as e:
            self._is_retry = False
            raise e
        except Exception as e:
            self._is_retry = False
            raise PaymentError(f"Failed to handle payment: {str(e)}") from e


def y402_http_adapter(
    account: Account,
    payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
    chain_id_by_name: Optional[Dict[str, int]] = None,
    **kwargs,
) -> y402HTTPAdapter:
    """
    Create an HTTP adapter that handles 402 Payment Required responses.

    Args:
        account: eth_account.Account instance for signing payments.
        payment_requirements_selector: Optional custom selector for payment requirements.
            Should be a callable that takes (accepts, network_filter, scheme_filter, max_value)
            and returns a PaymentRequirements object.
        chain_id_by_name: An optional mapping of extra networks to map (useful when there
                          are more networks to be used by the server). This is useful for
                          when the remote x402 server implements custom networks and does
                          not implement y402, for y402 implementations will tell another
                          way to establish that mapping to y402-compatible clients (like
                          this one).
        **kwargs: Additional arguments to pass to HTTPAdapter.

    Returns:
        x402HTTPAdapter instance that can be mounted to a requests session.
    """

    client = Y402Client(
        account,
        payment_requirements_selector=payment_requirements_selector,
        chain_id_by_name=chain_id_by_name
    )
    return y402HTTPAdapter(client, **kwargs)


def y402_requests(
    account: Account,
    payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
    chain_id_by_name: Optional[Dict[str, int]] = None,
    **kwargs,
) -> requests.Session:
    """
    Create a requests session with x402 payment handling (plus y402 enhancements).

    Args:
        account: eth_account.Account instance for signing payments.
        payment_requirements_selector: Optional custom selector for payment requirements.
            Should be a callable that takes (accepts, network_filter, scheme_filter)
            and returns a PaymentRequirements object.
        chain_id_by_name: An optional mapping of extra networks to map (useful when there
                          are more networks to be used by the server). This is useful for
                          when the remote x402 server implements custom networks and does
                          not implement y402, for y402 implementations will tell another
                          way to establish that mapping to y402-compatible clients (like
                          this one).
        kwargs: Extra arguments for the HTTP adapter.

    Returns:
        Session with x402 payment handling configured.
    """

    session = requests.Session()
    adapter = y402_http_adapter(
        account,
        payment_requirements_selector=payment_requirements_selector,
        chain_id_by_name=chain_id_by_name,
        **kwargs,
    )

    # Mount the adapter for both HTTP and HTTPS.
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
