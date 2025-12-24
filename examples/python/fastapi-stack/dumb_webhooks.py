from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("webhook.fastapi")

# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------

app = FastAPI()


async def _log_request(label: str, request: Request) -> None:
    # Headers
    headers: Dict[str, Any] = dict(request.headers)
    # Query params
    query: Dict[str, Any] = {k: request.query_params.getlist(k) for k in request.query_params}

    # Body: try JSON, fallback to raw text
    body: Any
    raw_body = await request.body()
    if not raw_body:
        body = None
    else:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = raw_body.decode("utf-8", errors="replace")

    logger.info(
        "%s request\n  headers=%r\n  query=%r\n  body=%r",
        label,
        headers,
        query,
        body,
    )


@app.post("/api/webhook/payments1")
async def payments1(request: Request):
    await _log_request("payments1", request)
    return JSONResponse({"ok": True})


@app.post("/api/webhook/payments2")
async def payments2(request: Request):
    await _log_request("payments2", request)
    return JSONResponse({"ok": True})


@app.post("/api/webhook/payments3")
async def payments3(request: Request):
    await _log_request("payments3", request)
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("__main__:app", host="0.0.0.0", port=9871)
