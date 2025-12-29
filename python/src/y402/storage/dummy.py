from typing import List, Union
from uuid import uuid4
from pydantic import BaseModel
from ..types.payment import SettledPayment
from .base import StorageManager as BaseStorageManager


_BS = 50
_BE = 60


class StorageManager(BaseStorageManager):
    """
    A dummy storage manager.
    """

    def allocate(self, collection: str, payment_id: uuid4,
                 payload: BaseModel, matched_requirements: BaseModel,
                 settled_payment: SettledPayment, webhook_name: str):
        """
        Dummy implementation of allocate(collection, payment_id, payload, matched_requirements,
        settled_payment, webhook_name). It's a no-op.
        """

    def abort(self, collection: str, payment_id: uuid4):
        """
        Dummy implementation of abort(collection, payment_id). It's a no-op.
        """

    def settle(self, collection: str, payment_id: uuid4, transaction: str):
        """
        Dummy implementation of settle(collection, payment_id, transaction). It's a no-op.
        """

    def get_batch(self, collection: str, webhook_name: str, worker_id: str) -> List[SettledPayment]:
        """
        Dummy implementation of get_batch(collection, webhook_name, worker_id). It's a no-op.
        """

        return []

    def mark_as_sent(self, collection: str, payment_id: Union[str, uuid4]):
        """
        Dummy implementation of mark_as_sent(collection, payment_id). It's a no-op.
        """
