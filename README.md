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

The client supports non-streaming chat completions, readiness, public
capability discovery, embeddings, moderation, image generation, transcription,
reranking, translation, batch jobs, video jobs, and controlled
application-declared tools.
It forwards a supplied request ID as `X-Request-ID` and returns `APIError` for
non-success runtime responses. It never installs the runtime or broadens tool
authority.

## Runnable self-hosted example

With a Trussium runtime running on port 9000, run the example from a source
checkout:

```bash
TRUSSIUM_URL=http://127.0.0.1:9000 \
TRUSSIUM_MODEL=llama3.1:8b \
TRUSSIUM_PROMPT="Say hello." \
uv run python examples/basic.py
```

The environment variables are optional. The example checks readiness and
capabilities before making one completion request. It calls an existing local,
private, or public runtime; it does not install or host Trussium.

## Development

```bash
uv sync --all-groups
uv run ruff check src tests
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```

GitHub Actions runs these checks on pushes and pull requests. A weekly
security workflow audits the committed `uv.lock` dependency versions, and
CodeQL scans the Python source on pull requests and on a weekly schedule.
