from typing import List, Callable
from flask import Request
from ..core.types.requirements import RequirePaymentDetails, FinalRequiredPaymentDetails
from ..core.types.setup import Y402Setup
from ..core.utils.prices import resolve_final_payment


def compute_prices(
    request: Request,
    prices: List[RequirePaymentDetails] | Callable[[Request], List[RequirePaymentDetails]],
    setup: Y402Setup
) -> List[FinalRequiredPaymentDetails]:
    """
    Args:
        request: The current flask request.
        prices: Either the prices or a callable based on the request and returning the prices.
                Always one single price per network.
        setup: The underlying, final, Y402Setup to compute the prices from.

    Returns:
        A list of final required payment details.
    """

    if callable(prices):
        prices = prices(request)

    return [resolve_final_payment(price, setup) for price in prices]
