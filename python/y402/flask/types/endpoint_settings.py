from typing import List, Callable, Awaitable
from pydantic import Field
from ...core.types.endpoint_settings import X402EndpointSettings as BaseX402EndpointSettings
from ...core.types.requirements import RequirePaymentDetails


Y402_ENDPOINT_SETTINGS = "y402_endpoint_settings"


PaymentDetailsListType = List[RequirePaymentDetails] | \
                         Callable[[], Awaitable[List[RequirePaymentDetails]] | List[RequirePaymentDetails]]


class X402EndpointSettings(BaseX402EndpointSettings):
    """
    The settings for a single endpoint. It also works as a decorator
    to set the settings into a specific endpoint, which should return
    a quick response based on the reference and nothing else, since
    by its arrival the payment was already sent to the webhook.

    This works on Flask.
    """

    payments_details: PaymentDetailsListType = Field(
        description="Either a non-empty list of allowed payment specs or a callable returning "
                    "a non-empty list of allowed payment specs (this callable can by sync or "
                    "async)"
    )

    def __call__(self, endpoint):
        setattr(endpoint, X402_ENDPOINT_SETTINGS, self)
        return endpoint
