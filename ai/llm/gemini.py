"""Gemini adapter using google-genai structured output (JSON constrained by a Pydantic schema)."""

import asyncio
import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from ai.llm.base import LLMError, LLMInvalidOutput, LLMQuotaExceeded, LLMTimeout, T

logger = logging.getLogger(__name__)

_RETRYABLE_SERVER_ATTEMPTS = 2


class GeminiLLM:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        base_url: str | None = None,
    ) -> None:
        self.model_id = model
        self._timeout = timeout_seconds
        # base_url lets the same Gemini API be reached through a compatible gateway/proxy.
        http_options = types.HttpOptions(base_url=base_url) if base_url else None
        self._client = genai.Client(api_key=api_key, http_options=http_options)

    async def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.2
    ) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )
        last_error: LLMError = LLMError("no attempt made")
        for attempt in range(1, _RETRYABLE_SERVER_ATTEMPTS + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self.model_id, contents=prompt, config=config
                    ),
                    timeout=self._timeout,
                )
            except TimeoutError as exc:
                raise LLMTimeout(f"{self.model_id} timed out after {self._timeout:.0f}s") from exc
            except genai_errors.ClientError as exc:
                if exc.code == 429:
                    raise LLMQuotaExceeded(f"{self.model_id} quota exceeded") from exc
                raise LLMError(f"{self.model_id} rejected the request (HTTP {exc.code})") from exc
            except genai_errors.ServerError as exc:
                last_error = LLMError(f"{self.model_id} server error (HTTP {exc.code})")
                logger.warning("Gemini server error on attempt %d: HTTP %s", attempt, exc.code)
                continue
            except genai_errors.APIError as exc:
                raise LLMError(f"{self.model_id} API error (HTTP {exc.code})") from exc

            usage = response.usage_metadata
            if usage is not None:
                logger.info(
                    "Gemini %s usage: prompt=%s output=%s tokens",
                    schema.__name__,
                    usage.prompt_token_count,
                    usage.candidates_token_count,
                )
            text = response.text or ""
            try:
                return schema.model_validate_json(text)
            except ValidationError:
                last_error = LLMInvalidOutput(f"{self.model_id} returned invalid {schema.__name__}")
                logger.warning("Gemini returned invalid %s on attempt %d", schema.__name__, attempt)
        raise last_error
