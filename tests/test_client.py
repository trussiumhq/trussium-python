import httpx
import pytest

from trussium_sdk import APIError, TrussiumClient


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
        "/v1/batches",
        "/v1/batches/batch-1",
        "/v1/batches/batch-1/cancel",
        "/v1/videos",
        "/v1/videos/video-1",
        "/v1/tools/executions",
        "/v1/audio/transcriptions",
    ]
