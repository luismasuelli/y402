from typing import Optional
from .endpoint_settings import X402_ENDPOINT_SETTINGS
from .setup import Y402Setup


class FinalEndpointSetupRegistry:
    """
    This is a registry of endpoints, under a single middleware,
    and the support for their networks and tokens.

    It works like a lazy retriever of endpoint-related custom data.
    For each endpoint that is queried, it's extended support data
    is generated and retrieved.
    """

    def __init__(self, middleware_custom_setup: Optional[Y402Setup]):
        self._full_data_by_endpoint = {}
        self._middleware_custom_setup = middleware_custom_setup

    def __getitem__(self, item):
        if item not in self._full_data_by_endpoint:
            endpoint_settings = getattr(item, X402_ENDPOINT_SETTINGS, None)
            endpoint_custom_setup = endpoint_settings and endpoint_settings.custom_setup
            if self._middleware_custom_setup and endpoint_custom_setup:
                setup = self._middleware_custom_setup | endpoint_custom_setup
            else:
                setup = self._middleware_custom_setup or endpoint_custom_setup or Y402Setup()
            self._full_data_by_endpoint[item] = setup
        return self._full_data_by_endpoint[item]
