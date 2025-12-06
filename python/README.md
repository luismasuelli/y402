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
    "The Token Name",  # The EIP-712 name of the token contract.
    "0xTheTokenAddress",  # The address of the token contract.
    1,  # The EIP-712 version of the token contract.
    18,  # The return value of .decimals() of the token contract.
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
```

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

### Understanding endpoints
