"""LLM configuration for local or cloud inference."""

import os
from dataclasses import dataclass
from typing import Optional


DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434/v1"


@dataclass
class LLMConfig:
    """Configuration for the agent's LLM (local or cloud)."""

    base_url: Optional[str] = None  # None = use default cloud provider
    model: str = "gpt-4o-mini"  # default when cloud
    api_key: Optional[str] = None

    def is_local(self) -> bool:
        return self.base_url is not None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        endpoint = os.environ.get("XCODE_LLM_ENDPOINT")
        model = os.environ.get("XCODE_MODEL", "gpt-4o-mini")
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("XCODE_LLM_API_KEY")
        return cls(base_url=endpoint or None, model=model, api_key=api_key or None)

    @classmethod
    def for_local(
        cls,
        base_url: str = DEFAULT_OLLAMA_ENDPOINT,
        model: str = "llama3.2",
    ) -> "LLMConfig":
        return cls(base_url=base_url, model=model, api_key=None)
