import traceback
from ..types.errors import MisconfigurationError
from ..types.requirements import FinalRequiredPaymentDetails, RequirePaymentDetails, Price, TokenAmount
from ..types.setup import Y402Setup


class PriceComputingError(Exception):
    """
    Tells an error occurred while computing the price
    of an endpoint.
    """


def _resolve_payment_price(
    network: str, price: Price, setup: Y402Setup
):
    if isinstance(price, str):
        try:
            code, amount = setup.parse_price_label(network, price)
            name, _, address, version, _ = setup.get_token_metadata(network, code)
            return amount, address, {"name": name, "version": version}
        except Exception:
            traceback.print_exc()
            raise PriceComputingError("There was an error while computing a price from string")
    elif isinstance(price, int):
        code = setup.get_default_token(network)
        if code is None:
            raise MisconfigurationError(f"The network {network} does not have a default token")
        try:
            name, _, address, version, _ = setup.get_token_metadata(network, code)
        except Exception:
            traceback.print_exc()
            raise PriceComputingError("There was an error while computing a price from int")
        return price, address, {"name": name, "version": version}
    elif isinstance(price, TokenAmount):
        # TokenAmount type - already in atomic units with asset info.
        return (
            price.amount,
            price.asset.address,
            {
                "name": price.asset.eip712.name,
                "version": price.asset.eip712.version,
            },
        )
    else:
        raise ValueError(f"Invalid price type: {type(price)}")


def resolve_final_payment(
    required_payment: RequirePaymentDetails,
    setup: Y402Setup
) -> FinalRequiredPaymentDetails:
    """
    Resolves a final payment based on a price specification.

    Args:
        required_payment: The required payment to base the final payment on.
        setup: The final setup for an endpoint.

    Returns:
        The final payment requirement.
    """

    amount, address, eip712_domain = _resolve_payment_price(
        required_payment.network, required_payment.price, setup
    )
    return FinalRequiredPaymentDetails(
        scheme=required_payment.scheme,
        network=required_payment.network,
        pay_to_address=required_payment.pay_to_address,
        asset_address=address,
        amount_required=amount,
        eip712_domain=eip712_domain
    )