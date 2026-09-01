#!/usr/bin/env python3
"""Thin client for local Ollama /api/chat."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_TIMEOUT = 600


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    """HTTP client for Ollama /api/chat with JSON response parsing."""

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.host = (host or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        self.timeout = timeout or int(os.environ.get("OLLAMA_TIMEOUT", DEFAULT_TIMEOUT))

    @staticmethod
    def parse_json_response(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def chat(
        self,
        prompt: str,
        *,
        json_mode: bool = True,
        retries: int = 2,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    f"{self.host}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise OllamaError("Empty response from Ollama")
                parsed = self.parse_json_response(content)
                return parsed, data
            except (requests.RequestException, json.JSONDecodeError, OllamaError) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(2 * attempt)
                    continue
                raise OllamaError(f"Ollama chat failed after {retries} attempts: {exc}") from exc

        raise OllamaError(str(last_error))


_default_client = OllamaClient()


def parse_json_response(text: str) -> dict[str, Any]:
    return OllamaClient.parse_json_response(text)


def chat(
    prompt: str,
    *,
    model: str | None = None,
    host: str | None = None,
    json_mode: bool = True,
    timeout: int | None = None,
    retries: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    client = OllamaClient(host=host, model=model, timeout=timeout)
    return client.chat(prompt, json_mode=json_mode, retries=retries)
