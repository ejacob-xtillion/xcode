"""
OpenAI-compatible LLM URL helpers (Ollama, LM Studio, vLLM, etc.).

xgraph and other OpenAI-SDK clients expect a *base URL* that includes the ``/v1`` path
segment. Ollama's default listen URL is ``http://localhost:11434`` but the API lives at
``http://localhost:11434/v1``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse, urlunparse


def normalize_openai_compatible_base_url(endpoint: str | None) -> str | None:
    """
    Normalize an LLM HTTP endpoint for OpenAI-compatible clients.

    Ollama (default port 11434) is rewritten to ``scheme://host:port/v1`` when the path
    does not already end with ``/v1``.

    Args:
        endpoint: Raw base URL from config or environment.

    Returns:
        Normalized URL, or None if endpoint is empty.
    """
    if endpoint is None:
        return None
    raw = str(endpoint).strip()
    if not raw:
        return None
    raw = raw.rstrip("/")
    parsed = urlparse(raw)
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/v1"):
        return raw
    # Default Ollama listen address (with or without explicit port)
    if parsed.port == 11434 or parsed.netloc in ("localhost:11434", "127.0.0.1:11434"):
        return urlunparse((parsed.scheme, parsed.netloc, "/v1", "", "", "")).rstrip("/")
    return raw


@contextmanager
def xgraph_openai_environ(openai_base_url: str | None) -> Iterator[None]:
    """
    Temporarily set ``OPENAI_BASE_URL`` (and optionally ``OPENAI_API_KEY``) for xgraph.

    xgraph's description generator reads ``OPENAI_BASE_URL`` / ``OPENAI_API_KEY``.
    Ollama does not require a real key; we set ``ollama`` only if no key is present.

    Restores previous environment keys after the block.
    """
    url = normalize_openai_compatible_base_url(openai_base_url) if openai_base_url else None
    if not url:
        yield
        return

    saved: dict[str, str | None] = {}
    try:
        saved["OPENAI_BASE_URL"] = os.environ.get("OPENAI_BASE_URL")
        os.environ["OPENAI_BASE_URL"] = url
        if not os.environ.get("OPENAI_API_KEY"):
            saved["OPENAI_API_KEY"] = None
            os.environ["OPENAI_API_KEY"] = "ollama"
        yield
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
