"""Run a minimal completion against an existing Trussium runtime."""

import os
from collections.abc import Mapping

from trussium_sdk import TrussiumClient


def settings_from_env(environ: Mapping[str, str] | None = None) -> tuple[str, str, str]:
    """Return runtime URL, model, and prompt from environment settings."""
    values = environ if environ is not None else os.environ
    return (
        values.get("TRUSSIUM_URL", "http://127.0.0.1:9000"),
        values.get("TRUSSIUM_MODEL", "llama3.1:8b"),
        values.get("TRUSSIUM_PROMPT", "Say hello from the Python SDK."),
    )


def main() -> None:
    """Check the runtime and print one completion."""
    base_url, model, prompt = settings_from_env()

    with TrussiumClient(base_url) as client:
        print(f"Ready: {client.readiness()}")
        print(f"Capabilities: {client.capabilities()}")
        response = client.complete(
            {"model": model, "messages": [{"role": "user", "content": prompt}]},
            request_id="python-example",
        )
        print(f"Completion: {response}")


if __name__ == "__main__":
    main()
