from typing import Optional, Any, List
from pydantic import BaseModel, Field
from .paywall import PaywallConfig
from .schema import HTTPInputSchema
from .setup import Y402Setup
from .storage import StorageManager

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
        default=None, description="An optional HTML Paywall template for this endpoint in particular"
    )
    storage_manager: Optional[StorageManager] = Field(
        default=None, description="The storage manager. It is preferred over the middleware-level "
                                  "storage manager, and it is mandatory if no storage manager is "
                                  "defined at middleware level"
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
    webhook_url: str = Field(
        description="The webhook URL for this payment endpoint. This is mandatory and per-endpoint"
    )
    api_key: Optional[str] = Field(
        description="The API Key for this endpoint's webhook URL. This will provided as an "
                    "Authorization: Bearer xxxx header. While this is an optional setting, it is "
                    "highly recommended for it to be set. Populate this field from a secret setup "
                    "like an environment variable or a read file's contents. Ensure the handler "
                    "behind the webhook URL handles the incoming Authorization header in this "
                    "way (Bearer xxx, where xxx is the final value in this field)"
    )
    request_timeout: Optional[int] = Field(
        default=None, description="An optional timeout for webhook requests"
    )

    def __call__(self, endpoint):
        setattr(endpoint, X402_ENDPOINT_SETTINGS, self)
        return endpoint
