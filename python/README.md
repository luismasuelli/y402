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