import base64
import traceback
from typing import Callable, Optional, List, Literal
import logging
from fastapi import Request, HTTPException
from pydantic import validate_call
from .prices import compute_prices
from .request_data import resolve_endpoint, get_root_url
from .response_presets import x402_response, response
from .types.endpoint_settings import X402EndpointSettings, Y402_ENDPOINT_SETTINGS
from ..core.types.facilitator import FacilitatorConfig
from ..core.types.paywall import PaywallConfig
from ..core.types.registry import FinalEndpointSetupRegistry
from ..core.types.requirements import FinalRequiredPaymentDetails, PaymentRequirements
from ..core.types.setup import Y402Setup
from ..core.types.storage import StorageManager
from ..core.utils.headers import decode_payment_header, validate_payment_asset
from ..core.utils.prices import PriceComputingError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@validate_call
def payment_required(
    *,
    mime_type: str = "",
    default_max_deadline_seconds: int = 60,
    paywall_config: Optional[PaywallConfig] = None,
    custom_paywall_html: Optional[str] = None,
    facilitator_config: Optional[FacilitatorConfig] = None,
    setup: Optional[FinalEndpointSetupRegistry] = None,
    client_http_library: Literal["httpx"] = "httpx",
    storage_manager: Optional[StorageManager] = None,
    request_timeout: int = 60
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
        storage_manager: The default storage manager. If not set, it must set on each of the endpoints
                         configured to be Y402-defined. Storage managers are used to store the requested
                         and paid-for jobs.
        request_timeout: The timeout for the webhook requests.

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

        if storage_manager is None:
            logger.error(f"Storage manager not defined")
            return response(
                request, 500, f"The resource {resource_url} is not properly configured",
                custom_paywall_html_, paywall_config_, [], {}
            )

        reference = ''
        if endpoint_data.reference_param is not None:
            reference = request.path_params.get(endpoint_data.reference_param, None)
            if reference is None:
                logger.error(f"Path parameter '{endpoint_data.reference_param}' not defined for "
                             f"resource {resource_url}")
                return response(
                    request, 500, f"The resource {resource_url} is not properly configured",
                    custom_paywall_html_, paywall_config_, [], {}
                )

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
            chain_id_by_name = merged_setup.get_chain_ids_mapping()
            prices: List[FinalRequiredPaymentDetails] = await compute_prices(
                request, endpoint_data.payments_details, merged_setup
            )
        except HTTPException:
            logger.exception("An early-terminating HTTP exception occurred at price computing stage:")
            raise
        except PriceComputingError as e:
            logger.exception("An error occurred at price computing stage:")
            return response(
                request, 500, f"The resource {resource_url}'s setup / pricing is not properly configured: {str(e)}",
                custom_paywall_html_, paywall_config_, [], {}
            )
        except:
            logger.exception("An error occurred at price computing stage:")
            return response(
                request, 500, f"The resource {resource_url}'s setup / pricing is not properly configured",
                custom_paywall_html_, paywall_config_, [], {}
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
                                 paywall_config_, payment_requirements, chain_id_by_name)

        # 6. Extract the payment header.
        try:
            payment = decode_payment_header(payment_header)
        except Exception:
            logger.exception(
                f"Invalid payment header format from {request.client.host if request.client else 'unknown'}:"
            )
            return x402_response(request, "Invalid payment header format", custom_paywall_html_,
                                 paywall_config_, payment_requirements, chain_id_by_name)

        # 7. Extract the extra header, perhaps, with payment token. It
        #    must be an address, if present.
        payment_asset_header = request.headers.get("X-PAYMENT-ASSET", "").lower()

        # 8. Based on the payment_token_header, if available, select
        #    which token was selected. Otherwise, iterate until a
        #    token matches the signature.
        network = payment.network
        code, asset, ok = validate_payment_asset(network, payment, payment_asset_header, merged_setup)
        if not ok:
            logger.error(
                f"Invalid payment header format from {request.client.host if request.client else 'unknown'}:"
            )
            return x402_response(request, "Invalid payment asset", custom_paywall_html_,
                                 paywall_config_, payment_requirements, chain_id_by_name)

        # 9. Pick the proper payment by the code, and make use of it later.
        requirement = next(
            (requirement
             for requirement in payment_requirements
             if requirement.asset == asset and requirement.network == network),
            None
        )
        if not requirement:
            return x402_response(request, "Invalid payment asset", custom_paywall_html_,
                                 paywall_config_, payment_requirements, chain_id_by_name)

        # 10. Pick the proper payment processor adapter.
        match client_http_library:
            case "httpx":
                from ..lifecycle.httpx import process_payment
            case _:
                return x402_response(request, "Server not properly configured", custom_paywall_html_,
                                     paywall_config_, payment_requirements, chain_id_by_name)

        # 11. Actually process the payment.
        try:
            payment_id, error, settle_response = await process_payment(
                resource_url, endpoint_data.tags, reference, payment,
                requirement, merged_setup, facilitator_config,
                storage_manager, endpoint_data.webhook_name
            )
            if error:
                lines = traceback.format_exception(error)
                logger.warning("WARNING!!! An error occurred while trying to forward the "
                               "payment to the endpoint:\n" + '\n'.join(lines))
                if not settle_response.success:
                    return x402_response(request, "Settle failed: " +
                                         (settle_response.error_reason or "Unknown error"),
                                         custom_paywall_html_, paywall_config_, payment_requirements,
                                         chain_id_by_name)
        except:
            logger.exception("An exception occurred when interacting with the facilitator or forwarding "
                             "the payment:")
            return x402_response(request, "The payment was invalid or it was an error processing it",
                                 custom_paywall_html_, paywall_config_, payment_requirements, chain_id_by_name)

        # 12. As state, keep: The payment_id, the send payment error (if any),
        #     and the reference (it might be blank).
        request.state.x402 = {
            "payment_id": payment_id,
            "send_payment_error": error,
            "reference": reference
        }

        # 13. Call and wrap the underlying endpoint, which should have a very small logic.
        try:
            response_ = await call_next(request)
            response_.headers["X-PAYMENT-RESPONSE"] = base64.b64encode(
                settle_response.model_dump_json(by_alias=True).encode("utf-8")
            ).decode("utf-8")
            return response
        except:
            return response(request, 500,
                            "An error occurred, but a payment was already processed. Contact support "
                            f"to claim your product or service by the internal payment id: {payment_id}",
                            custom_paywall_html_, paywall_config_, [], chain_id_by_name)

    return middleware
