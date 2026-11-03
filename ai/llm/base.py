from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Any failure to obtain a valid structured response. Messages never contain user content."""


class LLMTimeout(LLMError):
    pass


class LLMQuotaExceeded(LLMError):
    """Provider quota/rate limit hit. We never fall back to a paid model automatically."""


class LLMInvalidOutput(LLMError):
    """The model answered, but not with JSON matching the requested schema."""


class StructuredLLM(Protocol):
    model_id: str

    async def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.2
    ) -> T:
        """Return `schema` parsed from the model's JSON output, or raise LLMError."""
        ...
