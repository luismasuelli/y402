from flask import request


def get_root_url() -> str:
    """
    Retrieves the root URL (i.e. no path nor trailing slash).
    :return: The base proto://host url.
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
