from typing import Optional, Literal
from y402.core.types.facilitator import VerifyResponse, VerifyRequest, SettleRequest, SettleResponse, \
    FacilitatorConfig
from .utils import make_headers


class FacilitatorClient:
    """
    This class defines the base methods for facilitator clients.
    """

    def __init__(self, config: Optional[FacilitatorConfig] = None):
        self._config = config or FacilitatorConfig()

    def _make_headers(self, endpoint: Literal['verify', 'settle']) -> dict:
        """
        Makes the headers for the chosen endpoint and out of the
        settings given for the header.

        Args:
            endpoint: 'verify' or 'settle'.
        Returns:
            The dictionary of headers.
        """

        return make_headers(self._config.headers, endpoint)

    def verify(self, request: VerifyRequest, timeout: int = 10) -> VerifyResponse:
        """
        Performs a /verify POST call with the given data.

        Args:
            request: The current request.
            timeout: The timeout.
        Returns:
            The verify response.
        """

        raise NotImplementedError

    def settle(self, request: SettleRequest, timeout: int = 10) -> SettleResponse:
        """
        Performs a /settle POST call with the given data.

        Args:
            request: The current request.
            timeout: The timeout.
        Returns:
            The settle response.
        """

        raise NotImplementedError
