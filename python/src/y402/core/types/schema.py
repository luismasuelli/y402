from typing import Optional, Dict, Literal, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class HTTPInputSchema(BaseModel):
    """
    Schema for HTTP request input, excluding spec
    and method which are handled by the middleware.
    """

    query_params: Optional[Dict[str, str]] = None
    body_type: Optional[
        Literal["json", "form-data", "multipart-form-data", "text", "binary"]
    ] = None
    body_fields: Optional[Dict[str, Any]] = None
    header_fields: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
