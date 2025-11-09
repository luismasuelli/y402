import datetime
from uuid import uuid4
from y402.core.types.client import PaymentPayload
from y402.core.types.facilitator import VerifyRequest, X402_VERSION, FacilitatorConfig, SettleRequest
from y402.core.types.payment import SettledPayment, PaymentIdentity, PaymentDetails
from y402.core.types.requirements import PaymentRequirements
from y402.core.types.storage import StorageManager
from y402.facilitator_client.httpx import FacilitatorClient
from y402.triggers.httpx import send_payment


async def process_payment(payment: PaymentPayload, matched_requirements: PaymentRequirements,
                          facilitator_config: FacilitatorConfig, storage_manager: StorageManager,
                          webhook_url: str, api_key: str = None,
                          request_timeout: int = 15, webhook_timeout: int = 15):
    """
    Processes a given payment.

    Args:
        payment: The user-submitted payment.
        matched_requirements: The matched requirements.
        facilitator_config: The facilitator config to use to create a client.
        storage_manager: The storage manager for payments.
        webhook_url: The URL of the webhook to ping.
        api_key: The API key for the webhook. Optional.
        request_timeout: The timeout for requests.
        webhook_timeout: The timeout for the webhook.
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
        await facilitator_client.settle(SettleRequest(
            x402_version=X402_VERSION,
            payment_payload=payment,
            payment_requirements=matched_requirements,
            timeout=request_timeout
        ))
        await storage_manager.commit(payment_id)
        # TODO continue these all fields.
        settled_payment = SettledPayment(
            id_=payment_id,
            identity=PaymentIdentity(
                resource=...,
                tags=[...],
                reference=...
            ),
            details=PaymentDetails(
                payer=...,
                chain_id=...,
                token=...,
                value=...,
                code=...,
                name=...,
                price_label=...,
            ),
            settled_on=datetime.datetime.now(tz=datetime.timezone.utc)
        )
        await send_payment(webhook_url, settled_payment, api_key, webhook_timeout)
    except:
        await storage_manager.rollback(payment_id)
        raise
