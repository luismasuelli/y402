from fastapi import Request
from starlette.routing import Match


def get_root_url(request: Request) -> str:
    """
    Retrieves the root URL (i.e. no path nor trailing slash).

    Args:
        request: The current request.

    Returns:
        The base proto://host url.
    """

    # This uses forwarded headers if present (e.g. behind reverse proxy).
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

    # X-Forwarded-Host (and Proxy-Protocol) have precedence.
    host_header = request.headers.get("x-forwarded-host")
    if host_header:
        host = host_header
    else:
        # Fallback to the original host.
        host = request.headers.get("host") or request.url.netloc

    # Construct root URL without path/query.
    return f"{scheme}://{host}"


def resolve_endpoint(request: Request):
    """
    Obtains the endpoint (function) being responsible for
    the handing of the current request.

    Args:
        request: The request to analyze.

    Returns:
        The endpoint handling it.
    """

    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "endpoint", None)
    return None
