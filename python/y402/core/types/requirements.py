from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class PaymentRequirements(BaseModel):
    scheme: str = Field(
        default='exact',
        description="The payment payload scheme, e.g. 'exact'"
    )
    network: str = Field(
        description="The payment network by name (e.g. 'base', 'base-sepolia')"
    )
    max_amount_required: str = Field(
        description="The decimal representation of the required amount, in "
                    "terms of the minimal units"
    )
    resource: str = Field(
        description="The associated canonical resource URL or request URL for "
                    "this payment"
    )
    description: str = Field(
        description="The description of this service / the purpose of the payment"
    )
    mime_type: str = Field(
        default="application/json",
        description="The associated MIME type for this request"
    )
    output_schema: Optional[Any] = Field(
        default=None,
        description="The expected schema for this endpoint. Serves as documentation"
    )
    pay_to: str = Field(
        description="The address the payment must be authorized to"
    )
    max_timeout_seconds: int = Field(
        description="The maximum time the client is allowed to take before paying"
    )
    asset: str = Field(
        description="The 0x-prefixed ethereum address of the asset chosen "
                    "to make the payment in"
    )
    extra: Optional[dict[str, Any]] = Field(
        description="Extra data (typically used to state the EIP-712 domain"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("max_amount_required")
    def validate_max_amount_required(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError(
                "max_amount_required must be an integer encoded as a string"
            )
        return v
