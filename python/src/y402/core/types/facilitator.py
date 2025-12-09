from typing import Dict, Literal, Callable, Awaitable, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from ...core.types.client import PaymentPayload
from ...core.types.requirements import PaymentRequirements


X402_VERSION = 1
Y402_VERSION = 1


class BaseRequest(BaseModel):
    """
    This class stands for a base request for the facilitator endpoints.
    """

    x402_version: int = Field(
        default=X402_VERSION, alias="x402Version",
        description="The involved x402 version, for compatibility with the protocol"
    )
    payment_payload: PaymentPayload = Field(
        alias="paymentPayload",
        description="The client-sent payload"
    )
    payment_requirements: PaymentRequirements = Field(
        alias="paymentRequirements",
        description="The allowed requirements for this payment"
    )

    def to_json(self):
        """
        Builds the JSON payload of this base request object.

        Returns:
            A dictionary with the JSON response.
        """

        return {
            "x402Version": self.x402_version,
            "paymentPayload": self.model_dump(by_alias=True),
            "paymentRequirements": self.model_dump(
                by_alias=True, exclude_none=True
            ),
        }


class VerifyRequest(BaseRequest):
    """
    This class stands for the body a request to the /verify endpoint.
    """


class VerifyResponse(BaseModel):
    """
    This class stands for the body of a /verify response.
    """

    is_valid: bool = Field(alias="isValid")
    invalid_reason: Optional[str] = Field(default=None, alias="invalidReason")
    payer: Optional[str] = Field(default=None)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class SettleRequest(BaseRequest):
    """
    This class stands for the body of a request to the /settle endpoint.
    """


class SettleResponse(BaseModel):
    """
    This class stands for the body of a /settle response.
    """

    success: bool
    error_reason: Optional[str] = Field(None, alias="errorReason")
    transaction: Optional[str] = None
    network: Optional[str] = None
    payer: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


FacilitatorHeaders = Dict[Literal['settle', 'verify'], dict | Callable[[], dict] | Callable[[], Awaitable[dict]]]
FacilitatorHeaders.__doc__ = """
The way the headers are built when performing requests to
an x402 facilitator. They can be per endpoint and of types:

1. A dictionary.
2. A callable returning a dictionary of headers.
3. An awaitable callable returning a dictionary of headers.
"""


class FacilitatorConfig(BaseModel):
    """
    Configuration for the X402 facilitator service.

    Attributes:
        url: The base URL for the facilitator service.
        headers: Optional function to create authentication headers.
    """

    url: str = Field(
        default="https://x402.org/facilitator",
        description="The URL of the facilitator. It does not need to be a top-level URL but must "
                    "have two facilitator-compatible sub-endpoints named /verify and /settle"
    )
    headers: Optional[FacilitatorHeaders] = Field(
        default=None,
        description="The headers, or header-generation callables, to generate the headers for "
                    "each of the endpoints"
    )
