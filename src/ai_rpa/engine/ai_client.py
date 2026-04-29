"""OpenAI GPT client wrapper for AI-RPA."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# Retry settings for API errors
MAX_API_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class AIClient:
    """Wrapper around OpenAI GPT API with retry logic."""

    def __init__(self, api_key: str, model: str = "gpt-4o",
                 base_url: Optional[str] = None):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system_prompt: str, user_message: str,
             json_mode: bool = True, temperature: float = 0.1) -> str:
        """Send a chat completion request.

        Args:
            system_prompt: System role content.
            user_message: User role content.
            json_mode: If True, request JSON output format.
            temperature: Sampling temperature (low = more deterministic).

        Returns:
            The response text content.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(MAX_API_RETRIES):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("Empty response from API")
                return content
            except Exception as e:
                last_error = e
                logger.warning(
                    "API call failed (attempt %d/%d): %s",
                    attempt + 1, MAX_API_RETRIES, e,
                )
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))

        raise RuntimeError(f"API call failed after {MAX_API_RETRIES} retries: {last_error}")

    def chat_json(self, system_prompt: str, user_message: str,
                  temperature: float = 0.1) -> dict:
        """Send a chat request and parse the JSON response.

        Returns:
            Parsed dict from the JSON response.
        """
        text = self.chat(system_prompt, user_message, json_mode=True, temperature=temperature)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI JSON response: %s\nRaw: %s", e, text[:500])
            raise
