from __future__ import annotations

import json
from typing import Any, TypeVar

from httpx import AsyncClient, HTTPError
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import AISettings
from app.models import TaskResponse


T = TypeVar("T", bound=BaseModel)


class AIClientError(RuntimeError):
    pass


class AIClient:
    def __init__(self, settings: AISettings):
        if not settings.is_ready():
            raise AIClientError(
                "AI settings are incomplete. Set OPENAI_API_KEY, OPENAI_MODEL, and OPENAI_BASE_URL."
            )
        self.settings = settings
        self.http_client = AsyncClient(
            proxy=settings.proxy_url,
            trust_env=settings.trust_env,
        )
        http_client = self.http_client if settings.proxy_url else None
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            http_client=http_client,
        )

    async def complete_text(self, prompt: str) -> str:
        if self.settings.api_endpoint:
            return await self._complete_text_from_endpoint(prompt)

        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful writing assistant for a Word plugin backend.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if self.settings.use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception:
            if not self.settings.use_json_mode:
                raise
            kwargs.pop("response_format", None)
            response = await self.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        if not content:
            raise AIClientError("Model returned an empty response.")
        return content

    async def _complete_text_from_endpoint(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful writing assistant for a Word plugin backend.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "n": 1,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        }
        if self.settings.use_json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http_client.post(
                self.settings.api_endpoint,
                headers=headers,
                json=payload,
                timeout=120,
            )
        except HTTPError as exc:
            raise AIClientError(
                "Failed to connect to the model endpoint. "
                "Check campus network/VPN, OPENAI_API_ENDPOINT, and proxy settings."
            ) from exc
        if response.status_code >= 400:
            raise AIClientError(
                f"Model endpoint returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIClientError(f"Unexpected model endpoint response: {data}") from exc

        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            content = "\n".join(part for part in text_parts if part)

        if not isinstance(content, str) or not content.strip():
            raise AIClientError(f"Model endpoint returned empty content: {data}")
        return content

    async def complete_model(self, prompt: str, model_type: type[T]) -> T:
        raw = await self.complete_text(prompt)
        data = _extract_json(raw)
        return model_type.model_validate(data)

    async def complete_task(self, prompt: str) -> TaskResponse:
        return await self.complete_model(prompt, TaskResponse)


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIClientError(f"Model did not return valid JSON: {raw}") from exc

    if not isinstance(parsed, dict):
        raise AIClientError("Model JSON response must be an object.")
    return parsed
