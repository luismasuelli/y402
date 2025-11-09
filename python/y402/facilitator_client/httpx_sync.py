from .base import FacilitatorClient as BaseFacilitatorClient
from y402.core.types.errors import ConditionalDependencyError, BaseError
from .errors import VerifyFacilitatorUnknownError, SettleFacilitatorUnknownError
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

    def verify(self, request: VerifyRequest, timeout: int = 10) -> VerifyResponse:
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
            with httpx.Client(timeout=15) as client:
                response = client.post(self._config.url.rstrip("/") + "/verify", headers=headers,
                                       json=request.model_dump(mode="json"), timeout=timeout)
                response.read()
                self._check_verify_status(response.status_code, response.content, response.headers.get('Content-Type'))
                return self._parse_verify_obj(response.json())
        except BaseError:
            raise
        except Exception as e:
            raise VerifyFacilitatorUnknownError(e)

    def settle(self, request: SettleRequest, timeout: int = 10) -> SettleResponse:
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
            with httpx.Client(timeout=15) as client:
                response = client.post(self._config.url.rstrip("/") + "/settle", headers=headers,
                                       json=request.model_dump(mode="json"), timeout=timeout)
                response.read()
                self._check_settle_status(response.status_code, response.content, response.headers.get('Content-Type'))
                return self._parse_settle_obj(response.json())
        except BaseError:
            raise
        except Exception as e:
            raise SettleFacilitatorUnknownError(e)
