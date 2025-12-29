from typing import List, Union
from uuid import uuid4
from pydantic import BaseModel
from ..types.payment import SettledPayment


class StorageManager(BaseModel):
    """
    This class defines a storage manager for the (post-verified) user payment requests.
    """

    def allocate(self, collection: str, payment_id: uuid4,
                 payload: BaseModel, matched_requirements: BaseModel,
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

    def abort(self, collection: str, payment_id: uuid4):
        """
        Aborts a payment id, marking its record.

        Args:
            collection: The collection to remove the payment from.
            payment_id: The id of the payment to mark.
        """

        raise NotImplementedError

    def settle(self, collection: str, payment_id: uuid4, transaction: str):
        """
        Confirms a given payment id, meaning that the /settle endpoint worked.

        Args:
            collection: The collection to settle the payment into.
            payment_id: The id of the payment matching a stored one.
            transaction: The hash of the transaction.
        """

        raise NotImplementedError

    def batch_one(self, collection: str, webhook_name: str, worker_id: str, batch_size: int) -> bool:
        """
        Tries to find a non-batched record and batches it for the chosen
        worker. The worker will make use of batched records later and then
        proceed to do appropriate payments.

        Args:
            collection: The collection to batch a payment for a worker.
            webhook_name: The name of the webhook the records must have
                          to be batched by this method. Many workers may
                          batch for the same webook name.
            worker_id: The id of the worker to use for batching.
            batch_size: The size of the batch to work with.

        Returns:
            Whether one record could be batched or not.
        """

        raise NotImplementedError

    def get_batch(self, collection: str, webhook_name: str, worker_id: str) -> List[SettledPayment]:
        """
        Returns the current batch of records for the given worker and webhook name.

        Args:
            collection: The collection to batch a payment for a worker.
            webhook_name: The name of the webhook the records must have
                          to be batched by this method. Many workers may
                          batch for the same webook name.
            worker_id: The id of the worker to use for batching.

        Returns:
            A list of the requests to send to that webhook.
        """

        raise NotImplementedError

    def mark_as_sent(self, collection: str, payment_id: Union[str, uuid4]):
        """
        Marks a payment as webhook-sent.

        Args:
            collection: The collection to mark a payment into.
            payment_id: The payment id.
        """

        raise NotImplementedError
