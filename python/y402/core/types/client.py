from pydantic import BaseModel, ConfigDict, field_validator, Field
from pydantic.alias_generators import to_camel


class EIP3009Authorization(BaseModel):
    """
    This class stands for an EIP-3009 authorization body, without the signature.
    """

    from_: str = Field(alias="from")
    to: str
    value: str
    valid_after: str
    valid_before: str
    nonce: str

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

    signature: str
    authorization: EIP3009Authorization


class PaymentPayload(BaseModel):
    """
    This class stands for the full client-provided payment payload.
    """

    x402_version: int
    scheme: str
    network: str
    payload: SchemePayload

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
