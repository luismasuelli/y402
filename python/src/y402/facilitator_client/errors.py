from ..core.types.errors import BaseError


class BaseFacilitatorError(BaseError):
    """
    Raised when there was an error related to a facilitator.
    """


class HeadersBuildingFacilitatorError(BaseFacilitatorError):
    """
    Raised when there was an error creating the facilitator headers.
    """


class VerifyBadResponse(BaseFacilitatorError):
    """
    Raised when the verification returned a non-2xx error.
    """


class VerifyFacilitatorInvalidError(BaseFacilitatorError):
    """
    Raised when the verification failed (i.e. it's invalid).
    """


class VerifyFacilitatorUnknownError(BaseFacilitatorError):
    """
    Raised when the verification had an error.
    """


class SettleBadResponse(BaseFacilitatorError):
    """
    Raised when the settling returned a non-2xx error.
    """


class SettleFacilitatorFailedError(BaseFacilitatorError):
    """
    Raised when the settling had an error.
    """


class SettleFacilitatorUnknownError(BaseFacilitatorError):
    """
    Raised when the settling had an error.
    """
