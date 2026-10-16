#!/usr/bin/env python3
"""Focused configuration tests for embed_helper.py."""
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("embed_helper.py")
previous_numpy = sys.modules.get("numpy")
if previous_numpy is None:
    sys.modules["numpy"] = SimpleNamespace()
spec = importlib.util.spec_from_file_location("embed_helper", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
try:
    spec.loader.exec_module(module)
finally:
    if previous_numpy is None:
        sys.modules.pop("numpy", None)


def test_process_environment_overrides_dotenv_values():
    process_values = {
        "EMBED_API_BASE": "https://process.example.test",
        "EMBED_API_KEY": "process-key",
        "EMBED_MODEL": "process-model",
    }
    dotenv = (
        "EMBED_API_BASE=https://dotenv.example.test\n"
        "EMBED_API_KEY=dotenv-key\n"
        "EMBED_MODEL=dotenv-model\n"
    )
    with patch.object(module.Path, "exists", return_value=True), \
            patch.object(module.Path, "read_text", return_value=dotenv), \
            patch.dict(os.environ, process_values, clear=False):
        env = module._load_env()
    for key, value in process_values.items():
        assert env[key] == value


def test_cache_namespace_isolates_api_endpoints():
    settings = {
        "_API_PATH": "/v1/embeddings",
        "_MODEL": "shared-model",
    }
    with patch.multiple(module, _API_BASE="https://first.example.test", **settings):
        first = module._cache_namespace()
    with patch.multiple(module, _API_BASE="https://second.example.test", **settings):
        second = module._cache_namespace()

    assert first != second


if __name__ == "__main__":
    test_process_environment_overrides_dotenv_values()
    test_cache_namespace_isolates_api_endpoints()
    print("embed helper regression: PASS")
