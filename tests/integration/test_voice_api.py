"""Voice endpoints with fake STT/TTS providers against PostgreSQL."""

import uuid

import pytest
from fastapi.testclient import TestClient
from helpers import (
    FakeSpeechToText,
    FakeTextToSpeech,
    create_session,
    fake_llm,
    guest_headers,
    make_wav,
    requires_db,
    run_sql,
)

from app.core.config import Settings
from app.main import create_app
from speech.interfaces import SpeechUnavailable

pytestmark = requires_db


@pytest.fixture
def voice(settings: Settings, migrated: None):
    run_sql(settings.database_url, "TRUNCATE users CASCADE")
    stt, tts = FakeSpeechToText(), FakeTextToSpeech()
    with TestClient(create_app(settings, llm=fake_llm(), stt=stt, tts=tts)) as client:
        yield client, stt, tts


def _running(client: TestClient) -> tuple[dict[str, str], str]:
    headers = guest_headers(client)
    sid = create_session(client, headers)["id"]
    client.post(f"/api/interviews/{sid}/prepare", headers=headers)
    client.post(f"/api/interviews/{sid}/start", headers=headers)
    return headers, sid


def _upload(client, headers, sid, data, mime="audio/wav"):
    return client.post(
        f"/api/interviews/{sid}/transcribe",
        headers=headers,
        files={"file": ("answer.wav", data, mime)},
    )


def test_capabilities_reflect_configured_providers(voice, settings: Settings) -> None:
    client, _, _ = voice
    assert client.get("/api/speech/capabilities").json() == {
        "stt": True,
        "tts": True,
        "tts_provider": "fake-tts",
    }
    with TestClient(create_app(settings, llm=None, stt=None, tts=None)) as bare:
        assert bare.get("/api/speech/capabilities").json() == {
            "stt": False,
            "tts": False,
            "tts_provider": None,
        }


def test_recording_becomes_an_editable_transcript(voice) -> None:
    client, stt, _ = voice
    headers, sid = _running(client)
    response = _upload(client, headers, sid, make_wav(2))
    assert response.status_code == 200, response.text
    assert response.json()["text"] == stt.transcript
    size, mime, hints = stt.calls[-1]
    assert mime == "audio/wav"
    assert size > 60_000
    assert any(h in hints for h in ("rag", "RAG", "LLM"))  # skill keywords bias the spelling

    # The (edited) transcript is submitted as a voice answer.
    answered = client.post(
        f"/api/interviews/{sid}/answer",
        headers=headers,
        json={
            "request_id": uuid.uuid4().hex,
            "turn_no": 1,
            "answer_text": response.json()["text"] + " (đã sửa)",
            "answer_mode": "voice",
        },
    )
    assert answered.status_code == 200


@pytest.mark.parametrize(
    ("data", "mime", "status"),
    [
        (make_wav(2), "video/mp4", 422),
        (b"tiny", "audio/wav", 422),
        (make_wav(200, rate=8_000), "audio/wav", 422),
    ],
)
def test_bad_recordings_are_rejected_before_stt(voice, data, mime, status) -> None:
    client, stt, _ = voice
    headers, sid = _running(client)
    assert _upload(client, headers, sid, data, mime).status_code == status
    assert stt.calls == []


def test_transcription_only_during_an_interview(voice) -> None:
    client, _, _ = voice
    headers = guest_headers(client)
    sid = create_session(client, headers)["id"]
    assert _upload(client, headers, sid, make_wav(2)).status_code == 409


def test_unavailable_stt_asks_to_type(voice) -> None:
    client, stt, _ = voice
    headers, sid = _running(client)
    stt.error = SpeechUnavailable("Dịch vụ nhận dạng giọng nói tạm thời không dùng được.")
    response = _upload(client, headers, sid, make_wav(2))
    assert response.status_code == 503
    assert "không dùng được" in response.json()["detail"]


def test_question_audio_speaks_only_this_sessions_questions(voice) -> None:
    client, _, tts = voice
    headers, sid = _running(client)
    response = client.get(f"/api/interviews/{sid}/turns/1/audio", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    question = client.get(f"/api/interviews/{sid}", headers=headers).json()["turns"][0]
    assert tts.calls == [question["question_text"]]
    assert client.get(f"/api/interviews/{sid}/turns/9/audio", headers=headers).status_code == 404
    stranger = guest_headers(client)
    assert client.get(f"/api/interviews/{sid}/turns/1/audio", headers=stranger).status_code == 404


def test_tts_failure_lets_the_browser_voice_take_over(voice) -> None:
    client, _, tts = voice
    headers, sid = _running(client)
    tts.error = SpeechUnavailable("Dịch vụ đọc câu hỏi tạm thời không dùng được.")
    assert client.get(f"/api/interviews/{sid}/turns/1/audio", headers=headers).status_code == 503
