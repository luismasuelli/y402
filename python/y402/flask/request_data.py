from flask import request, current_app


def get_root_url() -> str:
    """
    Retrieves the root URL (i.e. no path nor trailing slash).

    Returns:
        The base proto://host url.
    """

    # This uses forwarded headers if present (e.g. behind reverse proxy).
    scheme = request.headers.get("x-forwarded-proto", request.scheme)

    # X-Forwarded-Host (and Proxy-Protocol) have precedence.
    host_header = request.headers.get("x-forwarded-host")
    if host_header:
        host = host_header
    else:
        # Fallback to the original host.
        host = request.headers.get("host") or request.host

    # Construct root URL without path/query.
    return f"{scheme}://{host}"


def resolve_endpoint():
    """
    Obtains the endpoint (function) being responsible for
    the handing of the current request.

    Returns:
        The endpoint handling it.
    """

    # `request.endpoint` gives the endpoint name (usually the function name)
    endpoint_name = request.endpoint
    if endpoint_name is None:
        return None

    # `current_app.view_functions` maps endpoint names to the actual callables
    return current_app.view_functions.get(endpoint_name)
