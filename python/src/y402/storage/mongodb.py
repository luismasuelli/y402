from typing import List
from uuid import uuid4
from pymongo import MongoClient, HASHED
from pymongo.collection import Collection
from ..core.types.client import PaymentPayload
from ..core.types.payment import SettledPayment
from ..core.types.requirements import PaymentRequirements
from ..core.types.storage import StorageManager as BaseStorageManager


class StorageManager(BaseStorageManager):
    """
    A MongoDB-based storage manager.
    """

    def __init__(self, url: str, database: str):
        url = url.strip()
        database = database.strip()
        if not url or not database:
            raise ValueError("Both URL and database must be specified for a"
                             "MongoDB-based StorageManager")
        self._client = MongoClient(url)
        self._database = self._client[database]

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

        collection_: Collection = self._database[collection]

        try:
            collection_.create_index({"payment_id": HASHED}, unique=True)
            collection_.create_index({"webhook_name": HASHED})
            collection_.create_index({"status": HASHED})
        except:
            pass

        collection_.insert_one({
            "payment_id": payment_id,
            "payload": payload.model_dump(),
            "matched_requirements": matched_requirements.model_dump(),
            "status": "verified",
            "webhook_payload": settled_payment,
            "webhook_name": webhook_name
        })

    def settle(self, collection: str, payment_id: uuid4):
        """
        Confirms a given payment id, meaning that the /settle endpoint worked.

        This update is synchronous.

        Args:
            collection: The collection to commit / confirm the payment into.
            payment_id: The id of the payment matching a stored one.
        """

        self._database[collection].update_one(
            {"payment_id": payment_id},
            {"$set": {"status": "settled"}}
        )

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

        # TODO implement atomic batching.
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

        # TODO implement atomic batching.
        raise NotImplementedError
