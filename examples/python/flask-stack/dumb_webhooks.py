from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("webhook.flask")

# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------

app = Flask(__name__)


def _log_request(label: str) -> None:
    # Headers as a plain dict
    headers: Dict[str, Any] = dict(request.headers)
    # Query args as dict (multi-values preserved as lists)
    query: Dict[str, Any] = request.args.to_dict(flat=False)

    # Body: try JSON first, fallback to raw text
    body: Any
    if request.is_json:
        body = request.get_json(silent=True)
    else:
        body = request.get_data(as_text=True)

    logger.info(
        "%s request\n  headers=%r\n  query=%r\n  body=%r",
        label,
        headers,
        query,
        body,
    )


@app.post("/api/webhook/payments1")
def payments1():
    _log_request("payments1")
    return jsonify(ok=True)


@app.post("/api/webhook/payments2")
def payments2():
    _log_request("payments2")
    return jsonify(ok=True)


@app.post("/api/webhook/payments3")
def payments3():
    _log_request("payments3")
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9872, debug=True)
