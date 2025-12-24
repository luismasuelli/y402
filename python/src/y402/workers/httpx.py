import asyncio
import inspect
import logging
from typing import Any, List
from httpx import AsyncClient
from ..core.types.payment import SettledPayment
from ..core.types.storage import StorageManager


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


async def _maybe_await(result: Any) -> Any:
    if inspect.isawaitable(result):
        result = await result
    return result


async def _send_batch(
    worker_id: str, webhook_name: str, webhook_url: str, api_key: str,
    manager: StorageManager, collection: str, logger: logging.Logger
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
        manager: The associated storage manager.
        collection: The collection to use with the manager.
        logger: An optional logger.
    """

    async def _send(client: AsyncClient, payload: SettledPayment):
        try:
            response = await client.post(url=webhook_url, headers=headers, json=payload.model_dump(mode="json"))
            response.raise_for_status()
            await _maybe_await(manager.mark_as_sent(collection, payload.id))
        except:
            logger.exception(f"An exception occurred when processing payment with id={payload.id}")

    api_key = api_key.strip()
    headers = {"X-API-Key": api_key} if api_key else {}
    logger.info("Processing a batch:")
    logger.info("- Retrieving the batch...")
    batch: List[SettledPayment] = await _maybe_await(manager.get_batch(collection, webhook_name, worker_id))
    logger.info(f"- Sending the batch ({len(batch)} elements)...")
    async with AsyncClient(timeout=15) as client:
        await asyncio.gather(*[_send(client, payload) for payload in batch])
    logger.info("- Updating the batch...")
    for element in batch:
        manager.mark_as_sent(collection, element.id)


async def _webhook_worker(
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
            await _send_batch(worker_id, webhook_name, webhook_url, api_key, manager, collection, logger)
            await asyncio.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info(f"Worker loop cancelled by the user")
    except:
        logger.exception("Worker loop stopped because of an error:")


def webhook_worker(
    worker_id: str, webhook_name: str, webhook_url: str, api_key: str,
    storage_manager: StorageManager, collection: str, logger: logging.Logger = None,
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
        storage_manager: The associated storage manager.
        collection: The collection to use with the manager.
        logger: An optional logger.
        sleep_time: A sleep time between iterations.
    """

    asyncio.run(_webhook_worker(worker_id, webhook_name, webhook_url, api_key, storage_manager, collection,
                                logger, sleep_time))
