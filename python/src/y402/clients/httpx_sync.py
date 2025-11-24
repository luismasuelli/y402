from typing import Optional, Dict, List
from httpx import Request, Response, Client
from eth_account import Account
from .common import (
    Y402Client as BaseY402Client,
    MissingRequestConfigError,
    PaymentError,
    PaymentSelectorCallable, decode_x_payment_networks,
)
from ..core.types.responses import x402PaymentRequiredResponse


class HttpxHooks:
    """
    Hooks for the Httpx sync adapter.
    """

    def __init__(self, client: BaseY402Client):
        self.client = client
        self._is_retry = False

    def on_request(self, request: Request):
        """
        Handle request before it is sent.
        """

    def on_response(self, response: Response) -> Response:
        """
        Handle response after it is received.
        """

        # If this is not a 402, just return the response.
        if response.status_code != 402:
            return response

        # If this is a retry response, just return it.
        if self._is_retry:
            return response

        try:
            if not response.request:
                raise MissingRequestConfigError("Missing request configuration")

            # Read the response content before parsing.
            response.read()

            data = response.json()

            # Get the X-Payment-Networks response.
            x_payment_networks = response.headers.get("X-Payment-Networks")
            try:
                y402_chain_id_by_name = decode_x_payment_networks(x_payment_networks) if x_payment_networks else None
            except:
                y402_chain_id_by_name = None

            payment_response = x402PaymentRequiredResponse(**data)

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
            request = response.request

            request.headers["X-Payment"] = payment_header
            request.headers["Access-Control-Expose-Headers"] = "X-Payment-Response, X-Payment-Networks"

            # Retry the request.
            with Client() as client:
                retry_response = client.send(request)

                # Copy the retry response data to the original response
                response.status_code = retry_response.status_code
                response.headers = retry_response.headers
                response._content = retry_response._content
                return response
        except PaymentError as e:
            self._is_retry = False
            raise e
        except Exception as e:
            self._is_retry = False
            raise PaymentError(f"Failed to handle payment: {str(e)}") from e


def y402_payment_hooks(
    account: Account,
    payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
    chain_id_by_name: Optional[Dict[str, int]] = None
) -> Dict[str, List]:
    """Create httpx event hooks dictionary for handling 402 Payment Required responses.

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

    Returns:
        Dictionary of event hooks that can be directly assigned to client.event_hooks.
    """

    # Create the Y402 client.
    client = BaseY402Client(
        account,
        payment_requirements_selector=payment_requirements_selector,
        chain_id_by_name=chain_id_by_name
    )

    # Create hooks.
    hooks = HttpxHooks(client)

    # Return event hooks dictionary.
    return {
        "request": [hooks.on_request],
        "response": [hooks.on_response],
    }


class Y402Client(Client):
    """
    Client with built-in y402 payment handling.
    """

    def __init__(
        self,
        account: Account,
        payment_requirements_selector: Optional[PaymentSelectorCallable] = None,
        chain_id_by_name: Optional[Dict[str, int]] = None,
        **kwargs
    ):
        """
        Initialize a Client with x402 payment handling (plus y402 enhancements).

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
            **kwargs: Additional arguments to pass to Client.
        """

        super().__init__(**kwargs)
        self.event_hooks = y402_payment_hooks(
            account, payment_requirements_selector, chain_id_by_name
        )
