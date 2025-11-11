from typing import Dict, Any


def is_browser_request(headers: Dict[str, Any]) -> bool:
    """
    Determine if request is from a browser vs API client.

    Args:
        headers: Dictionary of request headers (case-insensitive keys)

    Returns:
        True if request appears to be from a browser, False otherwise
    """
    headers_lower = {k.lower(): v for k, v in headers.items()}
    accept_header = headers_lower.get("accept", "")
    user_agent = headers_lower.get("user-agent", "")

    if "text/html" in accept_header and "Mozilla" in user_agent:
        return True

    return False
