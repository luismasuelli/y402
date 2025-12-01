from typing import Optional, Any, Union, Literal
import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from .eip712 import EIP712Domain


class TokenAsset(BaseModel):
    """
    Represents token asset information including EIP-712
    domain data.
    """

    address: str
    decimals: int
    eip712: EIP712Domain

    @field_validator("decimals")
    def validate_decimals(cls, v):
        if v < 0 or v > 255:
            raise ValueError("decimals must be between 0 and 255")
        return v


class TokenAmount(BaseModel):
    """
    Represents an amount of tokens in atomic units with asset
    information.
    """

    amount: str
    asset: TokenAsset

    @field_validator("amount")
    def validate_amount(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError("amount must be an integer encoded as a string")
        return v


Price = Union[str, int, TokenAmount]


class RequirePaymentDetails(BaseModel):
    """
    This is a payment requirement specification that applies
    for an endpoint in particular.
    """

    scheme: Literal["exact"] = Field(description="The scheme", default="exact")
    network: str = Field(
        description="The human name of the network (e.g. ethereum, ethereum-sepolia, "
                    "base, base-sepolia, avalanche, avalanche-fuji)"
    )
    price: Price = Field(
        description="The price, which can be any x402-supported price type"
    )
    pay_to_address: str = Field(
        description="The address to pay to. It must be a valid address"
    )

    @field_validator("pay_to_address")
    def validate_pay_to_address(cls, v):
        if not re.match(r"^0x[a-fA-F0-9]{40}$", v):
            raise ValueError("pay_to_address must be a 0x-prefixed 40-hex digits string")
        return v

    @field_validator("price")
    def validate_price(cls, v):
        has_allowed_type = True

        if not isinstance(v, (str, int, TokenAmount)):
            has_allowed_type = False
        if isinstance(v, str):
            if v[0] == '$':
                v = v[1:]
            try:
                if float(v) < 0:
                    raise Exception()
            except:
                has_allowed_type = False
        elif isinstance(v, int):
            if v < 0:
                has_allowed_type = False
        elif isinstance(v, TokenAmount):
            try:
                if int(v.amount) < 0:
                    raise Exception()
            except:
                has_allowed_type = False

        if not has_allowed_type:
            raise ValueError(f"The price must be a valid positive numeric str (can be $-prefixed), "
                             f"a positive int, or a positive TokenAmount object")

        return v


class PaymentRequirements(BaseModel):
    """
    This is the details of a payment requirement that both
    server and client agree on.
    """

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


class FinalRequiredPaymentDetails(BaseModel):
    """
    This is a final payment requirement specification
    that applies for an endpoint in particular.
    """

    scheme: str = Field(description="The scheme", default="exact")
    network: str = Field(
        description="The human name of the network (e.g. ethereum, ethereum-sepolia, "
                    "base, base-sepolia, avalanche, avalanche-fuji)"
    )
    asset_address: str = Field(
        description="The address of the token asset"
    )
    amount_required: str = Field(
        description="The required amount, as an uint256 value"
    )
    pay_to_address: str = Field(
        description="The address to pay to. It must be a valid address"
    )
    eip712_domain: dict = Field(
        description="The data related to the eip712 domain for this protocol"
    )
