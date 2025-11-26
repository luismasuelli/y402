from uuid import uuid4
from ...core.types.client import PaymentPayload
from ...core.types.requirements import PaymentRequirements
from .payment import SettledPayment


class StorageManager:
    """
    This class defines a synchronous storage manager for
    the post-verified user payment requests.
    """

    def allocate(self, collection: str, payment_id: uuid4,
                 payload: PaymentPayload, matched_requirements: PaymentRequirements,
                 settled_payment: SettledPayment, webhook_name: str):
        """
        Stores an authorization in 'verified' state. It tells the authorization
        (signed by the `from` sender) and the matched requirement. Ideally, the
        implementation of this method will store the data in some sort of store
        where the matched_requirements are a separate table, and the payment id
        serves as primary key, while the payload contains the whole data.

        These records serve well to track the evolution of a paid requirement
        and also address user claims. This also means: this method must NOT fail
        silently but be violent enough with the payment failing to be stored.

        The storage manager is totally free to choose other fields for the data
        (e.g. some sort of tagging) system.

        This allocation is synchronous.

        Args:
            collection: The collection to store the payment into.
            payment_id: The id of the payment (generated on the fly).
            payload: The client payload fromm headers.
            matched_requirements: The matched requirements.
            settled_payment: The settled payment record. It will be sent
                             via webhook after settlement.
            webhook_name: The associated webhook name to use on launch
                          after settlement.
        """

        raise NotImplementedError

    def settle(self, collection: str, payment_id: uuid4):
        """
        Confirms a given payment id, meaning that the /settle endpoint worked.

        This update is synchronous.

        Args:
            collection: The collection to commit / confirm the payment into.
            payment_id: The id of the payment matching a stored one.
        """

        raise NotImplementedError
