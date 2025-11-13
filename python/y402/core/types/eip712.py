from pydantic import BaseModel


class EIP712Domain(BaseModel):
    """EIP-712 domain information for token signing"""

    name: str
    version: str
