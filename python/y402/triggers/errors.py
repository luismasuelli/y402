from y402.core.types.errors import BaseError


class UnsuccessfulWebhookTrigger(BaseError):
    """
    Triggered when the response code is not between 200 and 299
    (both ends included) when hitting an endpoint. Redirects are
    resolved accordingly.
    """


class ExceptionOnWebhookTrigger(BaseError):
    """
    Triggered when there's a connection error when hitting the
    webhook trigger endpoint.
    """
