import os
import logging


logging.basicConfig()


MONGODB_URL = "mongodb://root:example@localhost:27517/mydb?authSource=admin"
INTERNAL_CLIENT_LIBRARY = os.environ["WORKER_INTERNAL_CLIENT_LIBRARY"]  # Allowed: "httpx", "httpx_sync", "requests"
WEBHOOK_NAME = os.environ["WORKER_WEBHOOK_NAME"]  # Allowed: {dynamic|fixed}_type_{fastapi|flask}.
WEBHOOK_URL = os.environ["WORKER_WEBHOOK_URL"]


if WEBHOOK_URL not in ["/api/webhook/payments1", "/api/webhook/payments2", "/api/webhook/payments3"]:
    raise Exception("Invalid WORKER_WEBHOOK_URL: must be /api/webhook/payments1, /api/webhook/payments2 or "
                    "/api/webhook/payments3")


match INTERNAL_CLIENT_LIBRARY:
    case "httpx":
        from y402.workers.httpx import webhook_worker
    case "httpx_sync":
        from y402.workers.httpx_sync import webhook_worker
    case "requests":
        from y402.workers.requests import webhook_worker
    case _:
        raise Exception("Invalid WORKER_INTERNAL_CLIENT_LIBRARY: must be httpx, httpx_sync or requests")


if WEBHOOK_NAME not in ["dynamic_type_fastapi", "dynamic_type_flask", "fixed_type_fastapi", "fixed_type_flask"]:
    raise Exception("Invalid WORKER_WEBHOOK_NAME: must be {dynamic|fixed}_type_{fastapi|flask}")


if WEBHOOK_NAME in ["dynamic_type_fastapi", "dynamic_type_flask"]:
    SOURCE_COLLECTION = "dynamic_type"
else:
    SOURCE_COLLECTION = "fixed_type"


if WEBHOOK_NAME in ["dynamic_type_fastapi", "fixed_type_fastapi"]:
    FINAL_URL = f"http://localhost:9871/{WEBHOOK_URL.lstrip('/')}"
else:
    FINAL_URL = f"http://localhost:9872/{WEBHOOK_URL.lstrip('/')}"


from y402.storage.mongodb import StorageManager
from y402.workers.httpx import webhook_worker


webhook_worker(worker_id="my-awesome-worker",
               webhook_name=WEBHOOK_NAME,  # For this example: {dynamic|fixed}_type_{fastapi|flask}.
               webhook_url=FINAL_URL,  # A URL for this webhook.
               api_key="",  # No API key needed in this example.
               storage_manager=StorageManager(url=MONGODB_URL, database="payments"),
               collection=SOURCE_COLLECTION)  # For this example: fixed_type, dynamic_type
