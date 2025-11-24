from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from ...core.types.requirements import PaymentRequirements


class x402PaymentRequiredResponse(BaseModel):
    x402_version: int
    accepts: list[PaymentRequirements]
    error: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
