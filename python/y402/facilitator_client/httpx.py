from .base import FacilitatorClient as BaseFacilitatorClient
from y402.core.types.errors import ConditionalDependencyError
from .errors import VerifyFacilitatorInvalidError, VerifyFacilitatorUnknownError, SettleFacilitatorUnknownError, \
    SettleFacilitatorFailedError
from ..core.types.facilitator import VerifyRequest, VerifyResponse, SettleResponse, SettleRequest


try:
    import httpx
except ImportError:
    raise ConditionalDependencyError("httpx library is not installed. Install it as a requirement "
                                     "by invoking httpx==0.28.1 or similar")


class FacilitatorClient(BaseFacilitatorClient):
    """
    This class stands for a httpx-based facilitator client.
    The results come in the form of awaitable objects.
    """

    async def verify(self, request: VerifyRequest, timeout: int = 10) -> VerifyResponse:
        """
        Performs a /verify POST call with the given data.

        Args:
            request: The current request.
            timeout: The timeout.
        Returns:
            The verify response.
        """

        headers = self._make_headers('verify')
        if timeout < 1:
            timeout = 1
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self._config.url, headers=headers,
                                             json=request.model_dump(mode="json"),
                                             timeout=timeout)
                if response.status_code not in range(200, 300):
                    raise Exception()
                obj = VerifyResponse(**(response.json()))
                if obj.is_valid:
                    raise VerifyFacilitatorInvalidError(response.status_code, obj)
                return obj
        except Exception as e:
            raise VerifyFacilitatorUnknownError(e)

    async def settle(self, request: SettleRequest, timeout: int = 10) -> SettleResponse:
        """
        Performs a /settle POST call with the given data.

        Args:
            request: The current request.
            timeout: The timeout.
        Returns:
            The settle response.
        """

        headers = self._make_headers('settle')
        if timeout < 1:
            timeout = 1
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self._config.url, headers=headers,
                                             json=request.model_dump(mode="json"),
                                             timeout=timeout)
                if response.status_code not in range(200, 300):
                    raise Exception()
                obj = SettleResponse(**(response.json()))
                if obj.success:
                    raise SettleFacilitatorFailedError(response.status_code, obj)
                return obj
        except Exception as e:
            raise SettleFacilitatorUnknownError(e)
