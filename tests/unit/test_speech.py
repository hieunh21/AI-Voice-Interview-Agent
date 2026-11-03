import asyncio
import json

import httpx
import pytest
from helpers import make_wav

from app.services.voice import stt_hints
from speech.audio import base_mime_type, validate_audio, wav_duration_seconds
from speech.interfaces import SpeechError, SpeechUnavailable, SynthesizedAudio
from speech.stt_providers import clean_transcript
from speech.tts_providers import CachedTextToSpeech, ElevenLabsTextToSpeech

MAX = 8 * 1024 * 1024


def test_wav_duration_is_read_from_the_header() -> None:
    assert wav_duration_seconds(make_wav(2.5)) == pytest.approx(2.5)
    assert wav_duration_seconds(b"not a wav file at all, definitely not" * 3) is None


def test_validate_audio_accepts_recorder_formats() -> None:
    assert validate_audio(make_wav(3), "audio/wav", MAX) == "audio/wav"
    assert validate_audio(b"x" * 5000, "audio/webm;codecs=opus", MAX) == "audio/webm"
    assert base_mime_type("audio/ogg; codecs=opus") == "audio/ogg"


@pytest.mark.parametrize(
    ("data", "mime", "message"),
    [
        (make_wav(3), "video/mp4", "không được hỗ trợ"),
        (b"x" * 100, "audio/wav", "quá ngắn"),
        (b"x" * (MAX + 1), "audio/webm", "quá lớn"),
        (make_wav(200, rate=8_000), "audio/wav", "3 phút"),
    ],
)
def test_validate_audio_rejects_bad_recordings(data: bytes, mime: str, message: str) -> None:
    with pytest.raises(SpeechError, match=message):
        validate_audio(data, mime, MAX)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('  "Em dùng RAG."  ', "Em dùng RAG."),
        ("Transcript: em dùng   LangGraph", "em dùng LangGraph"),
        ("```\n```", ""),
    ],
)
def test_transcript_cleanup(raw: str, expected: str) -> None:
    assert clean_transcript(raw) == expected


def test_stt_hints_take_latin_terms_from_the_question() -> None:
    hints = stt_hints("Bạn đo Recall@K trong hệ thống RAG và CI/CD thế nào?", ["bm25", "rag"])
    assert hints[:3] == ["Recall@K", "RAG", "CI/CD"]
    assert "bm25" in hints
    assert "rag" not in hints  # the question's casing wins


def _tts(handler) -> ElevenLabsTextToSpeech:
    return ElevenLabsTextToSpeech(
        api_key="test-key",
        voice_id="voice123",
        model="eleven_flash_v2_5",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )


def test_elevenlabs_request_shape() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["xi-api-key"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"ID3audio")

    audio = asyncio.run(_tts(handler).synthesize("Xin chào"))
    assert audio == SynthesizedAudio(data=b"ID3audio", mime_type="audio/mpeg")
    assert seen["url"].startswith("https://api.elevenlabs.io/v1/text-to-speech/voice123")
    assert "output_format=mp3_44100_64" in seen["url"]
    assert seen["key"] == "test-key"
    assert seen["body"] == {
        "text": "Xin chào",
        "model_id": "eleven_flash_v2_5",
        "language_code": "vi",
    }


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, SpeechUnavailable), (429, SpeechUnavailable), (500, SpeechError)],
)
def test_elevenlabs_errors_map_to_speech_errors(status: int, error: type) -> None:
    body = {"detail": {"status": "missing_permissions"}}
    tts = _tts(lambda request: httpx.Response(status, json=body))
    with pytest.raises(error):
        asyncio.run(tts.synthesize("Xin chào"))


def test_elevenlabs_timeout_is_a_speech_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(SpeechError):
        asyncio.run(_tts(handler).synthesize("Xin chào"))


def test_cache_avoids_paying_twice_and_evicts_oldest() -> None:
    calls = []

    class Inner:
        provider_id = "inner"

        async def synthesize(self, text: str) -> SynthesizedAudio:
            calls.append(text)
            return SynthesizedAudio(data=text.encode(), mime_type="audio/mpeg")

    cache = CachedTextToSpeech(Inner(), max_entries=2)

    async def run() -> None:
        for text in ["a", "a", "b", "c", "a"]:
            await cache.synthesize(text)

    asyncio.run(run())
    assert calls == ["a", "b", "c", "a"]  # second "a" cached; "a" evicted after "b","c"
    assert cache.hits == 1
