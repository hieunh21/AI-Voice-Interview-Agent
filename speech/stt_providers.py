"""Speech-to-text through Gemini audio understanding (same key/gateway as the LLM)."""

import asyncio
import logging
import re

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from speech.interfaces import SpeechError, SpeechUnavailable

logger = logging.getLogger(__name__)

MAX_HINTS = 200
_PREFIX = re.compile(r"^(transcript|bản ghi|nội dung)\s*:\s*", re.IGNORECASE)

PROMPT = """Chép lại NGUYÊN VĂN lời ứng viên nói trong đoạn âm thanh (tiếng Việt, có thể lẫn
thuật ngữ tiếng Anh).
- Danh sách gợi ý (không phân biệt hoa/thường) giúp nhận ra thuật ngữ đã nghe. Khi viết, dùng cách
  viết chuẩn phổ biến của thuật ngữ, ví dụ: LangGraph, Docker, PostgreSQL, BM25, RAG, Recall@K.
- Không thêm, bớt hay sửa ý; không trả lời câu hỏi; không bình luận; không dịch.
- Nếu không có lời nói rõ ràng, trả về chuỗi rỗng.
Danh sách gợi ý thuật ngữ: {hints}
Chỉ trả về transcript."""


def thinking_config(model: str) -> types.ThinkingConfig | None:
    """Transcription needs no reasoning; Gemini 2.5 Flash models accept a zero thinking budget."""
    return types.ThinkingConfig(thinking_budget=0) if "2.5-flash" in model else None


def clean_transcript(text: str) -> str:
    text = text.strip().strip("`").strip()
    text = _PREFIX.sub("", text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'“”":
        text = text[1:-1]
    return " ".join(text.split())


class GeminiSpeechToText:
    provider_id = "gemini"

    def __init__(
        self, *, api_key: str, model: str, timeout_seconds: float, base_url: str | None = None
    ) -> None:
        self._model = model
        self._timeout = timeout_seconds
        http_options = types.HttpOptions(base_url=base_url) if base_url else None
        self._client = genai.Client(api_key=api_key, http_options=http_options)

    async def transcribe(self, audio: bytes, *, mime_type: str, hints: list[str]) -> str:
        unique_hints = list(dict.fromkeys(h.strip() for h in hints if h.strip()))[:MAX_HINTS]
        prompt = PROMPT.format(hints=", ".join(unique_hints) or "(không có)")
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=[types.Part.from_bytes(data=audio, mime_type=mime_type), prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.0, thinking_config=thinking_config(self._model)
                    ),
                ),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise SpeechError(
                "Nhận dạng giọng nói quá lâu. Hãy thử lại hoặc gõ câu trả lời."
            ) from exc
        except genai_errors.ClientError as exc:
            logger.warning("STT rejected by provider: HTTP %s", exc.code)
            if exc.code in (401, 403, 429):
                raise SpeechUnavailable(
                    "Dịch vụ nhận dạng giọng nói tạm thời không dùng được. Hãy gõ câu trả lời."
                ) from exc
            raise SpeechError("Không nhận dạng được bản ghi âm này.") from exc
        except genai_errors.APIError as exc:
            logger.warning("STT provider error: HTTP %s", exc.code)
            raise SpeechError("Dịch vụ nhận dạng giọng nói đang lỗi. Hãy thử lại.") from exc

        transcript = clean_transcript(response.text or "")
        if not transcript:
            raise SpeechError(
                "Không nghe rõ câu trả lời. Hãy nói gần micro hơn, thử lại, hoặc gõ câu trả lời."
            )
        return transcript
