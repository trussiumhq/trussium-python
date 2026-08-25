"""HTTP client for a configured Trussium runtime."""

from collections.abc import Mapping
from typing import Any, Self

import httpx


class APIError(RuntimeError):
    """A bounded non-success response from a Trussium runtime."""

    def __init__(self, status_code: int, code: str | None = None) -> None:
        self.status_code = status_code
        self.code = code
        detail = f": {code}" if code else ""
        super().__init__(f"Trussium runtime returned HTTP {status_code}{detail}")


class TrussiumClient:
    """Synchronous client for an already-running Trussium runtime."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9000",
        *,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client = http_client or httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def complete(
        self, payload: Mapping[str, Any], *, request_id: str | None = None
    ) -> dict[str, Any]:
        """Create one non-streaming chat completion."""
        return self._request("POST", "/v1/chat/completions", payload, request_id)

    def readiness(self) -> dict[str, Any]:
        """Return the runtime readiness response."""
        return self._request("GET", "/health/ready")

    def capabilities(self) -> dict[str, Any]:
        """Return public configured-capability metadata."""
        return self._request("GET", "/v1/capabilities")

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        headers = {"X-Request-ID": request_id} if request_id else None
        try:
            response = self._client.request(method, path, json=payload, headers=headers)
        except httpx.HTTPError as error:
            raise RuntimeError("Trussium runtime request failed.") from error
        if response.is_error:
            code = _error_code(response)
            raise APIError(response.status_code, code)
        response_payload = response.json()
        if not isinstance(response_payload, dict):
            raise TypeError("Trussium runtime returned an invalid response.")
        return response_payload


def _error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), dict):
        return None
    code = payload["error"].get("code")
    return code if isinstance(code, str) else None
