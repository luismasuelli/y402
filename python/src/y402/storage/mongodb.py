import datetime
from typing import List, Union
from uuid import uuid4
from pydantic import BaseModel
from pymongo import MongoClient, HASHED
from pymongo.collection import Collection
from ..types.payment import SettledPayment
from .base import StorageManager as BaseStorageManager


_BS = 50
_BE = 60


class StorageManager(BaseStorageManager):
    """
    A MongoDB-based storage manager.
    """

    def __init__(self, url: str, database: str, batch_expiration: int = _BE, batch_size: int = _BS):
        super().__init__()
        url = url.strip()
        database = database.strip()
        if not url or not database:
            raise ValueError("Both URL and database must be specified for a"
                             "MongoDB-based StorageManager")
        self._client = MongoClient(url)
        self._database = self._client[database]
        self._batch_expiration = max(_BE, batch_expiration) if isinstance(batch_expiration, int) else _BE
        self._batch_expiration_delta = datetime.timedelta(seconds=self._batch_expiration)
        self._batch_size = max(_BS, batch_size) if isinstance(batch_size, int) else _BS

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
        except:
            pass

        try:
            collection_.create_index({"webhook_name": HASHED})
        except:
            pass

        try:
            collection_.create_index({"status": HASHED})
        except:
            pass

        collection_.insert_one({
            "payment_id": str(payment_id),
            "payload": payload.model_dump(),
            "matched_requirements": matched_requirements.model_dump(),
            "status": "verified",
            "webhook_payload": settled_payment.model_dump(),
            "webhook_name": webhook_name,
            "created_on": datetime.datetime.now(tz=datetime.UTC)
        })

    def abort(self, collection: str, payment_id: uuid4):
        """
        Aborts a payment id, removing its record.

        Args:
            collection: The collection to remove the payment from.
            payment_id: The id of the payment to remove.
        """

        collection_: Collection = self._database[collection]

        collection_.delete_one({"payment_id": str(payment_id), "status": "verified"})

    def settle(self, collection: str, payment_id: uuid4, transaction: str):
        """
        Confirms a given payment id, meaning that the /settle endpoint worked.

        This update is synchronous.

        Args:
            collection: The collection to commit / confirm the payment into.
            payment_id: The id of the payment matching a stored one.
            transaction: The hash of the transaction.
        """

        self._database[collection].update_one(
            {"payment_id": str(payment_id)},
            {"$set": {
                "status": "settled",
                "webhook_payload.transaction_hash": transaction,
                "webhook_payload.settled_on": datetime.datetime.now(tz=datetime.UTC)
            }}
        )

    def _batch_one(self, collection: str, webhook_name: str, worker_id: str,
                   stamp: datetime.datetime) -> bool:
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
            stamp: The pivot stamp to compute the date.

        Returns:
            Whether one record could be batched or not.
        """

        min_date = stamp - self._batch_expiration_delta
        result = self._database[collection].find_one_and_update({
            "status": "settled",
            "webhook_name": webhook_name,
            "$or": [
                {"batched_on": {"$exists": False}},
                {"batched_on": {"$lte": min_date}},
                {"worker": {"$exists": False}},
                {"worker": {"$in": ["", None]}},
            ]
        }, {"$set": {"worker": worker_id, "batched_on": stamp}})
        return result is not None

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

        # 1. Get the batch size and limit stamps.
        batch_size = self._batch_size
        stamp = datetime.datetime.now(tz=datetime.UTC)
        min_date = stamp - self._batch_expiration_delta

        # 2. Batch remaining items.
        already_batched_count = self._database[collection].count_documents({
            "status": "settled",
            "webhook_name": webhook_name,
            "worker": worker_id,
            "batched_on": {"$gt": min_date}
        })
        if already_batched_count < batch_size:
            for _ in range(batch_size - already_batched_count):
                if not self._batch_one(collection, webhook_name, worker_id, stamp):
                    break

        # 3. Return the records.
        result = []
        cursor = self._database[collection].find({
            "status": "settled",
            "webhook_name": webhook_name,
            "worker": worker_id,
            "batched_on": {"$gt": min_date}
        })
        for document in cursor:
            document.pop("_id", None)
            result.append(SettledPayment(**document["webhook_payload"]))
        return result

    def mark_as_sent(self, collection: str, payment_id: Union[str, uuid4]):
        """
        Marks a payment as webhook-sent.

        Args:
            collection: The collection to mark a payment into.
            payment_id: The payment id.
        """

        self._database[collection].update_one({
            "status": "settled",
            "payment_id": str(payment_id)
        }, {"$set": {"status": "finished"}})
