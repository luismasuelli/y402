from typing import Optional
from ..core.types.errors import ConditionalDependencyError
from ..core.types.payment import SettledPayment
from ..triggers.errors import UnsuccessfulWebhookTriggerError, ExceptionOnWebhookTriggerError


try:
    import requests
except ImportError:
    raise ConditionalDependencyError("Requests library is not installed. Install it as a requirement "
                                     "by invoking requests==2.32.5 or similar")


def send_payment(webhook_url: str, settled_payment: SettledPayment,
                 api_key: Optional[str] = None, timeout: int = 15):
    """
    Sends a settled payment, using the `requests` library.

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
        headers['X-API-Key'] = api_key
    if timeout < 1:
        timeout = 1

    try:
        response = requests.post(webhook_url, headers=headers, json=settled_payment.model_dump(mode="json"),
                                 timeout=timeout)
        response.raise_for_status()
        if response.status_code not in range(200, 300):
            raise UnsuccessfulWebhookTriggerError(response.status_code, response.content, response.headers)
    except Exception as e:
        raise ExceptionOnWebhookTriggerError(e)
