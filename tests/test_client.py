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
