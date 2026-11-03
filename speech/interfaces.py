"""Provider-agnostic speech interfaces. Swapping STT/TTS vendors never touches the API or UI."""

from dataclasses import dataclass
from typing import Protocol


class SpeechError(Exception):
    """A speech step failed; the message is user-facing (Vietnamese) and contains no user data."""


class SpeechUnavailable(SpeechError):
    """The provider is not configured, unauthorised or out of quota: the UI falls back to text."""


@dataclass(frozen=True)
class SynthesizedAudio:
    data: bytes
    mime_type: str


class SpeechToText(Protocol):
    provider_id: str

    async def transcribe(self, audio: bytes, *, mime_type: str, hints: list[str]) -> str:
        """Return the verbatim transcript. `hints` bias the spelling of technical terms."""
        ...


class TextToSpeech(Protocol):
    provider_id: str

    async def synthesize(self, text: str) -> SynthesizedAudio: ...
