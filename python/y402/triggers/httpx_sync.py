from typing import Optional
from y402.core.types.errors import ConditionalDependencyError
from y402.core.types.payment import SettledPayment
from y402.triggers.errors import UnsuccessfulWebhookTrigger, ExceptionOnWebhookTrigger


try:
    import httpx
except ImportError:
    raise ConditionalDependencyError("httpx library is not installed. Install it as a requirement "
                                     "by invoking httpx==0.28.1 or similar")


def send_payment(webhook_url: str, settled_payment: SettledPayment,
                 api_key: Optional[str] = None, timeout: int = 15):
    """
    Sends a settled payment, using the `httpx` library.

    Args:
        webhook_url: The URL to send (POST) the payment to.
        settled_payment: The already-settled payment to send.
        api_key: The API key to use (Bearer).
        timeout: The allowed request timeout.
    """

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    if timeout < 1:
        timeout = 1

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(webhook_url, headers=headers, json=settled_payment.model_dump(mode="json"),
                                   timeout=timeout)
            if response.status_code not in range(200, 300):
                raise UnsuccessfulWebhookTrigger(response.status_code, response.content, response.headers)
    except Exception as e:
        raise ExceptionOnWebhookTrigger(e)
