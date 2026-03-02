import json
from typing import List, Optional, Dict, Any
from .template import PAYWALL_TEMPLATE
from ..types.constants import X402_VERSION
from ..types.paywall import PaywallConfig
from ..types.requirements import PaymentRequirements


def create_x402_config(
    error: str,
    payment_requirements: List[PaymentRequirements],
    paywall_config: Optional[PaywallConfig] = None,
) -> Dict[str, Any]:
    """
    Create x402 configuration object from payment requirements.
    """

    requirements = payment_requirements[0] if payment_requirements else None
    display_amount = 0
    current_url = ""
    testnet = True

    if requirements:
        # Convert atomic amount back to USD (assuming USDC with 6 decimals)
        try:
            display_amount = (
                    float(requirements.max_amount_required) / 1000000
            )  # USDC has 6 decimals
        except (ValueError, TypeError):
            display_amount = 0

        current_url = requirements.resource or ""
        testnet = requirements.network == "base-sepolia"

    # Get paywall config values or defaults
    config = paywall_config or {}

    # Create the window.x402 configuration object
    return {
        "amount": display_amount,
        "paymentRequirements": [
            req.model_dump(by_alias=True) for req in payment_requirements
        ],
        "testnet": testnet,
        "currentUrl": current_url,
        "error": error,
        "x402Version": X402_VERSION,
        "cdpClientKey": config.get("cdp_client_key", ""),
        "appName": config.get("app_name", ""),
        "appLogo": config.get("app_logo", ""),
        "sessionTokenEndpoint": config.get("session_token_endpoint", ""),
    }


def inject_payment_data(
    html_content: str,
    error: str,
    payment_requirements: List[PaymentRequirements],
    paywall_config: Optional[PaywallConfig] = None,
) -> str:
    """
    Injects payment requirements into HTML as JavaScript variables.

    Args:
        html_content: The HTML content to insert.
        error: Error message to display.
        payment_requirements: List of payment requirements.
        paywall_config: Optional paywall UI configuration.

    Returns:
        The final contents.
    """

    # Create x402 configuration object
    x402_config = create_x402_config(error, payment_requirements, paywall_config)

    # Create the configuration script (matching TypeScript pattern)
    log_on_testnet = (
        "console.log('Payment requirements initialized:', window.x402);"
        if x402_config["testnet"]
        else ""
    )

    config_script = f"""
  <script>
    window.x402 = {json.dumps(x402_config)};
    {log_on_testnet}
  </script>"""

    # Inject the configuration script into the head (same as TypeScript)
    return html_content.replace("</head>", f"{config_script}\n</head>")


def get_paywall_html(
    error: str,
    payment_requirements: List[PaymentRequirements],
    paywall_config: Optional[PaywallConfig] = None,
) -> str:
    """
    Load paywall HTML and inject payment data.

    Args:
        error: Error message to display.
        payment_requirements: List of payment requirements.
        paywall_config: Optional paywall UI configuration.

    Returns:
        Complete HTML with injected payment data.
    """

    return inject_payment_data(
        PAYWALL_TEMPLATE, error, payment_requirements, paywall_config
    )
