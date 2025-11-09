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

    def verify(self, request: VerifyRequest) -> VerifyResponse:
        raise NotImplementedError

    def settle(self, request: SettleRequest) -> SettleResponse:
        raise NotImplementedError
