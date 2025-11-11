from fastapi import Request


def get_root_url(request: Request) -> str:
    """
    Retrieves the root URL (i.e. no path nor trailing slash).
    :param request: The current request.
    :return: The base proto://host url.
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
