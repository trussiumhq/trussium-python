import httpx
import pytest

from trussium_sdk import APIError, TrussiumClient, WorkflowRequest


def test_complete_forwards_request_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Request-ID"] == "request-123"
        return httpx.Response(200, json={"id": "chat-1"})

    with TrussiumClient(
        http_client=httpx.Client(
            base_url="http://runtime.test", transport=httpx.MockTransport(handler)
        )
    ) as client:
        assert client.complete({"model": "test", "messages": []}, request_id="request-123") == {
            "id": "chat-1"
        }


def test_api_errors_are_typed() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"code": "provider_unreachable"}})

    with (
        TrussiumClient(
            http_client=httpx.Client(
                base_url="http://runtime.test", transport=httpx.MockTransport(handler)
            )
        ) as client,
        pytest.raises(APIError, match="provider_unreachable") as raised,
    ):
        client.readiness()
    assert raised.value.status_code == 503


def test_additional_operations_use_stable_runtime_paths() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"ok": True})

    with TrussiumClient(
        http_client=httpx.Client(
            base_url="http://runtime.test", transport=httpx.MockTransport(handler)
        )
    ) as client:
        payload = {"model": "test"}
        client.embeddings(payload)
        client.moderations(payload)
        client.generate_image(payload)
        client.rerank(payload)
        client.translate(payload, request_id="translation-123")
        client.create_batch(payload)
        client.get_batch("batch-1")
        client.cancel_batch("batch-1")
        client.create_video(payload)
        client.get_video("video-1")
        client.execute_tool({"name": "echo", "arguments": {}})
        client.transcribe(model="whisper", filename="audio.wav", audio=b"audio")

    assert paths == [
        "/v1/embeddings",
        "/v1/moderations",
        "/v1/images/generations",
        "/v1/rerankings",
        "/v1/translations",
        "/v1/batches",
        "/v1/batches/batch-1",
        "/v1/batches/batch-1/cancel",
        "/v1/videos",
        "/v1/videos/video-1",
        "/v1/tools/executions",
        "/v1/audio/transcriptions",
    ]


def test_execute_workflow_sends_typed_request_and_request_id() -> None:
    expected: WorkflowRequest = {
        "steps": [
            {
                "id": "search",
                "invocation": {
                    "name": "knowledge.search",
                    "arguments": {"query": "runtime"},
                },
            }
        ],
        "deadline_seconds": 20,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/workflows/executions"
        assert request.headers["X-Request-ID"] == "workflow-request-1"
        assert request.read() == httpx.Request("POST", "http://runtime.test", json=expected).read()
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "steps": [{"tool_name": "knowledge.search", "output": {"matches": 1}}],
            },
        )

    with TrussiumClient(
        http_client=httpx.Client(
            base_url="http://runtime.test", transport=httpx.MockTransport(handler)
        )
    ) as client:
        result = client.execute_workflow(expected, request_id="workflow-request-1")

    assert result["status"] == "completed"
    assert result["steps"][0]["output"] == {"matches": 1}


def test_execute_workflow_preserves_runtime_error_code() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": {"code": "workflows_unavailable"}})

    with (
        TrussiumClient(
            http_client=httpx.Client(
                base_url="http://runtime.test", transport=httpx.MockTransport(handler)
            )
        ) as client,
        pytest.raises(APIError, match="workflows_unavailable") as raised,
    ):
        client.execute_workflow({"steps": []})

    assert raised.value.code == "workflows_unavailable"


def test_execute_workflow_rejects_malformed_success_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "completed", "steps": [{"output": []}]})

    with (
        TrussiumClient(
            http_client=httpx.Client(
                base_url="http://runtime.test", transport=httpx.MockTransport(handler)
            )
        ) as client,
        pytest.raises(TypeError, match="invalid workflow response"),
    ):
        client.execute_workflow(
            {"steps": [{"id": "search", "invocation": {"name": "docs.search", "arguments": {}}}]}
        )
