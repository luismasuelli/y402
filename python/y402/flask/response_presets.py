from typing import List, Optional
from flask import request, Response, make_response, jsonify
from y402.core.types.facilitator import X402_VERSION
from y402.core.types.paywall import PaywallConfig
from y402.core.types.requirements import PaymentRequirements
from y402.core.types.responses import x402PaymentRequiredResponse
from y402.core.utils.headers import is_browser_request
from y402.core.utils.html import get_paywall_html


def x402_response(
    error: str,
    custom_paywall_html: Optional[str],
    paywall_config: Optional[PaywallConfig],
    payment_requirements: List[PaymentRequirements],
) -> Response:
    """
    Creates a 402 response with payment requirements.

    Args:
        error: The message of the concrete error that occurred.
        custom_paywall_html: The paywall HTML to render for HTML requests.
        paywall_config: The configuration for the paywall.
        payment_requirements: The alternate payment requirements.
    Returns:
        A Response object.
    """

    request_headers = dict(request.headers)
    status_code = 402

    if is_browser_request(request_headers):
        html_content = custom_paywall_html or get_paywall_html(
            error, payment_requirements, paywall_config
        )
        headers = {"Content-Type": "text/html; charset=utf-8"}

        resp = make_response(html_content, status_code)
        resp.headers.update(headers)
        return resp
    else:
        response_data = x402PaymentRequiredResponse(
            x402_version=X402_VERSION,
            accepts=payment_requirements,
            error=error,
        ).model_dump(by_alias=True)

        headers = {"Content-Type": "application/json"}

        resp = make_response(jsonify(response_data), status_code)
        resp.headers.update(headers)
        return resp
