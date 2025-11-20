from typing import Optional, Literal
from ..core.types.facilitator import VerifyResponse, VerifyRequest, SettleRequest, SettleResponse, \
    FacilitatorConfig
from .errors import VerifyFacilitatorInvalidError, VerifyBadResponse, SettleBadResponse, SettleFacilitatorFailedError
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

    def _check_verify_status(self, status_code: int, content: bytes, content_type: str):
        """
        Requires the status_code of verify to be 2xx.

        Args:
            status_code: The status code.
        """

        if status_code not in range(200, 300):
            raise VerifyBadResponse(status_code, content, content_type)

    def _parse_verify_obj(self, obj: dict) -> VerifyResponse:
        """
        Parses a verify object (dict) into a model. It also
        fails if the verification is not valid.

        Args:
            obj: The dictionary to parse.
        Returns:
            The parsed object.
        """

        obj = VerifyResponse(**obj)
        if obj.is_valid:
            raise VerifyFacilitatorInvalidError(obj)
        return obj

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

    def _check_settle_status(self, status_code: int, content: bytes, content_type: str):
        """
        Requires the status_code of settle to be 2xx.

        Args:
            status_code: The status code.
        """

        if status_code not in range(200, 300):
            raise SettleBadResponse(status_code, content, content_type)

    def _parse_settle_obj(self, obj: dict) -> SettleResponse:
        """
        Parses a settle object (dict) into a model. It also
        fails if the settling has failed.

        Args:
            obj: The dictionary to parse.
        Returns:
            The parsed object.
        """

        obj = SettleResponse(**obj)
        if obj.is_valid:
            raise SettleFacilitatorFailedError(obj)
        return obj

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
