"""Voice use-cases. Audio is processed in memory only: nothing recorded is ever stored."""

import logging
import re
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.playbook_loader import PlaybookLibrary
from ai.schemas.enums import SessionStatus
from app.models import InterviewSession, InterviewTurn
from app.services.interviews import ServiceError
from speech.audio import validate_audio
from speech.interfaces import (
    SpeechError,
    SpeechToText,
    SpeechUnavailable,
    SynthesizedAudio,
    TextToSpeech,
)

logger = logging.getLogger(__name__)

# Standalone ASCII tokens with an uppercase letter, digit or symbol are technical terms
# (RAG, Recall@K, CI/CD); plain lowercase ASCII words may be unaccented Vietnamese ("trong").
_TOKEN = re.compile(r"(?<!\w)[A-Za-z][A-Za-z0-9@.+#/_-]*[A-Za-z0-9](?!\w)")
_TERM_MARK = re.compile(r"[A-Z0-9@.+#/_-]")


def stt_hints(question: str, keywords: list[str]) -> list[str]:
    """Question terms (original casing, e.g. "RAG") first, then keywords; deduped ignoring case."""
    terms = [t for t in _TOKEN.findall(question) if _TERM_MARK.search(t)]
    seen: set[str] = set()
    hints = []
    for term in [*terms, *keywords]:
        if term.casefold() not in seen:
            seen.add(term.casefold())
            hints.append(term)
    return hints


async def transcribe_answer(
    db: AsyncSession,
    session: InterviewSession,
    stt: SpeechToText | None,
    library: PlaybookLibrary,
    *,
    data: bytes,
    content_type: str | None,
    max_bytes: int,
) -> tuple[str, int]:
    if stt is None:
        raise ServiceError(503, "Nhận dạng giọng nói chưa được cấu hình. Hãy gõ câu trả lời.")
    if session.status is not SessionStatus.IN_PROGRESS:
        raise ServiceError(409, "Chỉ ghi âm được khi buổi phỏng vấn đang diễn ra.")
    try:
        mime = validate_audio(data, content_type, max_bytes)
    except SpeechError as exc:
        raise ServiceError(413 if len(data) > max_bytes else 422, str(exc)) from exc

    pending = await db.scalar(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session.id, InterviewTurn.answer_text.is_(None))
        .order_by(InterviewTurn.turn_no.desc())
    )
    # The current skill's terms first, then every library term: a single skill's list alone biases
    # the model towards the wrong neighbour (e.g. "LangChain" for a spoken "LangGraph").
    hints: list[str] = []
    if pending is not None:
        skill = library.skills.get(pending.skill_id)
        keywords = list(skill.meta.keywords) if skill else []
        keywords += [k for s in library.skills.values() for k in s.meta.keywords]
        hints = stt_hints(pending.question_text, keywords)

    started = time.perf_counter()
    try:
        text = await stt.transcribe(data, mime_type=mime, hints=hints)
    except SpeechUnavailable as exc:
        raise ServiceError(503, str(exc)) from exc
    except SpeechError as exc:
        raise ServiceError(422, str(exc)) from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "STT session %s turn %s: %d KB in %d ms",
        session.id,
        pending.turn_no if pending else "-",
        len(data) // 1024,
        latency_ms,
    )
    return text, latency_ms


async def question_audio(
    db: AsyncSession, session: InterviewSession, tts: TextToSpeech | None, turn_no: int
) -> SynthesizedAudio:
    """Speak one of this session's questions (never arbitrary text: protects TTS credits)."""
    if tts is None:
        raise ServiceError(503, "Giọng đọc chưa được cấu hình.")
    turn = await db.scalar(
        select(InterviewTurn).where(
            InterviewTurn.session_id == session.id, InterviewTurn.turn_no == turn_no
        )
    )
    if turn is None:
        raise ServiceError(404, "Không tìm thấy câu hỏi.")
    started = time.perf_counter()
    try:
        audio = await tts.synthesize(turn.question_text)
    except SpeechUnavailable as exc:
        raise ServiceError(503, str(exc)) from exc
    except SpeechError as exc:
        raise ServiceError(502, str(exc)) from exc
    logger.info(
        "TTS session %s turn %d: %d ms", session.id, turn_no, (time.perf_counter() - started) * 1000
    )
    return audio
