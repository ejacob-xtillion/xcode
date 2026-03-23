"""Tests for OpenAI-compatible URL normalization (Ollama, etc.)."""

import os

import pytest

from xcode.llm_compat import normalize_openai_compatible_base_url, xgraph_openai_environ


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("http://localhost:11434", "http://localhost:11434/v1"),
        ("http://127.0.0.1:11434", "http://127.0.0.1:11434/v1"),
        ("http://localhost:11434/", "http://localhost:11434/v1"),
        ("http://localhost:11434/v1", "http://localhost:11434/v1"),
        ("http://localhost:11434/v1/", "http://localhost:11434/v1"),
        ("https://api.openai.com/v1", "https://api.openai.com/v1"),
        ("http://localhost:8080", "http://localhost:8080"),
    ],
)
def test_normalize_openai_compatible_base_url(raw, expected):
    assert normalize_openai_compatible_base_url(raw) == expected


def test_xgraph_openai_environ_sets_and_restores(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with xgraph_openai_environ("http://localhost:11434"):
        assert os.environ["OPENAI_BASE_URL"] == "http://localhost:11434/v1"
        assert os.environ.get("OPENAI_API_KEY") == "ollama"
    assert "OPENAI_BASE_URL" not in os.environ
    assert "OPENAI_API_KEY" not in os.environ


def test_xgraph_openai_environ_preserves_existing_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    with xgraph_openai_environ("http://localhost:11434"):
        assert os.environ["OPENAI_BASE_URL"] == "http://localhost:11434/v1"
        assert os.environ["OPENAI_API_KEY"] == "secret"
    assert os.environ["OPENAI_API_KEY"] == "secret"
