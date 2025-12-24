import asyncio
import inspect
import os
import random
from eth_account import Account


# PK for address: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (1st anvil account)
PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
INTERNAL_CLIENT_LIBRARY = os.environ["FRONTEND_INTERNAL_CLIENT_LIBRARY"]  # Allowed: "httpx", "httpx_sync", "requests"
SERVER_TYPE = os.environ["FRONTEND_SERVER_TYPE"]  # Allowed: "flask", "fastapi". They listen in different ports.


match INTERNAL_CLIENT_LIBRARY:
    case "httpx":
        from y402.clients.httpx import Y402Client as make_client
    case "httpx_sync":
        from y402.clients.httpx_sync import Y402Client as make_client
    case "requests":
        from y402.clients.requests import y402_requests as make_client
    case _:
        raise Exception("Invalid WORKER_INTERNAL_CLIENT_LIBRARY: must be httpx, httpx_sync or requests")


match SERVER_TYPE:
    case "flask":
        base_url = "http://localhost:9875"
    case "fastapi":
        base_url = "http://localhost:9873"
    case _:
        raise Exception("Invalid FRONTEND_SERVER_TYPE: must be flask or fastapi (only needed for knowing port)")


if __name__ == "__main__":
    client = make_client(Account.from_key(PRIVATE_KEY))
    type_ = random.choice(["gold", "silver", "bronze"])
    reference = ''.join(random.choice("1234567890abcdef") for _ in range(10))
    url = base_url + random.choice(["/api/purchase/<type>",
                                    "/api/purchase2/<type>/<reference>",
                                    "/api/purchase3/fixed",
                                    "/api/purchase4/fixed/<reference>"]).replace(
        "<type>", type_
    ).replace(
        '<reference>', reference
    )
    print("Triggering URL: " + url)
    result = client.post(url)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print("POST result:")
    print(">>> Headers:", result.headers)
    try:
        print(">>> JSON:", result.json())
    except:
        print(">>> Content:", result.content)