"""Provider-agnostic structured-output LLM interface (Gemini adapter + fake for tests)."""

from ai.llm.base import (
    LLMError,
    LLMInvalidOutput,
    LLMQuotaExceeded,
    LLMTimeout,
    StructuredLLM,
)

__all__ = ["LLMError", "LLMInvalidOutput", "LLMQuotaExceeded", "LLMTimeout", "StructuredLLM"]
