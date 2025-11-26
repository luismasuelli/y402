import inspect
import uuid
from typing import List, Tuple, Any
from uuid import uuid4
from ..core.types.client import PaymentPayload
from ..core.types.facilitator import VerifyRequest, X402_VERSION, FacilitatorConfig, SettleRequest, SettleResponse
from ..core.types.requirements import PaymentRequirements
from ..core.types.setup import Y402Setup
from ..core.types.storage import StorageManager
from ..facilitator_client.requests import FacilitatorClient
from ..lifecycle.utils import create_settled_payment
from ..triggers.requests import send_payment


def _forbid_awaitable(result: Any, method: str) -> Any:
    if inspect.isawaitable(result):
        raise TypeError(f"The result of StorageManage.{method}(...) must not be an awaitable "
                        "in this process_payment implementation")
    return result


async def process_payment(
    # The identity of the payment.
    resource: str, tags: List[str], reference: str,
    # User payment selection.
    payment: PaymentPayload, matched_requirements: PaymentRequirements,
    # External components.
    setup: Y402Setup, facilitator_config: FacilitatorConfig,
    # Storage.
    storage_manager: StorageManager, storage_collection: str,
    # Webhook-related data.
    webhook_name: str,
    # Tunings.
    request_timeout: int = 15
) -> Tuple[uuid.UUID, SettleResponse]:
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
        storage_collection: The collection to store the payment into.
        webhook_name: The name of the webhook.
        request_timeout: The timeout for requests.

    Returns:
        The processed UUID for this payment. Also, the settle response, if any.
    """

    # 1. Prepare all the data for a settled payment. Do this in advance
    #    so no failures are spotted later, on settling, on this topic.
    payer = payment.payload.authorization.from_
    network = payment.network
    token = matched_requirements.asset
    value = payment.payload.authorization.value
    chain_id, code, name, price_label = setup.get_payment_data(network, token, value)
    payment_id = uuid4()
    settled_payment = create_settled_payment(
        payment_id, resource, tags, reference,
        payer, chain_id, token, value,
        code, name, price_label
    )

    # 2. Create the facilitator config.
    facilitator_client = FacilitatorClient(facilitator_config)

    # 3. Perform the verification.
    facilitator_client.verify(VerifyRequest(
        x402_version=X402_VERSION,
        payment_payload=payment,
        payment_requirements=matched_requirements,
        timeout=request_timeout
    ))

    # 4. Store the verified payment. Done so, if the settlement
    #    fails and the client complains that the authorization
    #    was consumed, then the data is present for any claim.
    #    Abusing this system would involve a decent amount of
    #    gas consumption from the client, so very often this
    #    will be legit.
    _forbid_awaitable(storage_manager.allocate(
        storage_collection, payment_id, payment, matched_requirements,
        settled_payment, webhook_name
    ), "allocate")

    # 5. Settle the payment. By this point, the payment is consumed
    #    and the corresponding record is marked as such.
    response = facilitator_client.settle(SettleRequest(
        x402_version=X402_VERSION,
        payment_payload=payment,
        payment_requirements=matched_requirements,
        timeout=request_timeout
    ))

    # 6. Here, the response was successful in terms of HTTP (200)
    #    and the settling was successful as well.
    #
    #    If the setting were not to be successful, then it would
    #    not execute this point (committing the settlement).
    if response.success:
        _forbid_awaitable(storage_manager.settle(
            storage_collection, payment_id
        ), "commit")
    return payment_id, response
