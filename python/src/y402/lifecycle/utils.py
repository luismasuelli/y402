from typing import List
from uuid import uuid4

from ..core.types.facilitator import Y402_VERSION
from ..types.payment import SettledPayment, PaymentIdentity, PaymentDetails


def create_settled_payment(
    payment_id: uuid4,
    # The identity of the payment.
    resource: str, tags: List[str], reference: str,
    # The payer, chain id, token / value, and target address.
    payer: str, chain_id: int, token: str, value: str, pay_to_address: str,
    # The descriptive data.
    code: str, name: str, price_label: str
    # The transaction hash for the settlement.
) -> SettledPayment:
    """
    This utility lets the user create a settled payment, out
    of the input data and values.

    Args:
        payment_id: The internal / tracking id of the payment.
        resource: The resource URL.
        tags: The associated payment tags.
        reference: The external / public reference of the payment.
        payer: The address of the payer.
        chain_id: The chain id.
        token: The token contract's address.
        value: The value.
        pay_to_address: The address that received the payment.
        code: The codename of the token (optional, or "" - typically provided).
        name: The name of the token (optional, or "" - typically provided).
        price_label: The price label of this payment.

    Returns:
        A settled payment record.
    """

    return SettledPayment(
        id=str(payment_id),
        version=Y402_VERSION,
        identity=PaymentIdentity(
            resource=resource,
            tags=tags,
            reference=reference
        ),
        details=PaymentDetails(
            payer=payer,
            chain_id=str(chain_id),
            token=token,
            value=value,
            pay_to_address=pay_to_address,
            code=code,
            name=name,
            price_label=price_label,
        )
    )
