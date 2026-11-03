"""Text-to-speech: ElevenLabs over HTTP, wrapped in an in-memory LRU cache.

Planned questions repeat across sessions, so caching by text saves both latency and credits.
"""

import hashlib
import logging
from collections import OrderedDict

import httpx

from speech.interfaces import SpeechError, SpeechUnavailable, SynthesizedAudio

logger = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io"
OUTPUT_FORMAT = "mp3_44100_64"
# Models that accept `language_code` to enforce the output language.
LANGUAGE_ENFORCING_MODELS = {"eleven_flash_v2_5", "eleven_turbo_v2_5"}


class ElevenLabsTextToSpeech:
    provider_id = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._voice_id = voice_id
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=ELEVENLABS_URL,
            headers={"xi-api-key": api_key},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def synthesize(self, text: str) -> SynthesizedAudio:
        body: dict[str, str] = {"text": text, "model_id": self._model}
        if self._model in LANGUAGE_ENFORCING_MODELS:
            body["language_code"] = "vi"
        try:
            response = await self._client.post(
                f"/v1/text-to-speech/{self._voice_id}",
                params={"output_format": OUTPUT_FORMAT},
                json=body,
            )
        except httpx.TimeoutException as exc:
            raise SpeechError("Đọc câu hỏi quá lâu, đang dùng giọng dự phòng.") from exc
        except httpx.HTTPError as exc:
            raise SpeechError("Không kết nối được dịch vụ giọng nói.") from exc

        if response.status_code in (401, 403, 429):
            status = _error_status(response)
            logger.warning("ElevenLabs refused TTS: HTTP %s (%s)", response.status_code, status)
            raise SpeechUnavailable("Dịch vụ đọc câu hỏi tạm thời không dùng được.")
        if response.status_code != 200 or not response.content:
            logger.warning("ElevenLabs TTS failed: HTTP %s", response.status_code)
            raise SpeechError("Không tạo được giọng đọc cho câu hỏi.")
        return SynthesizedAudio(data=response.content, mime_type="audio/mpeg")

    async def aclose(self) -> None:
        await self._client.aclose()


def _error_status(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail", {})
        return str(detail.get("status") or detail.get("code") or "unknown")
    except ValueError:
        return "unknown"


class CachedTextToSpeech:
    """LRU cache bounded by entry count and total bytes."""

    def __init__(self, inner, *, max_entries: int = 256, max_bytes: int = 32 * 1024 * 1024):
        self._inner = inner
        self.provider_id = inner.provider_id
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._entries: OrderedDict[str, SynthesizedAudio] = OrderedDict()
        self._bytes = 0
        self.hits = 0

    async def synthesize(self, text: str) -> SynthesizedAudio:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._entries.get(key)
        if cached is not None:
            self._entries.move_to_end(key)
            self.hits += 1
            return cached
        audio = await self._inner.synthesize(text)
        self._entries[key] = audio
        self._bytes += len(audio.data)
        while self._entries and (
            len(self._entries) > self._max_entries or self._bytes > self._max_bytes
        ):
            _, evicted = self._entries.popitem(last=False)
            self._bytes -= len(evicted.data)
        return audio

    async def aclose(self) -> None:
        closer = getattr(self._inner, "aclose", None)
        if closer is not None:
            await closer()
