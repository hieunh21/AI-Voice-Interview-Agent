"""Deterministic stand-in for tests and offline development."""

from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel

from ai.llm.base import T

Responder = Callable[[str, str, type[BaseModel]], BaseModel | Exception]


@dataclass
class FakeLLM:
    """Calls `responder(system, prompt, schema)`; an Exception return value is raised."""

    responder: Responder
    model_id: str = "fake-llm"
    calls: list[tuple[str, type[BaseModel]]] = field(default_factory=list)

    async def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.2
    ) -> T:
        self.calls.append((prompt, schema))
        result = self.responder(system, prompt, schema)
        if isinstance(result, Exception):
            raise result
        if not isinstance(result, schema):
            raise TypeError(
                f"responder returned {type(result).__name__}, expected {schema.__name__}"
            )
        return result
