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
must configure the same networks but in its own format).

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
