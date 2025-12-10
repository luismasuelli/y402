import os
from typing import Literal, cast
from flask import Flask, jsonify, Request
from y402.api.flask.decorator import payment_required
from y402.core.types.facilitator import FacilitatorConfig
from y402.core.types.requirements import RequirePaymentDetails
from y402.core.types.setup import Y402Setup
from y402.core.types.schema import HTTPInputSchema
from y402.storage.mongodb import StorageManager as MongoDBStorageManager
from y402.api.flask.types.endpoint_settings import X402EndpointSettings


MONGODB_URL = "mongodb://root:example@localhost:27517/mydb?authSource=admin"
# Address for PK: 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a (2nd anvil account)
PAY_TO_ADDRESS = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
INTERNAL_CLIENT_LIBRARY: Literal["httpx_sync", "requests"] = cast(Literal["httpx_sync", "requests"],
                                                                  os.environ["SERVER_INTERNAL_CLIENT_LIBRARY"])
TOKEN_ADDRESS = os.environ["SERVER_TOKEN_ADDRESS"]
FACILITATOR_URL = "http://localhost:9876"


setup = Y402Setup()
setup.add_network("local")
setup.add_token(
    "local", "usdf", "USD Fake", TOKEN_ADDRESS,
    "1", 6, "$", True
)


app = Flask(__name__)
decorator = payment_required(
    mime_type="application/json",
    default_max_deadline_seconds=60,
    facilitator_config=FacilitatorConfig(url=FACILITATOR_URL),
    setup=setup,
    client_http_library=INTERNAL_CLIENT_LIBRARY,
    storage_manager=MongoDBStorageManager(url=MONGODB_URL, database="payments")
)


def payment_details_per_type(request: Request):
    """
    Processes payment details per type. Types can be: "bronze", "silver", "gold"
    :param request: The request.
    :return: The price, as a string.
    """

    type_ = request.view_args.get("type", "").lower()
    match type_:
        case "bronze":
            price = "$1"
        case "silver":
            price = "$3"
        case "gold":
            price = "$5"
        case _:
            raise ValueError(f"Invalid type: {type_}")

    return [RequirePaymentDetails(scheme="exact", network="local", price=price,
                                  pay_to_address=PAY_TO_ADDRESS)]


@app.post("/api/purchase/<type>")
@decorator
@X402EndpointSettings(
    # resource="/api/purchase/...", only useful for static ones.
    payments_details=payment_details_per_type,
    description="Accepts payments of certain type: gold, silver, bronze",
    max_deadline_seconds=60,  # Optional
    input_schema=HTTPInputSchema(body_type="json"),
    output_schema={"ok": "boolean"},
    mime_type="application/json",  # Optional
    tags=["dynamic", "anonymous"],
    webhook_name="dynamic_type_flask",
    storage_collection="dynamic_type"
)
def purchase(type):
    return jsonify(ok=True)


@app.post("/api/purchase2/<type>/<reference>")
@decorator
@X402EndpointSettings(
    # resource="/api/purchase/...", only useful for static ones.
    payments_details=payment_details_per_type,
    description="Accepts payments of certain type: gold, silver, bronze (tracks reference)",
    max_deadline_seconds=60,  # Optional
    input_schema=HTTPInputSchema(body_type="json"),
    output_schema={"ok": "boolean"},
    mime_type="application/json",  # Optional
    tags=["dynamic", "reference"],
    webhook_name="dynamic_type_flask",
    storage_collection="dynamic_type"
)
def purchase2(type, reference):
    return jsonify(ok=True)


@app.post("/api/purchase3/fixed")
@decorator
@X402EndpointSettings(
    # resource="/api/purchase3/fixed", only useful for static ones.
    payments_details=[RequirePaymentDetails(scheme="exact", network="local", price="$2.5",
                                            pay_to_address=PAY_TO_ADDRESS)],
    description="Accepts payments of fixed type",
    max_deadline_seconds=60,  # Optional
    input_schema=HTTPInputSchema(body_type="json"),
    output_schema={"ok": "boolean"},
    mime_type="application/json",  # Optional
    tags=["fixed", "anonymous"],
    webhook_name="fixed_type_flask",
    storage_collection="fixed_type"
)
def purchase3():
    return jsonify(ok=True)


@app.post("/api/purchase4/fixed/<reference>")
@decorator
@X402EndpointSettings(
    # resource="/api/purchase4/fixed/...", only useful for static ones.
    payments_details=[RequirePaymentDetails(scheme="exact", network="local", price="$2.5",
                                            pay_to_address=PAY_TO_ADDRESS)],
    description="Accepts payments of fixed type (tracks reference)",
    max_deadline_seconds=60,  # Optional
    input_schema=HTTPInputSchema(body_type="json"),
    output_schema={"ok": "boolean"},
    mime_type="application/json",  # Optional
    tags=["fixed", "reference"],
    webhook_name="fixed_type_flask",
    storage_collection="fixed_type"
)
def purchase4(reference):
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(port=9875, debug=True)
