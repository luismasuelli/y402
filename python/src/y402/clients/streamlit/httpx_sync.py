from __future__ import annotations
from typing import Any, Dict, Optional
from ...core.types.errors import ConditionalDependencyError


try:
    import httpx
except ImportError as exc:
    raise ConditionalDependencyError(
        "httpx sync support requires httpx==0.28.1 or a compatible version."
    ) from exc


from .common import (
    StreamlitRequestResult,
    StreamlitY402Client as BaseStreamlitY402Client,
    make_request_fingerprint,
)


class Y402Client:
    """
    Streamlit-friendly sync httpx client for y402-protected endpoints.
    """

    def __init__(
        self,
        wallet,
        payment_requirements_selector=None,
        chain_id_by_name: Optional[Dict[str, int]] = None,
        client: Optional[httpx.Client] = None,
        **kwargs: Any,
    ):
        self.client = client or httpx.Client(**kwargs)
        self.payment_client = BaseStreamlitY402Client(
            wallet,
            payment_requirements_selector=payment_requirements_selector,
            chain_id_by_name=chain_id_by_name,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        key: str,
        **kwargs: Any,
    ) -> StreamlitRequestResult[httpx.Response]:
        fingerprint = make_request_fingerprint(
            method,
            url,
            params=kwargs.get("params"),
            headers=kwargs.get("headers"),
            content=kwargs.get("content"),
            data=kwargs.get("data"),
            json_data=kwargs.get("json"),
        )

        existing_flow = self.payment_client.resume_payment_flow(
            key=key,
            request_fingerprint=fingerprint,
        )
        if existing_flow is None:
            response = self.client.request(method, url, **kwargs)
            if response.status_code != 402:
                self.payment_client.clear_flow(key)
                return StreamlitRequestResult(status="success", response=response)

            flow_result = self.payment_client.process_402_response(
                key=key,
                request_fingerprint=fingerprint,
                response_body=response.json(),
                x_payment_networks=response.headers.get("X-Payment-Networks"),
            )
        else:
            flow_result = existing_flow

        if flow_result.status != "success":
            return StreamlitRequestResult(
                status=flow_result.status,
                error=flow_result.error,
                payment_requirements=flow_result.payment_requirements,
            )

        retry_headers = dict(kwargs.get("headers") or {})
        retry_headers["X-Payment"] = flow_result.payment_header
        retry_headers["X-Payment-Asset"] = flow_result.payment_requirements.asset
        retry_headers["Access-Control-Expose-Headers"] = (
            "X-Payment-Response, X-Payment-Networks"
        )
        retry_kwargs = dict(kwargs)
        retry_kwargs["headers"] = retry_headers
        retry_response = self.client.request(method, url, **retry_kwargs)
        if retry_response.status_code == 402:
            self.payment_client.clear_flow(key)
            return StreamlitRequestResult(
                status="error",
                error="The wallet authorization did not satisfy the payment challenge. Start again.",
                payment_requirements=flow_result.payment_requirements,
            )

        self.payment_client.clear_flow(key)
        return StreamlitRequestResult(status="success", response=retry_response)

    def get(self, url: str, *, key: str, **kwargs: Any) -> StreamlitRequestResult[httpx.Response]:
        return self.request("GET", url, key=key, **kwargs)

    def post(self, url: str, *, key: str, **kwargs: Any) -> StreamlitRequestResult[httpx.Response]:
        return self.request("POST", url, key=key, **kwargs)

    def put(self, url: str, *, key: str, **kwargs: Any) -> StreamlitRequestResult[httpx.Response]:
        return self.request("PUT", url, key=key, **kwargs)

    def patch(self, url: str, *, key: str, **kwargs: Any) -> StreamlitRequestResult[httpx.Response]:
        return self.request("PATCH", url, key=key, **kwargs)

    def delete(self, url: str, *, key: str, **kwargs: Any) -> StreamlitRequestResult[httpx.Response]:
        return self.request("DELETE", url, key=key, **kwargs)

    def close(self) -> None:
        self.client.close()
