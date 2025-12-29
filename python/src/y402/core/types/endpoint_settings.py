from typing import Optional, Any, List
from pydantic import BaseModel, Field
from .paywall import PaywallConfig
from .schema import HTTPInputSchema
from .setup import Y402Setup


Y402_ENDPOINT_SETTINGS = "y402_endpoint_settings"


class X402EndpointSettings(BaseModel):
    """
    The settings for a single endpoint. It also works as a decorator
    to set the settings into a specific endpoint, which should return
    a quick response based on the reference and nothing else, since
    by its arrival the payment was already sent to the webhook.
    """

    resource_url: Optional[str] = Field(
        default=None, description="An optional, normalized, resource URL for this endpoint"
    )
    reference_param: Optional[str] = Field(
        default=None, description="An optional field to tell which URL parameter stands for "
                                  "the internal reference. Using references is like using "
                                  "tags in the way that they let to identify the payment or "
                                  "the object / product / invoice being paid, but they are "
                                  "dynamic rather than static (inferred from the URL). It "
                                  "is optional to use this, but once used it must match a "
                                  "parameter from the URL. If not used, the reference will "
                                  "be an empty string for each payment in this endpoint"
    )
    description: Optional[str] = Field(
        default=None, description="An optional endpoint description"
    )
    max_deadline_seconds: Optional[int] = Field(
        default=None, description="An optional setting for the time this endpoint can wait "
                                  "for a given payment handshake. If not set, then the default "
                                  "value can be configured in the middleware"
    )
    input_schema: Optional[HTTPInputSchema] = Field(
        default=None, description="An optional input schema for the x402 response to hint the "
                                  "agents when using this endpoint"
    )
    output_schema: Optional[Any] = Field(
        default=None, description="An optional output schema for the x402 response to hint the "
                                  "agents when using this endpoint"
    )
    mime_type: str = Field(
        default="", description="An optional MIME type for this endpoint"
    )
    paywall_config: Optional[PaywallConfig] = Field(
        default=None, description="An optional paywall configuration (i.e. a coinbase developer "
                                  "platform app settings)"
    )
    custom_paywall_html: Optional[str] = Field(
        default=None, description="An optional HTML Paywall template for this endpoint in particular"
    )
    custom_setup: Optional[Y402Setup] = Field(
        default=None, description="A custom setup (i.e. to set more networks and more tokens) "
                                  "applying for this endpoint only. It will merge to the setup "
                                  "in the middleware (only for this endpoint) to generate the "
                                  "final layout of supported networks and tokens"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Arbitrary tags associated to this endpoint"
    )
    webhook_name: str = Field(
        description="The webhook name. It is an arbitrary string. Dispatch workers must pick "
                    "payments with this value and batch-send them in order for any payment "
                    "with this value to be sent to the webhook"
    )
    storage_collection: str = Field(
        description="The collection to store the payments into for this endpoint"
    )
    # A dispatch worker must run by specifying the same webhook_name and associating 3 options
    # in order to effectively send the payments: webhook_url (absolute), api_key (optional -
    # it will use "X-Api-Key: xxxx" if specified) and request_timeout (optional - if absent or
    # less than 10 seconds it will become actually 10 seconds).

    def __call__(self, endpoint):
        setattr(endpoint, Y402_ENDPOINT_SETTINGS, self)
        return endpoint
