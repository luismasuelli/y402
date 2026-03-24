import json
import secrets
from typing import Any
from urllib import request as urllib_request
import streamlit as st
from streamlit_browser_web3 import wallet_get
from y402.clients.common import PaymentError
from y402.clients.streamlit import (
    StreamlitWalletNotConnectedError,
)


CHAIN_ID = 31337
CHAIN_ID_HEX = hex(CHAIN_ID)
CHAIN_NAME = "Anvil Local"
CHAIN_ID_BY_NAME = {"local": CHAIN_ID}
RPC_URL = "http://127.0.0.1:8545"
ACTIVE_REQUEST_STATE_KEY = "front_end:streamlit:active_request"
LAST_RESULT_STATE_KEY = "front_end:streamlit:last_result"
REQUEST_FLOW_KEY = "front-end:purchase"
SWITCH_CHAIN_REQUEST_KEY = "front-end:wallet:switch-chain"
ADD_CHAIN_REQUEST_KEY = "front-end:wallet:add-chain"

SERVER_BASE_URLS = {
    "fastapi": "http://localhost:9873",
    "flask": "http://localhost:9875",
}

ENDPOINT_OPTIONS = {
    "Dynamic price": "/api/purchase/{type}",
    "Dynamic price + reference": "/api/purchase2/{type}/{reference}",
    "Fixed price": "/api/purchase3/fixed",
    "Fixed price + reference": "/api/purchase4/fixed/{reference}",
}


def _default_reference() -> str:
    return secrets.token_hex(5)


def _build_url(
    *,
    server_type: str,
    endpoint_kind: str,
    purchase_type: str,
    reference: str,
) -> str:
    path = ENDPOINT_OPTIONS[endpoint_kind]
    path = path.replace("{type}", purchase_type).replace("{reference}", reference)
    return f"{SERVER_BASE_URLS[server_type]}{path}"


def _parse_json_payload(raw_value: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON body: {exc}"

    if not isinstance(payload, dict):
        return None, "The JSON body must decode to an object."

    return payload, None


def _latest_block_timestamp() -> tuple[int | None, str | None]:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": ["latest", False],
            "id": 1,
        }
    ).encode("utf-8")
    req = urllib_request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return None, str(exc)

    result = body.get("result")
    if not isinstance(result, dict):
        return None, "Invalid eth_getBlockByNumber response."

    raw_timestamp = result.get("timestamp")
    if not isinstance(raw_timestamp, str):
        return None, "Missing block timestamp in RPC response."

    try:
        return int(raw_timestamp, 16), None
    except ValueError:
        return None, f"Invalid block timestamp: {raw_timestamp}"


def _make_client(client_library: str, wallet, selected_account: str):
    kwargs = {
        "wallet": wallet,
        "chain_id_by_name": CHAIN_ID_BY_NAME,
        "account_selector": lambda _wallet: selected_account,
    }
    if client_library == "httpx":
        from y402.clients.streamlit.httpx_sync import Y402Client as Y402HttpxSyncClient
        return Y402HttpxSyncClient(**kwargs)
    if client_library == "requests":
        from y402.clients.streamlit.requests import Y402Client as Y402RequestsClient
        return Y402RequestsClient(**kwargs)
    raise ValueError(f"Unsupported client library: {client_library}")


def _store_last_result(*, status: str, title: str, detail: Any) -> None:
    st.session_state[LAST_RESULT_STATE_KEY] = {
        "status": status,
        "title": title,
        "detail": detail,
    }


def _render_last_result() -> None:
    result = st.session_state.get(LAST_RESULT_STATE_KEY)
    if not result:
        return

    status = result["status"]
    title = result["title"]
    detail = result["detail"]
    renderer = {
        "success": st.success,
        "error": st.error,
        "warning": st.warning,
        "info": st.info,
    }.get(status, st.info)
    renderer(title)
    st.json(detail, expanded=False)


def _handle_wallet_chain_actions(wallet) -> None:
    if not wallet.available:
        return

    if wallet.chain_id == CHAIN_ID:
        st.success(f"Connected to chain {CHAIN_ID}")
        return

    st.warning(f"Wallet chain must be {CHAIN_ID} for this app.")
    switch_status, switch_result = ("idle", None)
    add_status, add_result = ("idle", None)

    switch_clicked = st.button(
        f"Switch to {CHAIN_ID}",
        key="switch-chain-button",
        disabled=wallet.busy,
        use_container_width=True,
    )
    if switch_clicked:
        switch_status, switch_result = wallet.request(
            "wallet_switchEthereumChain",
            [{"chainId": CHAIN_ID_HEX}],
            key=SWITCH_CHAIN_REQUEST_KEY,
        )
    else:
        existing = wallet.get_request_status(SWITCH_CHAIN_REQUEST_KEY)
        if existing:
            switch_status, switch_result = existing

    add_clicked = st.button(
        "Add Anvil chain",
        key="add-chain-button",
        disabled=wallet.busy,
        use_container_width=True,
    )
    if add_clicked:
        add_status, add_result = wallet.request(
            "wallet_addEthereumChain",
            [
                {
                    "chainId": CHAIN_ID_HEX,
                    "chainName": CHAIN_NAME,
                    "nativeCurrency": {
                        "name": "Ethereum",
                        "symbol": "ETH",
                        "decimals": 18,
                    },
                    "rpcUrls": ["http://127.0.0.1:8545"],
                }
            ],
            key=ADD_CHAIN_REQUEST_KEY,
        )
    else:
        existing = wallet.get_request_status(ADD_CHAIN_REQUEST_KEY)
        if existing:
            add_status, add_result = existing

    for label, status, result in (
        ("Switch chain", switch_status, switch_result),
        ("Add chain", add_status, add_result),
    ):
        if status == "pending":
            st.info(f"{label} request pending in the wallet.")
        elif status == "error":
            st.error(f"{label} failed: {result}")
        elif status == "success":
            st.success(f"{label} completed.")


def _execute_active_request(wallet) -> None:
    active_request = st.session_state.get(ACTIVE_REQUEST_STATE_KEY)
    if not active_request:
        return

    selected_account = active_request["selected_account"]
    current_timestamp, timestamp_error = _latest_block_timestamp()
    if current_timestamp is not None:
        st.info(f"Sending transaction (current timestamp is: {current_timestamp}).")
    else:
        st.info(f"Sending transaction (current timestamp unavailable: {timestamp_error}).")

    try:
        client = _make_client(
            active_request["client_library"],
            wallet,
            selected_account,
        )
        try:
            result = client.post(
                active_request["url"],
                key=REQUEST_FLOW_KEY,
                json=active_request["json_payload"],
            )
        finally:
            client.close()
    except (PaymentError, StreamlitWalletNotConnectedError) as exc:
        st.session_state.pop(ACTIVE_REQUEST_STATE_KEY, None)
        _store_last_result(status="error", title="Payment request failed.", detail={"error": str(exc)})
        return
    except Exception as exc:
        st.session_state.pop(ACTIVE_REQUEST_STATE_KEY, None)
        _store_last_result(status="error", title="Unexpected request failure.", detail={"error": str(exc)})
        return

    if result.status == "pending":
        st.info("Payment authorization is pending in the wallet. Complete it and the app will resume.")
        if result.payment_requirements is not None:
            st.json(result.payment_requirements.model_dump(mode="json"), expanded=False)
        return

    st.session_state.pop(ACTIVE_REQUEST_STATE_KEY, None)

    if result.status == "error":
        _store_last_result(
            status="error",
            title="Paid request failed.",
            detail={
                "error": result.error,
                "payment_requirements": (
                    result.payment_requirements.model_dump(mode="json")
                    if result.payment_requirements is not None
                    else None
                ),
            },
        )
        return

    response = result.response
    response_payload: Any
    try:
        response_payload = response.json()
    except Exception:
        response_payload = response.text

    _store_last_result(
        status="success",
        title="Paid request completed.",
        detail={
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_payload,
        },
    )


def main() -> None:
    st.set_page_config(page_title="y402 Streamlit Front-End", layout="wide")
    st.title("y402 Streamlit front-end")
    st.caption("Wallet-backed x402 purchase flow using Streamlit and streamlit-browser-web3.")

    wallet = wallet_get()
    active_request = st.session_state.get(ACTIVE_REQUEST_STATE_KEY)
    selected_account_locked = bool(active_request)

    with st.sidebar:
        st.header("Wallet")
        st.write(f"Required chain: `{CHAIN_ID}`")

        if not wallet.available:
            st.error("No injected wallet was detected in this browser.")
        elif not wallet.connected:
            st.warning("Connect a browser wallet to continue.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Connect", use_container_width=True, disabled=wallet.busy):
                wallet.connect()
        with col2:
            if st.button("Disconnect", use_container_width=True, disabled=wallet.busy):
                wallet.disconnect()

        if wallet.last_error:
            st.error(wallet.last_error)

        st.write(f"Status: `{wallet.status}`")
        st.write(f"Current chain: `{wallet.chain_id}`")

        _handle_wallet_chain_actions(wallet)

        accounts = wallet.accounts or []
        default_index = 0
        if active_request and active_request["selected_account"] in accounts:
            default_index = accounts.index(active_request["selected_account"])

        selected_account = st.selectbox(
            "Account",
            options=accounts,
            index=default_index if accounts else None,
            disabled=selected_account_locked or not accounts,
            placeholder="Connect wallet first",
        )

        st.divider()
        st.header("Request config")
        client_library = st.radio(
            "Client library",
            options=["httpx", "requests"],
            index=0 if not active_request else ["httpx", "requests"].index(active_request["client_library"]),
            disabled=selected_account_locked,
            help="`httpx` uses the sync Streamlit adapter here.",
        )
        server_type = st.radio(
            "Server type",
            options=["fastapi", "flask"],
            index=0 if not active_request else ["fastapi", "flask"].index(active_request["server_type"]),
            disabled=selected_account_locked,
        )

    endpoint_kind = st.radio(
        "Endpoint",
        options=list(ENDPOINT_OPTIONS.keys()),
        horizontal=True,
        disabled=selected_account_locked,
    )

    form_cols = st.columns(2)
    with form_cols[0]:
        purchase_type = st.radio(
            "Purchase type",
            options=["gold", "silver", "bronze"],
            horizontal=True,
            disabled=selected_account_locked or "Dynamic" not in endpoint_kind,
        )
    with form_cols[1]:
        reference = st.text_input(
            "Reference",
            value=active_request["reference"] if active_request else _default_reference(),
            disabled=selected_account_locked or "reference" not in endpoint_kind.lower(),
        )

    body_raw = st.text_area(
        "POST JSON body",
        value=json.dumps(active_request["json_payload"], indent=2) if active_request else "{}",
        height=180,
        disabled=selected_account_locked,
    )

    preview_url = _build_url(
        server_type=active_request["server_type"] if active_request else server_type,
        endpoint_kind=active_request["endpoint_kind"] if active_request else endpoint_kind,
        purchase_type=active_request["purchase_type"] if active_request else purchase_type,
        reference=active_request["reference"] if active_request else reference,
    )
    st.code(preview_url, language="text")

    action_cols = st.columns(2)
    with action_cols[0]:
        submit_clicked = st.button(
            "Submit paid POST request",
            type="primary",
            use_container_width=True,
            disabled=selected_account_locked,
        )
    with action_cols[1]:
        cancel_clicked = st.button(
            "Cancel active flow",
            use_container_width=True,
            disabled=not active_request,
        )

    if cancel_clicked:
        st.session_state.pop(ACTIVE_REQUEST_STATE_KEY, None)
        _store_last_result(
            status="warning",
            title="Active payment flow cancelled.",
            detail={"request_key": REQUEST_FLOW_KEY},
        )

    if submit_clicked:
        if not wallet.available or not wallet.connected:
            _store_last_result(
                status="error",
                title="Wallet connection required.",
                detail={"error": "Connect a browser wallet before submitting a paid request."},
            )
        elif wallet.chain_id != CHAIN_ID:
            _store_last_result(
                status="error",
                title="Wrong wallet chain.",
                detail={"error": f"Switch the wallet to chain id {CHAIN_ID} before submitting."},
            )
        elif not selected_account:
            _store_last_result(
                status="error",
                title="No wallet account selected.",
                detail={"error": "Pick an account from the sidebar."},
            )
        else:
            json_payload, json_error = _parse_json_payload(body_raw)
            if json_error:
                _store_last_result(
                    status="error",
                    title="Invalid request body.",
                    detail={"error": json_error},
                )
            else:
                final_reference = reference or _default_reference()
                st.session_state[ACTIVE_REQUEST_STATE_KEY] = {
                    "client_library": client_library,
                    "server_type": server_type,
                    "endpoint_kind": endpoint_kind,
                    "purchase_type": purchase_type,
                    "reference": final_reference,
                    "selected_account": selected_account,
                    "json_payload": json_payload,
                    "url": _build_url(
                        server_type=server_type,
                        endpoint_kind=endpoint_kind,
                        purchase_type=purchase_type,
                        reference=final_reference,
                    ),
                }
                st.session_state.pop(LAST_RESULT_STATE_KEY, None)

    _execute_active_request(wallet)
    _render_last_result()


if __name__ == "__main__":
    main()
