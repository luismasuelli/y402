class BaseError(Exception):
    """
    Base error, for all the error subclasses, of this library.
    """

class MisconfigurationError(BaseError):
    """
    Raised when a configuration error occurs.
    """

class ConditionalDependencyError(BaseError):
    """
    Raised when an import error of a conditionally-required
    library (e.g. FastAPI, requests) occurs.
    """
