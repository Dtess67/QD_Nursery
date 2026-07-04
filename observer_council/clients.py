from __future__ import annotations

import os
import requests

from .provenance import ObserverProvenance, Lineage
from .exceptions import ObserverUnavailableError, ObserverResponseError

TIMEOUT_SECONDS = 120


def call_observer(observer: ObserverProvenance, system_prompt: str, user_message: str) -> str:
    """
    Single entry point. Routes to the right vendor format based on lineage.
    Returns raw text response. Raises ObserverUnavailableError or
    ObserverResponseError — never returns a silent empty string.
    """
    if observer.lineage == Lineage.ALIBABA and observer.model_id == "qwen2.5:32b":
        return _call_ollama(observer, system_prompt, user_message)

    api_key = os.environ.get(observer.api_env_var, "")
    if not api_key:
        raise ObserverUnavailableError(
            f"{observer.name}: {observer.api_env_var} not set in environment."
        )

    if observer.lineage == Lineage.ANTHROPIC:
        return _call_anthropic(observer, api_key, system_prompt, user_message)
    elif observer.lineage == Lineage.GOOGLE:
        return _call_gemini(observer, api_key, system_prompt, user_message)
    else:
        # OpenAI, xAI, DeepSeek all speak the OpenAI-compatible chat format
        return _call_openai_compatible(observer, api_key, system_prompt, user_message)


# --------------------------------------------------------------------------- #
# Vendor-specific calls                                                        #
# --------------------------------------------------------------------------- #

def _call_anthropic(observer: ObserverProvenance, api_key: str,
                     system_prompt: str, user_message: str) -> str:
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": observer.model_id,
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        if not text:
            raise ObserverResponseError(f"{observer.name}: empty response body")
        return text
    except requests.RequestException as e:
        raise ObserverUnavailableError(f"{observer.name}: {e}") from e


def _call_openai_compatible(observer: ObserverProvenance, api_key: str,
                             system_prompt: str, user_message: str) -> str:
    """OpenAI, xAI (Grok), and DeepSeek all use this same request/response shape."""
    base_urls = {
        Lineage.OPENAI:   "https://api.openai.com/v1/chat/completions",
        Lineage.XAI:      "https://api.x.ai/v1/chat/completions",
        Lineage.DEEPSEEK: "https://api.deepseek.com/v1/chat/completions",
    }
    url = base_urls.get(observer.lineage)
    if not url:
        raise ObserverUnavailableError(f"{observer.name}: no endpoint configured for {observer.lineage}")

    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": observer.model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 2000,
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        if not text:
            raise ObserverResponseError(f"{observer.name}: empty response body")
        return text
    except requests.RequestException as e:
        raise ObserverUnavailableError(f"{observer.name}: {e}") from e
    except (KeyError, IndexError) as e:
        raise ObserverResponseError(f"{observer.name}: unexpected response shape: {e}") from e


def _call_gemini(observer: ObserverProvenance, api_key: str,
                  system_prompt: str, user_message: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{observer.model_id}:generateContent"
    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}],
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        if not text:
            raise ObserverResponseError(f"{observer.name}: empty response body")
        return text
    except requests.RequestException as e:
        raise ObserverUnavailableError(f"{observer.name}: {e}") from e
    except (KeyError, IndexError) as e:
        raise ObserverResponseError(f"{observer.name}: unexpected response shape: {e}") from e


def _call_ollama(observer: ObserverProvenance, system_prompt: str, user_message: str) -> str:
    """Local Qwen via Ollama — same pattern as the QD kernel's own OllamaClient."""
    try:
        from ollama import Client
        client = Client(host="http://localhost:11434")
        response = client.chat(
            model=observer.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        text = response.message.content
        if not text:
            raise ObserverResponseError(f"{observer.name}: empty response body")
        return text
    except Exception as e:
        raise ObserverUnavailableError(f"{observer.name}: {e}") from e
