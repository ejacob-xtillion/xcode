"""
LLM client for AI model interactions.
"""

import httpx

from xcode.llm_compat import normalize_openai_compatible_base_url


class LLMClient:
    """Client for LLM API operations."""

    def __init__(self, base_url: str | None = None, model: str = "gpt-5"):
        self.base_url = normalize_openai_compatible_base_url(base_url) if base_url else None
        self.model = model

    async def chat_completion(
        self,
        messages: list[dict],
        stream: bool = False,
        **kwargs,
    ) -> dict | httpx.Response:
        """
        Send chat completion request to LLM.

        Args:
            messages: List of message dictionaries
            stream: Whether to stream the response
            **kwargs: Additional parameters for the API

        Returns:
            Response dictionary or streaming response
        """
        if not self.base_url:
            raise ValueError("LLM base_url not configured")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": stream,
                    **kwargs,
                },
            )

            if stream:
                return response

            return response.json()
