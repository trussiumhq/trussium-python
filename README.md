# Trussium Python SDK

The official Python SDK calls an existing Trussium runtime. It does not install
or host the runtime, Kubernetes, Helm, or `trussium-operator`.

## Install

```bash
pip install trussium-sdk
```

## Usage

```python
from trussium_sdk import TrussiumClient

with TrussiumClient("http://127.0.0.1:9000") as client:
    response = client.complete(
        {"model": "llama3.1:8b", "messages": [{"role": "user", "content": "Say hello."}]},
        request_id="request-123",
    )
```

The foundation provides non-streaming chat completions, readiness, and public
capability discovery. It forwards a supplied request ID as `X-Request-ID` and
returns `APIError` for non-success runtime responses.

## Development

```bash
uv sync --all-groups
uv run ruff check src tests
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```
