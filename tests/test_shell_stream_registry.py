"""Tests for shell stream registry (no ``app`` package import — avoids PYTHONPATH clashes)."""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY = (
    _REPO_ROOT
    / "agent"
    / "app"
    / "engine"
    / "xcode_coding_agent"
    / "shell_stream_registry.py"
)


def _load_registry():
    spec = importlib.util.spec_from_file_location("xcode_shell_stream_registry", _REGISTRY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["xcode_shell_stream_registry"] = mod
    spec.loader.exec_module(mod)
    return mod


_reg = _load_registry()
clear_shell_stream_registry = _reg.clear_shell_stream_registry
get_shell_stream_queue_for_thread = _reg.get_shell_stream_queue_for_thread
register_shell_stream_queue = _reg.register_shell_stream_queue
unregister_shell_stream_queue = _reg.unregister_shell_stream_queue


@pytest.fixture(autouse=True)
def _clear_registry():
    clear_shell_stream_registry()
    yield
    clear_shell_stream_registry()


def test_register_unregister_roundtrip():
    q = register_shell_stream_queue("thread-a", 100)
    assert q is not None
    assert get_shell_stream_queue_for_thread("thread-a") is q
    unregister_shell_stream_queue("thread-a")
    assert get_shell_stream_queue_for_thread("thread-a") is None


def test_register_zero_chunks_returns_none():
    assert register_shell_stream_queue("t", 0) is None
