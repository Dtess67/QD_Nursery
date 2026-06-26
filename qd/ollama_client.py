from __future__ import annotations

import json
from ollama import Client
from .exceptions import ModelUnavailableError, ModelResponseError


class OllamaClient:
    """
    Direct Ollama Python library wrapper.
    No intermediate frameworks.
    Raises typed errors — ModelUnavailableError or ModelResponseError.
    """

    DEFAULT_MODEL = "qwen2.5:32b"
    DEFAULT_HOST  = "http://localhost:11434"

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
        self.model  = model
        self.client = Client(host=host)

    def complete(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """Single completion. Returns raw text."""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                options={"temperature": temperature},
            )
            return response.message.content
        except Exception as e:
            if "connect" in str(e).lower() or "refused" in str(e).lower():
                raise ModelUnavailableError(
                    f"Ollama not reachable at {self.client._client.base_url}: {e}"
                ) from e
            raise ModelUnavailableError(f"Ollama error: {e}") from e

    def complete_json(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> dict:
        """
        Completion expecting JSON. Returns parsed dict.
        Raises ModelUnavailableError if Ollama unreachable.
        Raises ModelResponseError if response is not valid JSON.
        """
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                format="json",
                options={"temperature": temperature},
            )
        except Exception as e:
            if "connect" in str(e).lower() or "refused" in str(e).lower():
                raise ModelUnavailableError(
                    f"Ollama not reachable: {e}"
                ) from e
            raise ModelUnavailableError(f"Ollama error: {e}") from e

        raw = response.message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ModelResponseError(
                f"Model returned invalid JSON: {e}\nRaw (first 500): {raw[:500]}"
            ) from e
