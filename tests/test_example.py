import importlib.util
from pathlib import Path
from types import ModuleType


def _load_example() -> ModuleType:
    path = Path(__file__).parents[1] / "examples" / "basic.py"
    spec = importlib.util.spec_from_file_location("trussium_python_example", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_uses_self_hosted_defaults_and_overrides() -> None:
    example = _load_example()
    assert example.settings_from_env({}) == (
        "http://127.0.0.1:9000",
        "llama3.1:8b",
        "Say hello from the Python SDK.",
    )
    assert example.settings_from_env(
        {"TRUSSIUM_URL": "http://runtime:9000", "TRUSSIUM_MODEL": "model", "TRUSSIUM_PROMPT": "Hi"}
    ) == ("http://runtime:9000", "model", "Hi")
