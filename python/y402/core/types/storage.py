from uuid import uuid4
from y402.core.types.client import PaymentPayload
from y402.core.types.requirements import PaymentRequirements


class StorageManager:
    """
    This class defines a synchronous storage manager for
    the post-verified user payment requests.
    """

    def allocate(self, payment_id: uuid4, payload: PaymentPayload, matched_requirements: PaymentRequirements):
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
            payment_id: The id of the payment (generated on the fly).
            payload: The client payload fromm headers.
            matched_requirements: The matched requirements.
        """

        raise NotImplementedError

    def commit(self, payment_id: uuid4):
        """
        Confirms a given payment id, meaning that the /settle endpoint worked.

        This update is synchronous.

        Args:
            payment_id: The id of the payment matching a stored one.
        """

        raise NotImplementedError

    def rollback(self, payment_id: uuid4):
        """
        Rollbacks a given payment id, meaning that the /settle endpoint failed.

        This removal is synchronous.

        The payment record will be removed.

        Args:
            payment_id: The id of the payment matching a stored one.
        """

        raise NotImplementedError
