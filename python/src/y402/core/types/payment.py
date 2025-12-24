from datetime import datetime
from typing import List, Optional
from pydantic import Field, BaseModel


class PaymentIdentity(BaseModel):
    """
    This class holds the identity of a payment.
    """

    resource: str = Field(
        description="The URL of the resource. This URL is both user-defined "
                    "and user-configured. It has exactly one argument named "
                    "reference_ticket which can refer an object that can be "
                    "paid once or more (depending on the asset)"
    )
    tags: List[str] = Field(
        description="This is a mandatory list of tags which can be used to "
                    "identify categories for the payments. Tags are set once "
                    "per configuration and are static in nature, since they "
                    "are categories of payment processing. By configuration, "
                    "one resource URL will relate to a set of tags and a given "
                    "(internal) reference"
    )
    reference: str = Field(
        description="This is the internal reference code, primarily added "
                    "into the resource URL, as it is used to identify the "
                    "payment"
    )


class PaymentDetails(BaseModel):
    """
    This class stands for the payment details (source address, amount, token, ...).
    """

    # Canonic fields.
    payer: str = Field(description="The 0x-prefixed ethereum address of the account authorizing the payment")
    chain_id: str = Field(description="The id of the chain, in decimal representation")
    token: str = Field(description="The 0x-prefixed ethereum address of the token contract. It will support "
                                   "ERC-3009 or be somehow supported by this payment system")
    value: str = Field(description="The decimal representation of the token amount. It will be expressed in "
                                   "the minimal token units according to the decimals supported by the token")

    # Representational fields.
    code: str = Field(description="The codename of the token (e.g. usdt, usdc, eurc, eurt)")
    name: str = Field(description="The display name of the token (e.g. USDt, USDC, EURt, EURC")
    price_label: str = Field(
        description="A symbol-based representation of the amount being paid. For example, USDC and USDt "
                    "will represent 150000 as $0.15, while EURC and and EURt will represent 150000 as "
                    "€0.15. Tokens without symbol will use no symbol, representing a fractional number "
                    "according to their decimals, e.g. a 10-decimals token will represent 150000 as "
                    "0.000015, without any kind of symbol unless one is stated"
    )


class SettledPayment(BaseModel):
    """
    This class stands for a settled payment. Settled
    payments are notified via a custom webhook URL
    (POST method) so the customers can make use of
    it when attending the request.
    """

    id: str = Field(
        description="The unique ID of the payment"
    )
    version: int = Field(
        description="The y402 version"
    )
    identity: PaymentIdentity = Field(
        description="The identity of the payment (with identifier and category)"
    )
    details: PaymentDetails = Field(
        description="The details of the payment (token, network, ...)"
    )
    settled_on: Optional[datetime] = Field(
        default=None,
        description="The time this payment was settled on"
    )
    transaction_hash: Optional[str] = Field(
        default=None,
        description="The 0x-prefixed transaction hash"
    )
