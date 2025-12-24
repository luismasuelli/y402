import inspect
import logging
import threading
import time
from typing import Any, List
from httpx import Client
from ..core.types.payment import SettledPayment
from ..core.types.storage import StorageManager


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _forbid_awaitable(result: Any, method: str) -> Any:
    if inspect.isawaitable(result):
        raise TypeError(f"The result of StorageManage.{method}(...) must not be an awaitable "
                        "in this process_payment implementation")
    return result


def _send_batch(
    worker_id: str, webhook_name: str, webhook_url: str, api_key: str,
    storage_manager: StorageManager, collection: str, logger: logging.Logger
):
    """
    Performs the processing of a single batch being sent. This updates
    the status of the in-batch processed payments, so new calls to this
    method are not idempotent.

    Args:
        worker_id: The id of this worker.
        webhook_name: The name of the webhook to look records for.
        webhook_url: The URL to send requests to.
        api_key: The api key to use in the X-API-Key header, if any.
        storage_manager: The associated storage manager.
        collection: The collection to use with the manager.
        logger: An optional logger.
    """

    def _send(client: Client, payload: SettledPayment):
        try:
            response = client.post(url=webhook_url, headers=headers, json=payload.model_dump(mode="json"))
            response.raise_for_status()
            _forbid_awaitable(storage_manager.mark_as_sent(collection, payload.id_), "mark_as_sent")
        except:
            logger.exception(f"An exception occurred when processing payment with id={payload.id_}")

    api_key = api_key.strip()
    headers = {"X-API-Key": api_key} if api_key else {}
    logger.info("Processing a batch:")
    logger.info("- Retrieving the batch...")
    batch: List[SettledPayment] = _forbid_awaitable(storage_manager.get_batch(collection, webhook_name, worker_id),
                                                    "get_batch")
    logger.info(f"- Sending the batch ({len(batch)} elements)...")
    with Client(timeout=15) as client:
        threads = [threading.Thread(target=lambda: _send(client, payload)) for payload in batch]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    logger.info("- Updating the batch...")
    for element in batch:
        storage_manager.mark_as_sent(collection, element.id_)


def webhook_worker(
    worker_id: str, webhook_name: str, webhook_url: str, api_key: str,
    manager: StorageManager, collection: str, logger: logging.Logger = None,
    sleep_time: int = 5
):
    """
    Sends a batch of settled requests, assigned to a webhook name, to the
    corresponding webhook URL (and with proper authentication, if any).
    It uses a specific worker name for this, so it does not collide with
    other workers in the same process.

    Args:
        worker_id: The id of this worker.
        webhook_name: The name of the webhook to look records for.
        webhook_url: The URL to send requests to.
        api_key: The api key to use in the X-API-Key header, if any.
        manager: The associated storage manager.
        collection: The collection to use with the manager.
        logger: An optional logger.
        sleep_time: A sleep time between iterations.
    """

    logger = logger or LOGGER

    logger.info(f"Starting webhook worker loop.\n- webhook_name={webhook_name}\n- worker_id={worker_id}")
    try:
        while True:
            _send_batch(worker_id, webhook_name, webhook_url, api_key, manager, collection, logger)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info(f"Worker loop cancelled by the user")
    except:
        logger.exception("Worker loop stopped because of an error:")
