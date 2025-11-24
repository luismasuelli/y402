import inspect
import asyncio
from typing import Literal
from ..core.types.facilitator import FacilitatorHeaders
from ..facilitator_client.errors import HeadersBuildingFacilitatorError


def make_headers(headers: FacilitatorHeaders, endpoint: Literal["settle", "verify"]) -> dict:
    """
    Makes the headers out of a spec. This method is synchronous.

    Args:
        headers: The headers spec for the facilitator.
        endpoint: 'settle' or 'verify'.

    Returns:
        A dictionary with the headers.
    """

    stuff = headers.get(endpoint, {})
    if isinstance(stuff, dict):
        return stuff
    else:  # callable
        try:
            obj = stuff()
            if inspect.isawaitable(stuff):
                return asyncio.run(obj)
            return obj
        except Exception as e:
            raise HeadersBuildingFacilitatorError(e)
