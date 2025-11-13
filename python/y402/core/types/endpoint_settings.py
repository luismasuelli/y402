from typing import Optional, Any
from pydantic import BaseModel, Field
from .paywall import PaywallConfig
from .schema import HTTPInputSchema


X402_ENDPOINT_SETTINGS = "x402_endpoint_settings"


class X402EndpointSettings(BaseModel):
    """
    The settings for a single endpoint. It also works as a decorator
    to set the settings into a specific endpoint.
    """

    resource_url: Optional[str] = Field(
        default=None, description="An optional, normalized, resource URL for this endpoint"
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
        default=None, description="An optional HTML Paywall template for this endpoint in particular "
    )

    def __call__(self, endpoint):
        setattr(endpoint, X402_ENDPOINT_SETTINGS, self)
        return endpoint
