from y402.core.types.errors import BaseError


class HeadersBuildingFacilitatorError(BaseError):
    """
    Raised when there was an error creating the facilitator headers.
    """


class VerifyFacilitatorInvalidError(BaseError):
    """
    Raised when the verification failed (i.e. it's invalid).
    """


class VerifyFacilitatorUnknownError(BaseError):
    """
    Raised when the verification had an error.
    """


class SettleFacilitatorFailedError(BaseError):
    """
    Raised when the settling had an error.
    """


class SettleFacilitatorUnknownError(BaseError):
    """
    Raised when the settling had an error.
    """
