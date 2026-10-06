"""HTTP client for a configured Trussium runtime."""

from collections.abc import Mapping
from typing import Any, Self, cast

import httpx

from trussium_sdk.workflows import WorkflowRequest, WorkflowResult


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

    def embeddings(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create embeddings through the configured runtime."""
        return self._request("POST", "/v1/embeddings", payload)

    def moderations(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Classify input with the moderation capability."""
        return self._request("POST", "/v1/moderations", payload)

    def generate_image(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create an image-generation request."""
        return self._request("POST", "/v1/images/generations", payload)

    def rerank(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Rerank documents through the configured runtime."""
        return self._request("POST", "/v1/rerankings", payload)

    def translate(
        self, payload: Mapping[str, Any], *, request_id: str | None = None
    ) -> dict[str, Any]:
        """Translate text through the configured runtime."""
        return self._request("POST", "/v1/translations", payload, request_id)

    def create_batch(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a provider-owned batch job."""
        return self._request("POST", "/v1/batches", payload)

    def get_batch(self, batch_id: str) -> dict[str, Any]:
        """Read provider-owned batch-job metadata."""
        return self._request("GET", f"/v1/batches/{batch_id}")

    def cancel_batch(self, batch_id: str) -> dict[str, Any]:
        """Request cancellation for a provider-owned batch job."""
        return self._request("POST", f"/v1/batches/{batch_id}/cancel")

    def create_video(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a video job and return metadata only."""
        return self._request("POST", "/v1/videos", payload)

    def get_video(self, video_id: str) -> dict[str, Any]:
        """Read video-job metadata."""
        return self._request("GET", f"/v1/videos/{video_id}")

    def execute_tool(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Invoke one application-declared allowlisted runtime tool."""
        return self._request("POST", "/v1/tools/executions", payload)

    def execute_workflow(
        self,
        payload: WorkflowRequest,
        *,
        request_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a declared workflow using tools registered by the runtime application.

        This request method does not register or discover tools. The runtime
        must be composed with the requested tools before the workflow runs.
        """
        response = self._request(
            "POST", "/v1/workflows/executions", cast(Mapping[str, Any], payload), request_id
        )
        return _validate_workflow_result(response)

    def transcribe(
        self,
        *,
        model: str,
        filename: str,
        audio: bytes,
        content_type: str = "application/octet-stream",
        language: str | None = None,
        prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Send audio bytes only to the configured runtime for transcription."""
        data: dict[str, str] = {"model": model}
        for key, value in (
            ("language", language),
            ("prompt", prompt),
            ("temperature", temperature),
        ):
            if value is not None:
                data[key] = str(value)
        try:
            response = self._client.post(
                "/v1/audio/transcriptions",
                data=data,
                files={"file": (filename, audio, content_type)},
            )
        except httpx.HTTPError as error:
            raise RuntimeError("Trussium runtime request failed.") from error
        if response.is_error:
            raise APIError(response.status_code, _error_code(response))
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Trussium runtime returned an invalid response.")
        return payload

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
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        error = payload.get("detail")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


def _validate_workflow_result(payload: dict[str, Any]) -> WorkflowResult:
    status = payload.get("status")
    steps = payload.get("steps")
    if status not in {"completed", "cancelled", "timed_out"} or not isinstance(steps, list):
        raise TypeError("Trussium runtime returned an invalid workflow response.")
    for step in steps:
        if (
            not isinstance(step, dict)
            or not isinstance(step.get("tool_name"), str)
            or not isinstance(step.get("output"), dict)
        ):
            raise TypeError("Trussium runtime returned an invalid workflow response.")
    return cast(WorkflowResult, payload)
