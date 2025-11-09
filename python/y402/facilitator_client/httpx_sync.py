from .base import FacilitatorClient as BaseFacilitatorClient
from y402.core.types.errors import ConditionalDependencyError
from ..core.types.facilitator import VerifyRequest, VerifyResponse, SettleResponse, SettleRequest


try:
    import httpx
except ImportError:
    raise ConditionalDependencyError("httpx library is not installed. Install it as a requirement "
                                     "by invoking httpx==0.28.1 or similar")


class FacilitatorClient(BaseFacilitatorClient):
    """
    This class stands for a httpx-based facilitator client.
    However, this implementation is synchronous.
    """

    def verify(self, request: VerifyRequest) -> VerifyResponse:
        raise NotImplementedError

    def settle(self, request: SettleRequest) -> SettleResponse:
        raise NotImplementedError
