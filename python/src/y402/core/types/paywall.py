from typing import TypedDict


class PaywallConfig(TypedDict, total=False):
    """
    Configuration for paywall UI customization.
    """

    cdp_client_key: str
    app_name: str
    app_logo: str
    session_token_endpoint: str
