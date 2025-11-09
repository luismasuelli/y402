from .base import FacilitatorClient as BaseFacilitatorClient
from y402.core.types.errors import ConditionalDependencyError
from ..core.types.facilitator import VerifyRequest, VerifyResponse, SettleResponse, SettleRequest


try:
    import requests
except ImportError:
    raise ConditionalDependencyError("Requests library is not installed. Install it as a requirement "
                                     "by invoking requests==2.32.5 or similar")


class FacilitatorClient(BaseFacilitatorClient):
    """
    This class stands for a requests-based facilitator client.
    """

    def verify(self, request: VerifyRequest) -> VerifyResponse:
        raise NotImplementedError

    def settle(self, request: SettleRequest) -> SettleResponse:
        raise NotImplementedError
