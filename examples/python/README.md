# Python-side examples

This document describes the examples in the Python side on how to use this library.

First, launch a MongoDB database: `docker compose -f docker-compose.mongodb.yml up`.
This, since a database will be used to track the payments.

## Launching server-side services

In order to launch the server-side services, three things must be done:

1. Choose whether `fastapi-stack/` or `flask-stack/` will be tested. Ideally,
   testing this should be done for each package (i.e. these steps for flask,
   and the same/similar steps for fastapi).
2. `pip install -e ../../../python/` to install the dev-mode package.
3. `pip install -r requirements.txt` to install all the other dependencies.
4. `python3 dumb_webhooks.py` to have the webhooks ready (FastAPI one uses port 9871, Flask one uses 9872).
5. `python3 fake_facilitatoy.py` to have a very dumb, non-production-ready, facilitator
   (FastAPI one uses 9874, Flask one uses 9876).
6. `python3 payment_api.py` to have the main x402-enabled example payment API
   (FastAPI one uses 9873, Flask one uses 9875).

_For simplicity, ports and urls are hard-coded. So always use the services from the same directory, unless
 you want to temporarily change the ports by hand._

Configuration will be explained later.

## Launching the workers

In order to forward the payments properly, workers are needed. A simple example
can be run with the following command, but in the sibling `workers/` directory:

```shell
python3 worker.py
```

Configuration will be explained later.

## Configuration for the processes

Most of the values are hard-coded here, for ease of testing. Others are
still configurable (e.g. private keys and so).

1. The `dumb_webhooks.py` does not need any configuration.
   - It accepts endpoints: `/api/webhook/payments1` to `/api/webhook/payments3`. These endpoints
     will be used later.
2. The `fake_facilitator.py` needs some configuration:
   - `FACILITATOR_TOKEN_ADDRESS`: The address of the local contract serving as ERC-20/ERC-3009 payment token.
3. The `payment_api.py` needs some configuration:
   - `SERVER_PAY_TO_ADDRESS`: An address that will receive the payments.
   - `SERVER_INTERNAL_CLIENT_LIBRARY`: Which library to use: `httpx`, `httpx_sync` or `requests`.
     This one is used to interact with the facilitator. The Flask one does not support `httpx`.
   - `SERVER_TOKEN_ADDRESS`: Same as `FACILITATOR_TOKEN_ADDRESS` for the token.
4. The worker needs some configuration:
   - `WORKER_INTERNAL_CLIENT_LIBRARY`: Which library to use: `httpx`, `httpx_sync` or `requests`.
   - `WORKER_WEBHOOK_NAME`: For this example: `fixed_type_flask`, `fixed_type_fastapi`, `dynamic_type_flask` or
     `dynamic_type_fastapi` (two of them are intended to use with flask, and the other ones with fastapi; this
     is only related on how the example servers were coded - not a limitation of the library). Several workers
     might (should) be launched.
   - `WORKER_WEBHOOK_URL`: For this example, choose `/api/webhook/payments1` to `/api/webhook/payments3`.