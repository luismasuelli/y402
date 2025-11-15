from typing import Callable, Optional, List, Literal
import logging
from fastapi import Request, HTTPException
from .prices import compute_prices
from .request_data import resolve_endpoint, get_root_url
from .response_presets import x402_response
from .types.endpoint_settings import X402EndpointSettings, Y402_ENDPOINT_SETTINGS
from ..core.types.facilitator import FacilitatorConfig
from ..core.types.paywall import PaywallConfig
from ..core.types.registry import FinalEndpointSetupRegistry
from ..core.types.requirements import FinalRequiredPaymentDetails, PaymentRequirements
from ..core.types.setup import Y402Setup
from ..core.utils.headers import decode_payment_header
from ..core.utils.prices import PriceComputingError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def payment_required(
    mime_type: str = "",
    default_max_deadline_seconds: int = 60,
    paywall_config: Optional[PaywallConfig] = None,
    custom_paywall_html: Optional[str] = None,
    facilitator_config: Optional[FacilitatorConfig] = None,
    setup: Optional[FinalEndpointSetupRegistry] = None,
    client_http_library: Literal["httpx"] = "httpx"
):
    """
    This factory creates a middleware that performs the
    full Y402 (extremely similar and compatible to X402)
    cycle, directly to be used in a FastAPI application.

    Args:
        mime_type: The MIME type for the answer.
        default_max_deadline_seconds: The maximum time the client can take to send the paid request.
        paywall_config: The paywall configuration (applies when serving HTML).
        custom_paywall_html: The custom paywall HTML contents (applies when serving HTML).
        facilitator_config: The configuration for the facilitator.
        setup: The general, middleware-wide, setup.
        client_http_library: The allowed client library (to make new HTTP calls with).
    Returns:
        A middleware function.
    """

    registry = FinalEndpointSetupRegistry(setup)

    async def middleware(request: Request, call_next: Callable):
        """
        This is the final middleware implementation.

        Args:
            request: The request.
            call_next: A function to invoke next (typically,
                the next middleware in the list, or endpoint).
        Returns:
            The response.
        """

        # 1. Retrieve the endpoint, and the endpoint data.
        endpoint = resolve_endpoint(request)
        endpoint_data: Optional[X402EndpointSettings] = getattr(endpoint, Y402_ENDPOINT_SETTINGS, None)
        if not isinstance(endpoint_data, X402EndpointSettings):
            return await call_next(request)

        # 2. Get / initialize the per-endpoint aggregated networks
        #    and tokens setup data, and the resource metadata.
        resource_url = get_root_url(request) + "/" + endpoint_data.resource_url.lstrip("/") \
            if endpoint_data.resource_url else str(request.url)
        description = endpoint_data.description or ""
        max_deadline_seconds = endpoint_data.max_deadline_seconds or default_max_deadline_seconds
        output_schema = endpoint_data.output_schema
        input_schema = endpoint_data.input_schema
        mime_type_ = endpoint_data.mime_type or mime_type
        paywall_config_ = endpoint_data.paywall_config or paywall_config
        custom_paywall_html_ = endpoint_data.custom_paywall_html or custom_paywall_html

        # 3. Given the per-endpoint configuration, get all the prices
        #    the user can pay. All of them will be *exact*, but can
        #    express in different networks (existing; configured ones).
        #    This said, each record will have:
        #    - The network (it's name, not the chain id; unique).
        #    - The address of the token.
        #    - The required amount (we'll use "exact" here).
        #    - The pay-to address.
        try:
            merged_setup: Y402Setup = registry[endpoint]
            prices: List[FinalRequiredPaymentDetails] = await compute_prices(
                request, endpoint_data.payments_details, merged_setup
            )
        except HTTPException:
            logger.exception("An early-terminating HTTP exception occurred at price computing stage:")
            raise
        except PriceComputingError as e:
            logger.exception("An error occurred at price computing stage:")
            return x402_response(
                request, f"The resource {resource_url}'s setup / pricing is not properly configured: {str(e)}",
                custom_paywall_html_, paywall_config_, []
            )
        except:
            logger.exception("An error occurred at price computing stage:")
            return x402_response(
                request, f"The resource {resource_url}'s setup / pricing is not properly configured",
                custom_paywall_html_, paywall_config_, []
            )

        # 4. Construct payment details. Only one payment is supported
        # per network, since even when it's not a problem in the protocol
        # itself, most of the clients will stick to this library implementation.
        payment_requirements = [
            PaymentRequirements(
                scheme=price.scheme,  # e.g. "exact"
                network=price.network,  # e.g. "ethereum"
                asset=price.asset_address,  # 0x...40 hex digits...
                max_amount_required=price.amount_required,  # ...dec digits...
                resource=resource_url,
                description=description,
                mime_type=mime_type_,
                pay_to=price.pay_to_address,  # 0x...40 hex digits...
                max_timeout_seconds=max_deadline_seconds,
                output_schema={
                    "input": {
                        "type": "http",
                        "method": request.method.upper(),
                        "discoverable": True,
                        **(input_schema.model_dump() if input_schema else {}),
                    },
                    "output": output_schema,
                },
                extra=price.eip712_domain,
            ) for price in prices
        ]

        # 5. Check for payment header. If it does not exist, halt and require
        #    a payment.
        payment_header = request.headers.get("X-PAYMENT", "")
        if payment_header == "":
            return x402_response(request, "No X-PAYMENT header provided", custom_paywall_html_,
                                 paywall_config_, payment_requirements)

        # 6. Extract the payment header.
        try:
            payment = decode_payment_header(payment_header)
        except Exception:
            logger.exception(
                f"Invalid payment header format from {request.client.host if request.client else 'unknown'}:"
            )
            return x402_response(request, "Invalid payment header format", custom_paywall_html_,
                                 paywall_config_, payment_requirements)

        # 7. Extract the extra header, perhaps, with payment token.
        payment_asset_header = request.headers.get("X-PAYMENT-ASSET", "")

        # 8. Based on the payment_token_header, if available, select
        #    which token was selected. Otherwise, iterate until a
        #    token matches the signature.

    return middleware
