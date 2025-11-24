import uuid
from typing import List, Tuple
from uuid import uuid4
from ..core.types.client import PaymentPayload
from ..core.types.facilitator import VerifyRequest, X402_VERSION, FacilitatorConfig, SettleRequest, SettleResponse
from ..core.types.requirements import PaymentRequirements
from ..core.types.setup import Y402Setup
from ..core.types.storage import StorageManager
from ..facilitator_client.httpx import FacilitatorClient
from ..lifecycle.utils import create_settled_payment
from ..triggers.httpx import send_payment


async def process_payment(
    # The identity of the payment.
    resource: str, tags: List[str], reference: str,
    # User payment selection.
    payment: PaymentPayload, matched_requirements: PaymentRequirements,
    # External components.
    setup: Y402Setup, facilitator_config: FacilitatorConfig, storage_manager: StorageManager,
    # Webhook-related data.
    webhook_url: str, api_key: str = None,
    # Tunings.
    request_timeout: int = 15, webhook_timeout: int = 15
) -> Tuple[uuid.UUID, Exception, SettleResponse]:
    """
    Processes a given payment.

    Args:
        resource: The (PUBLIC) resource URL.
        tags: The tags that apply.
        reference: The reference that applies.
        payment: The user-submitted payment.
        matched_requirements: The matched requirements.
        setup: An existing Y402 setup.
        facilitator_config: The facilitator config to use to create a client.
        storage_manager: The storage manager for payments.
        webhook_url: The URL of the webhook to ping.
        api_key: The API key for the webhook. Optional.
        request_timeout: The timeout for requests.
        webhook_timeout: The timeout for the webhook.

    Returns:
        The processed UUID for this payment, and (if applicable) the
        error when notifying the webhook. Also, the settle response,
        if any.
    """

    # 1. Create the facilitator config.
    facilitator_client = FacilitatorClient(facilitator_config)

    # 2. Perform the verification.
    await facilitator_client.verify(VerifyRequest(
        x402_version=X402_VERSION,
        payment_payload=payment,
        payment_requirements=matched_requirements,
        timeout=request_timeout
    ))

    # 3. Store the verified payment.
    payment_id = uuid4()
    await storage_manager.allocate(payment_id, payment, matched_requirements)

    # 4. Settle the payment.
    try:
        response = await facilitator_client.settle(SettleRequest(
            x402_version=X402_VERSION,
            payment_payload=payment,
            payment_requirements=matched_requirements,
            timeout=request_timeout
        ))
        await storage_manager.commit(payment_id)
        payer = payment.payload.authorization.from_
        network = payment.network
        token = matched_requirements.asset
        value = payment.payload.authorization.value
        chain_id, code, name, price_label = setup.get_payment_data(network, token, value)
        settled_payment = create_settled_payment(
            payment_id, resource, tags, reference,
            payer, chain_id, token, value,
            code, name, price_label
        )
        send_payment_error = None
        try:
            await send_payment(webhook_url, settled_payment, api_key, webhook_timeout)
        except Exception as e:
            send_payment_error = e
        return payment_id, send_payment_error, response
    except:
        await storage_manager.rollback(payment_id)
        raise
