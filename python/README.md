# y402

A Python implementation of the X402 (with extension features called Y402). A description of y402 is given in the main
README.md file in the repository.

## Install

Execute this command:

```shell
pip install y402
```

Also execute at least one of:

```shell
pip install requests==2.32.5
pip install httpx==0.28.1
```

If the intention is to launch a server, execute at least one of these:

```shell
pip install Flask==3.1.2
pip install fastapi==0.121.1
```

For Streamlit browser-wallet support:

```shell
pip install "y402[streamlit]"
```

## Usage (client)

Depending on the installed dependency, one of these can be imported:

```python
# One of these:
from y402.clients.httpx import Y402Client as make_402_client
from y402.clients.httpx_sync import Y402Client as make_402_client
from y402.clients.requests import y402_requests as make_402_client
```

Then, create an account:

```python
from eth_account import Account

account = Account.from_key("0xSomePrivateKey")

client = make_402_client(account)
```

The arguments for `make_402_client` are:

```python
client = make_402_client(
    account, payment_requirements_selector=..., chain_id_by_name=...
)
```

The two arguments are optional.

`chain_id_by_name` is a mapping of strings (being chain names) to int (being 
chain ids). **The keys must be set up carefully**, typically related to other 
implementations of x402 (names are somewhat standard among these libraries, 
even if not necessarily true as per the protocol). If no mapping is specified 
here, it doesn't matter: this package has a decent setup of networks that have 
USDC / EURC installed (e.g. Base, Polygon, ...).

On the other hand, `payment_requirements_selector` tells which payment alternative
is to be considered and, if no callback is set, a callback taking the first
available one being of scheme="exact" will be used by default. It takes a single
argument of type `List[y402.core.types.requirements.PaymentRequirements]` and
returns a single chosen `y402.core.types.requirements.PaymentRequirements`.

After this instantiation, the client is transparently used in the same way
of `httpx.AsyncClient`, `httpx.Client` or `requests` / `requests.Session`,
depending on the chosen implementation and available dependencies, except that
it captures the y402/x402-related responses and performs the appropriate logic
(related to x402 protocol and the y402 extensions described in the main README.md
file in this repository).

## Usage (Streamlit client)

Streamlit cannot complete interactive wallet authorization inside one blocking
HTTP call, so the Streamlit adapter returns a small result object with a
`status` of `success`, `pending` or `error`.

Use `streamlit_browser_web3.wallet_get()` on every rerun and keep using the same
request `key` while the user is approving the signature in the wallet.

```python
import streamlit as st
from streamlit_browser_web3 import wallet_get
from y402.clients.streamlit.requests import Y402Client


wallet = wallet_get()
client = Y402Client(wallet)


if wallet.status != "connected":
    if st.button("Connect wallet"):
        wallet.connect()
else:
    result = client.get(
        "https://example.com/protected-resource",
        key="protected-resource",
    )

    if result.status == "pending":
        st.info("Approve the payment signature in your wallet.")
    elif result.status == "error":
        st.error(result.error)
    else:
        st.write(result.response.json())
```

There is also an equivalent sync `httpx` wrapper:

```python
from y402.clients.streamlit.httpx_sync import Y402Client
```

## Usage (server)

Mounting a server depends on three things:

1. Whether using `Flask` (version 3) or `FastAPI` (modern versions).
2. Which type of storage (by default, `MongoDB`, but users can add their custom
   implementation if they want).
3. Whether using `httpx` (either sync or async mode is supported) or `requests`
   to send Facilitator requests.

The first point, however, is defining an optional setup if more things are
needed. This setup must be analogous between the client and the server (i.e.
in the same way the client defined its `chain_id_by_name`, if used, the setup
must configure the same networks but in its own format - this can be skipped
if it's only expected for the client to use the same y402 client instead of an
arbitrary x402 client for some reason).

Creating a setup looks like this:

```python
from y402.core.types.setup import Y402Setup

setup = Y402Setup()

# Adding a network.

# To add a network among these (whose chain ids are known):
# base, base-sepolia, avalanche, avalanche-fuji, sei, sei-testnet,
# polygon or polygon-amoy.
setup.add_network("some_network_name")
# To add a custom network, not among the previous ones, use this:
# E.g. if the chain id would be 1111111.
setup.add_network("some_network_name", 1111111)

# The same networks must be configured in the client libraries.
# The default names correspond to Coinbase's implementation.

# Adding a token.

# To add a token among these (whose codenames are known):
# usdc, eurc (not all networks have eurc among the default networks)
#
# The chosen network must already be configured.
#
# - base: Has usdc, eurc.
# - base-sepolia: Has usdc, eurc.
# - avalanche: Has usdc, eurc.
# - avalanche-fuji: Has usdc, eurc.
# - sei: Has usdc.
# - sei-testnet: Has usdc.
# - polygon: Has usdc.
# - polygon-amoy: Has usdc.
#
# So use a call like this (for network "base" and token "usdc").
setup.add_token("base", "usdc")
# To add a custom token, not among the previous ones, use this:
# (assuming base network is added)
setup.add_token(
    "base", "my_token",
    "The Token Name",     # The EIP-712 name of the token contract.
    "0xTheTokenAddress",  # The address of the token contract.
    "1",  # The EIP-712 version of the token contract.
    18,   # The return value of .decimals() of the token contract.
    "@",  # The symbol we'll associate for the token. This will
          # be explained later.
    default_for_symbol=True,  # Optional (by default: False). It
                              # sets, on True, the current token
                              # as the one associated to the symbol
                              # with a similar logic to calling the
                              # .set_default_for_symbol_token method.
)

# Registered tokens can be used in endpoints setup, later.

# In order to set an existing and registered token as default for
# its symbol, this method can be called:
setup.set_default_for_symbol_token("base", "my_token")
# It will account for the symbol it was registered with (e.g. @ in
# the previous example), same as specifying default_for_symbol=True.

# Also, a default token can be specified for when the price is not
# a token value or string, but an integer. A token can be used to
# be chosen when an integer value is used as price for a given
# network by calling this method:
setup.set_default_token("base", "my_token")
```

### Using MongoDB storage manager

In order to instantiate a manager to store the payments in a MongoDB database:

```python
from y402.storage.mongodb import StorageManager

storage_manager = StorageManager("mongodb://...", "some_database")
# These are more arguments to this StorageManager: batch_expiration=60, batch_size=50.
# batch_expiration regulates the time a payment is locked (i.e. not picked by another
# worker) after being picked by a worker, before being picked by another worker, if
# not finished processing yet. batch_size regulates the size of the batch to pick.
```

### Using Flask as server

In order to make use of y402 in Flask, have your Flask app and do something like this:

```python
from flask import Flask
from y402.api.flask.decorator import payment_required
from y402.core.types.facilitator import FacilitatorConfig

# Create the app object:
app = Flask(...)

# Create the decorator (centralized instantiation):
require_payment = payment_required(
    # The MIME type to use by default.
    mime_type="application/json",  # Optional; default value.
    # The max. time the client can take to answer this
    # request and provide the payment.
    default_max_deadline_seconds=60,  # Optional; default value.
    # Coinbase Developer Platform paywall configuration.
    paywall_config=None,  # Optional; default value.
    # Custom HTML paywall when using HTML responses.
    # If None, it uses a default paywall renderer.
    custom_paywall_html=None,  # Optional; default value.
    # The config to use for the facilitator client. If not given,
    # the facilitator will use https://x402.org/facilitator, which
    # needs no particular auth. headers. Otherwise, it can make
    # use of fields url="https://..." (a full URL to a POST URL)
    # and optional headers={...a dictionary...}.
    facilitator_config=FacilitatorConfig(),  # Optional; default value.
    # Only httpx_sync / requests is allowed as a library  for Flask.
    client_http_library="httpx_sync",  # Optional; default value.
    # The setup defined in the earlier point. If this setup is None,
    # then the only setup that will be considered is taken from the
    # endpoint being processed. If the endpoint does not define its
    # setup, and empty setup is used.
    setup=setup,  # Optional; default value can safely be None.
    # The storage manager defined in the earlier point.
    # This is MANDATORY.
    storage_manager=storage_manager
)
```

_`storage_manager` is optional - if not specified, standard x402 flow will apply, but
with no external webhook workers or out-of-the-box payments storage and tracking._

The same @require_payment operator can be used multiple times.

In order to use this in a Flask endpoint (this decorator is used endpoint-wise):

```python
from y402.api.flask.types.endpoint_settings import X402EndpointSettings
from y402.core.types.schema import HTTPInputSchema


@app.route(...flask-related setup...)
...
@require_payment
@X402EndpointSettings(
    # The canonical URL to use for to-client documentation
    # in the x402 protocol response message. Optional. If
    # absent, the same request's URL will be used.
    resource_url=None,
    # The path parameter, present in the URL for this endpoint,
    # from which the reference argument will be extracted. It
    # must match an existing path parameter in the URL, or an
    # error / None value will occur. If not specified, then
    # the reference will be None for payments of this endpoint,
    # which might not be a good idea. So it's always better
    # to specify a valid reference_param for this endpoint.
    reference_param=None,
    # The description of the endpoint. Optional.
    description="This endpoint does ...",
    # The time, in seconds, that a client can take to perform
    # the signing of the payment before it needs to start the
    # x402 exchange again.
    max_deadline_seconds=60,
    # An optional schema, of type HTTPInputSchema, to use
    # to hint the clients about the format of the expected
    # input (path params, query params, headers and body).
    # Useful for the agents reading the result and understanding.
    # Not needed if the app is client-only.
    input_schema=None,
    # A description of the output schema (a mapping field =>
    # description). Meant to be used to tell agents what to
    # expect. Only useful for agents. Optional.
    output_schema=None,
    # A different MIME type to use, rather than the one
    # configured in the @require_payment decorator.
    # Optional.
    mime_type=None,
    # A different paywall config instance to use, rather
    # than the one configured in the @require_payment
    # decorator. Optional.
    paywall_config=None,  # Or a paywall config instance.
    # A different HTML endpoint to use, rather than the one
    # configured in the @require_payment decorator. Optional.
    custom_paywall_html=None,  # Or a new HTML content.
    # A custom setup to merge to the existing setup, if present.
    # Optional.
    custom_setup=None,  # Or a Y402Setup instance.
    # Arbitrary custom tags to add to this endpoint's payments.
    # Optional.
    tags=["some", "tags"],
    # The name of the webhook that will receive the payments
    # that were settled in this endpoint. Mandatory.
    webhook_name="some_webhook_name",
    # The collection where the storage manager will maintain
    # payments for this endpoint. Mandatory.
    storage_collection="some_collection",
    # The details of the payment.
    payments_details=...
)
def my_endpoint(...flask-related parameters...):
    # this is regular Flask endpoint code.
    # By this point in code execution, the payment has been processed
    # and queued for notification to the webhook.
    return ...
```

The `payment_details` is **mandatory** and can be:

1. A list of `x402.core.types.requirements.RequirePaymentDetails` objects.
2. A callable taking the current `Request` object and returning, synchronously or via awaitables,
   a list of `x402.core.types.requirements.RequirePaymentDetails` objects.

The `RequirePaymentDetails` accepts:

1. A `scheme`. Typically, `exact`. The only one implemented in this library, so far.
2. A `network` among the registered ones in the setup. It is in practice mandatory that
   either the setup in the centralized decorator or the endpoint decorator define the
   network and tokens to be used here.
3. A `pay_to_address` address that will receive the payment via x402 protocol.
4. A `price` which can be an integer (expressed in the minimal units of whatever token
   is set as per-network default using `.set_default_token` in the setup for the given
   network; otherwise, an error will occur), a string (in this case, the per-network
   per-symbol token will be used for values like $12.34, @12.34 or whatever symbol is
   being used; an error will occur on unknown symbol or mismatch, otherwise the number
   will be multiplied by the decimals factor, rounded to integer, and used as the value
   for the corresponding token) or a direct `y402.core.types.requirements.TokenAmount`
   instance.

In the case of a `TokenAmount` instance, it takes these arguments:

1. `amount` as integer, in terms of its intended minimal units.
2. `asset` as `TokenAsset` (same module / package).

In turn, `TokenAsset` takes these arguments:

1. `address` is the address of the token contract.
2. `decimals` is the amount of decimals it returns on its `.decimals()` method.
3. `eip712` is the mandatory `y402.core.types.eip712.EIP712Domain` instance.

Finally, `EIP712Domain` takes these arguments:

1. `name` is the EIP-712 name of the contract's domain.
2. `version` is the EIP-712 version of the contract's domain.

### Using FastAPI as server

The setup is similar to Flask's but with some remarks:

1. No central decorator here. It's used as a middleware instead.
2. The callable accepted in `payments_details=`, if using a callable, accepts the
   request as a FastAPI's `Request` object.

Creating the middleware is done like this:

```python
from fastapi import FastAPI
from y402.api.fastapi.middleware import payment_required
from y402.core.types.facilitator import FacilitatorConfig

storage_manager = ... # Same as in Flask's.

app = FastAPI(title=...)
app.middleware("http")(
    payment_required(
        # Notice how the arguments are the same as in Flask's.

        # The MIME type to use by default.
        mime_type="application/json",  # Optional; default value.
        # The max. time the client can take to answer this
        # request and provide the payment.
        default_max_deadline_seconds=60,  # Optional; default value.
        # Coinbase Developer Platform paywall configuration.
        paywall_config=None,  # Optional; default value.
        # Custom HTML paywall when using HTML responses.
        # If None, it uses a default paywall renderer.
        custom_paywall_html=None,  # Optional; default value.
        # The config to use for the facilitator client. If not given,
        # the facilitator will use https://x402.org/facilitator, which
        # needs no particular auth. headers. Otherwise, it can make
        # use of fields url="https://..." (a full URL to a POST URL)
        # and optional headers={...a dictionary...}.
        facilitator_config=FacilitatorConfig(),  # Optional; default value.
        # Only httpx is allowed as a library.
        client_http_library="httpx",  # Optional; default value.
        # The setup defined in the earlier point. If this setup is None,
        # then the only setup that will be considered is taken from the
        # endpoint being processed. If the endpoint does not define its
        # setup, and empty setup is used.
        setup=setup,  # Optional; default value can safely be None.
        # The storage manager defined in the earlier point.
        # This is MANDATORY.
        storage_manager=storage_manager
    )
)

# Include the routers here...
app.include_router(...)
```

_`storage_manager` is optional - if not specified, standard x402 flow will apply, but
with no external webhook workers or out-of-the-box payments storage and tracking._

Then, in the routers, ensure to have this structure:

```python
from fastapi import APIRouter, ...
from y402.api.fastapi.types.endpoint_settings import X402EndpointSettings
from y402.core.types.schema import HTTPInputSchema


router = APIRouter()


@X402EndpointSettings(
   # These are the same arguments as Flask's X402EndpointSettings.
   #
   # The only difference is the explained on in payments_details=.
   resource_url="/the/url",  # or /the/url/{reference}
   description="Accepts a payload bla bla bla...",
   # max_deadline_seconds=60,
   input_schema=HTTPInputSchema(
      # query_params={ ... },
      # header_fields={},
      body_type="json",
      body_fields=...
   ),
   output_schema={"foo": "Some foo field", ...},
   mime_type="application/json",
   payments_details=...
)
@router.post("/the/url", ...)
async def endpoint(...):
    # Define it as normal in FastAPI. Return arbitrary values as normal.
    # By this point in code execution, the payment has been processed
    # and queued for notification to the webhook.
    return ...
```

## Usage (endpoint dispatcher)

The endpoint dispatcher is a kind of worker that should run forever.

_Please note: This worker relies on having a non-dummy storage manager,
both in the payment server and in the worker. If there's a mismatch,
or the server uses a dummy storage manager (in particular, when not
specifying a storage manager at all), then this worker will not batch
and send any payment from that server._

This worker performs the following cycle:

1. Takes the settled, but not finished, payments _of certain type_.
   This _type_ will match, actually, the `webhook_name=` argument
   provided to a `@X402EndpointSettings` decorator in your application.
2. Reserves them for itself. Reserving it is a complex detail, but it
   relates to a `worker_id` (an arbitrary string value) given at start
   (execution of a worker).
3. Sends them to a specific endpoint, also configured at start. The
   endpoint is a full URL (http://... or https://...) and, optionally,
   a proper API key (if given, it will fly into the X-Api-Key header;
   this is only mandatory if the endpoint requires an X-Api-Key header
   for authentication).

This, in a loop that runs until stopped.

In order to run a worker, consider the following snippet:

```python
from y402.storage.mongodb import StorageManager

# Pick only one of:
from y402.workers.httpx import webhook_worker
from y402.workers.httpx_sync import webhook_worker
from y402.workers.requests import webhook_worker

webhook_worker(worker_id="my-awesome-worker",
               webhook_name="some_webhook_name",
               webhook_url="http://some-server:8080/some/endpoint",
               api_key="",  # No API key needed == use empty or omit it.
               storage_manager=StorageManager("mongodb://...", "some_database"),
               collection="some_collection",
               logger=some_logger,  # An optional logging.Logger object.
               sleep_time=10)  # Sleep time, expressed in seconds.
```

This, considering some remarks:

1. The `webhook_name` should match a webhook_name used in your application.
   This means that `some_webhook_name` is the name to use for this example,
   since it was used in previous `@X402EndpointSettings` decorators. This
   means that stuff stored by that endpoint (and all the endpoints using
   the same webhook_name) will be attended.
2. The webhook URL is arbitrary and related only to this worker, but must
   be a fully-qualified URL. If that remote endpoint (behind that URL) use
   the X-Api-Key authentication, specify the key in the `api_key=` argument.
3. The `storage_manager=` and `collection=` must match, respectively, the
   `storage_manager=` used at middleware / decorator level and the given
   collection name at `storage_collection=` in the `@X402EndpointSettings`
   decorator definition. Given these settings, only the endpoints with the
   same `webhook_name` and same storage settings will find their payments
   being handled by this worker.
4. The `worker_id` is arbitrary, useful if several workers attend the same
   `webhook_name`.
5. `logger=` is optional (anyway, a default logger is used), and `sleep_time`
   is `5` (seconds) by default if not specified.

With this, the worker will run and process all the logs in those settings.

### Understanding endpoints

There are two endpoint types that matter here:

1. Endpoints intended to receive payments (with the `@X402EndpointSettings`
   decorator).
2. Endpoints intended to receive confirmations of payments.

The first endpoints are configured as described earlier (they must be POST
endpoints, always).

> This repository has some examples in the examples/python/fastapi-stack
  and examples/python/flask-stack on how to configure them.

The second (type of) endpoints are arbitrary endpoints in arbitrary HTTP
servers. They're, still, POST endpoints.

The important parts are:

1. These endpoints are developed by the user, entirely, in the HTTP stack
   they prefer (even if it's not Python).
2. These endpoints, when attending the request, should not fail or veto
   anything here. Failure to return 200 will involve the endpoint to be
   retried later, instead of marking the payment as finished.
3. These endpoints will receive a body like this (this is an example):

```
{
    // The uuid of the payment.
    'id': 'dce92a17-63c5-468e-8d5b-d5fd08b79d63',
    
    // The version of the protocol. So far, only the first
    // version of the protocol is supported.
    'version': 1,

    // The identity / taxonomy of the involved resource.
    // This might be a unique resource or a not unique one.
    'identity': {
        // The original x402 payment endpoint that attended the request.
        'resource': 'http://localhost:9873/api/purchase/bronze',
        
        // The configured tags.
        'tags': ['dynamic', 'anonymous'],
        
        // Optionally, the reference of the payment, it that concept is used.
        'reference': ''
    },
    'details': {
        // The address doing the payment.
        'payer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',

        // The chain into which the address is doing the payment.
        'chain_id': '31337',
        
        // The address of the involved token.
        'token': '0x5fbdb2315678afecb367f032d93f642f64180aa3',
        
        // The amount of the token (expressed as a raw integer value).
        // This value must be taken into account with respect to the
        // decimals (ERC-20's decimals()) of the token.
        'value': '1000000',
        
        // The code the token is registered with.
        'code': 'usdf',
        
        // The display name / EIP-712 name of the token.
        'name': 'USD Fake',
        
        // The label corresponding to the actual price being paid.
        'price_label': '$1'
    },
    
    // The date when this payment was settled.
    'settled_on': '2025-12-24T21:31:54.200000',
    
    // The hash of the transaction when that occurred.
    'transaction_hash': '9105e97f55cd6712a87233c98c274fd6e873c825a9e1463fd03bb164fea48768'
}
```
