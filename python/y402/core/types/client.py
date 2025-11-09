from pydantic import BaseModel, ConfigDict, field_validator, Field
from pydantic.alias_generators import to_camel


class EIP3009Authorization(BaseModel):
    """
    This class stands for an EIP-3009 authorization body, without the signature.
    """

    from_: str = Field(alias="from", description="The address sending the token")
    to: str = Field(description="The address that will receive the tokens")
    value: str = Field(description="The amount being send, as a decimal representation of minimal units")
    valid_after: str = Field(description="An EVM-compatible number, as a decimal representation, being the first "
                                         "instant of validity for the signature")
    valid_before: str = Field(description="An EVM-compatible number, as a decimal representation, being the last "
                                          "instant of validity for the signature")
    nonce: str = Field(description="A decimal representation of the nonce for this authorization")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("value")
    def validate_value(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError("value must be an integer encoded as a string")
        return v


class SchemePayload(BaseModel):
    """
    This class stands for the client-chosen payload from the server.
    """

    signature: str = Field(description="The 0x-prefixed hexadecimal value of the signature")
    authorization: EIP3009Authorization = Field(description="The authorization payload matching the signature")


class PaymentPayload(BaseModel):
    """
    This class stands for the full client-provided payment payload.
    """

    x402_version: int = Field(
        default=1,
        description="The payment payload version, e.g. 1"
    )
    scheme: str = Field(
        default='exact',
        description="The payment payload scheme, e.g. 'exact'"
    )
    network: str = Field(
        description="The payment network by name (e.g. 'base', 'base-sepolia')"
    )
    payload: SchemePayload = Field(
        description="The payment payload. This one does NOT include the contract's "
                    "address, so different supported per-network addresses should "
                    "be tried (unless hinted otherwise) to tell which token this "
                    "signature belongs to"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
