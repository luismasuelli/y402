import base64
import json
from typing import Optional, List, Dict
from fastapi import Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from ...core.types.constants import X402_VERSION
from ...core.types.paywall import PaywallConfig
from ...core.types.requirements import PaymentRequirements
from ...core.types.responses import x402PaymentRequiredResponse
from ...core.utils.headers import is_browser_request
from ...core.utils.html import get_paywall_html


def response(
    request: Request, status_code: int, error: str,
    custom_paywall_html: Optional[str],
    paywall_config: Optional[PaywallConfig],
    payment_requirements: List[PaymentRequirements],
    chain_id_by_name: Dict[str, int]
) -> Response:
    """
    Creates a dynamic response with payment requirements.

    Args:
        request: The current request.
        status_code: The status code.
        error: The message of the concrete error that occurred.
        custom_paywall_html: The paywall HTML to render for HTML requests.
        paywall_config: The configuration for the paywall.
        payment_requirements: The alternate payment requirements.
        chain_id_by_name: A mapping name => chain_id from the current setup.

    Returns:
        A Response object.
    """

    request_headers = dict(request.headers)
    encoded_networks_mapping = base64.b64encode(
        json.dumps(chain_id_by_name).encode("utf-8")
    ).decode("utf-8") if chain_id_by_name else None
    headers = {
        "X-Payment-Networks": encoded_networks_mapping
    } if encoded_networks_mapping else {}

    if is_browser_request(request_headers):
        html_content = custom_paywall_html or get_paywall_html(
            error, payment_requirements, paywall_config
        )
        headers["Content-Type"] = "text/html; charset=utf-8"

        return HTMLResponse(
            content=html_content,
            status_code=status_code,
            headers=headers,
        )
    else:
        response_data = x402PaymentRequiredResponse(
            x402_version=X402_VERSION,
            accepts=payment_requirements,
            error=error,
        ).model_dump(by_alias=True)
        headers["Content-Type"] = "application/json"

        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers=headers,
        )


def x402_response(
    request: Request, error: str,
    custom_paywall_html: Optional[str],
    paywall_config: Optional[PaywallConfig],
    payment_requirements: List[PaymentRequirements],
    chain_id_by_name: Dict[str, int]
) -> Response:
    """
    Creates a 402 response with payment requirements.

    Args:
        request: The current request.
        error: The message of the concrete error that occurred.
        custom_paywall_html: The paywall HTML to render for HTML requests.
        paywall_config: The configuration for the paywall.
        payment_requirements: The alternate payment requirements.
        chain_id_by_name: A mapping name => chain_id from the current setup.

    Returns:
        A Response object.
    """

    return response(
        request, 402, error, custom_paywall_html,
        paywall_config, payment_requirements, chain_id_by_name
    )
