from ..types.errors import MisconfigurationError
from ..types.requirements import FinalRequiredPaymentDetails, RequirePaymentDetails, Price, TokenAmount
from ..types.setup import Y402Setup


class PriceComputingError(Exception):
    """
    Tells an error occurred while computing the price
    of an endpoint.
    """


def _get_chain_id(network: str, setup: Y402Setup):
    try:
        int(network)
        return network
    except ValueError:
        try:
            return setup.get_chain_id(network)
        except KeyError:
            raise PriceComputingError("Unsupported network: " + network)


def _resolve_payment_price(
    network: str, price: Price, setup: Y402Setup
):
    if isinstance(price, str):
        return setup.parse_price_label(network, price)
    elif isinstance(price, int):
        code = setup.get_default_token(network)
        if code is None:
            raise MisconfigurationError(f"The network {network} does not have a default token")
        name, _, address, version, _ = setup.get_token_metadata(network, code)
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