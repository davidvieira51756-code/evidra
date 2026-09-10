import os
from typing import Protocol

import httpx


class AIProviderError(Exception):
    """Raised when a configured provider cannot produce a usable response."""


class AIProvider(Protocol):
    @property
    def is_configured(self) -> bool:
        """Return whether the provider has enough configuration to be used."""

    @property
    def disabled_reason(self) -> str:
        """Return the deterministic fallback limitation when the provider is disabled."""

    def generate(self, prompt: str) -> str:
        """Generate a raw JSON response string for an explanation prompt."""


class OllamaProvider:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self.model = model if model is not None else os.getenv("OLLAMA_MODEL", "")
        configured_base_url = (
            base_url if base_url is not None else os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self.base_url = configured_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.model)

    @property
    def disabled_reason(self) -> str:
        return "GenAI is disabled because OLLAMA_MODEL is not configured."

    def generate(self, prompt: str) -> str:
        if not self.is_configured:
            raise AIProviderError(self.disabled_reason)

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "prompt": prompt,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as exception:
            raise AIProviderError(describe_ollama_failure(exception)) from exception


def describe_ollama_failure(exception: Exception) -> str:
    if isinstance(exception, httpx.HTTPStatusError):
        response_text = exception.response.text.replace("\n", " ")
        return (
            f"Ollama API returned HTTP {exception.response.status_code}: "
            f"{truncate(response_text, 240)}"
        )

    if isinstance(exception, httpx.RequestError):
        return f"Ollama API request failed before receiving a response: {exception.__class__.__name__}."

    return f"GenAI response handling failed: {exception.__class__.__name__}."


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
