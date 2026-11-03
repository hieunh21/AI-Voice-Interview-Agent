"""Long-lived runtime objects built once at startup: playbook library, LLM client, PREP graph."""

import logging

from ai.graphs.prep_graph import Preparer
from ai.llm.base import StructuredLLM
from ai.llm.gemini import GeminiLLM
from ai.playbook_loader import PlaybookLibrary, load_library
from ai.playbooks.lint import lint_library
from app.core.config import Settings
from speech.interfaces import SpeechToText, TextToSpeech
from speech.stt_providers import GeminiSpeechToText
from speech.tts_providers import CachedTextToSpeech, ElevenLabsTextToSpeech

logger = logging.getLogger(__name__)


class PlaybookLibraryError(RuntimeError):
    pass


def load_validated_library(settings: Settings) -> PlaybookLibrary:
    """Refuse to start on an invalid library. Without draft permission the strict gate applies."""
    library = load_library()
    issues = lint_library(library, strict=not settings.allow_draft_playbooks)
    errors = [str(issue) for issue in issues if issue.severity == "error"]
    if errors:
        shown = "\n".join(errors[:20])
        raise PlaybookLibraryError(f"Playbook library has {len(errors)} error(s):\n{shown}")
    logger.info(
        "Playbook library loaded: %d role playbooks, %d skills (drafts allowed: %s)",
        len(library.roles),
        len(library.skills),
        settings.allow_draft_playbooks,
    )
    return library


def build_llm(settings: Settings) -> StructuredLLM | None:
    if settings.gemini_api_key is None:
        logger.warning("GEMINI_API_KEY is not set: plans are built from seeds, without CV/JD AI")
        return None
    if settings.gemini_base_url:
        logger.info("Gemini requests go through %s", settings.gemini_base_url)
    return GeminiLLM(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        timeout_seconds=settings.llm_timeout_seconds,
        base_url=settings.gemini_base_url,
    )


def build_stt(settings: Settings) -> SpeechToText | None:
    if settings.gemini_api_key is None:
        return None
    return GeminiSpeechToText(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        timeout_seconds=settings.stt_timeout_seconds,
        base_url=settings.gemini_base_url,
    )


def build_tts(settings: Settings) -> TextToSpeech | None:
    if settings.elevenlabs_api_key is None or not settings.elevenlabs_voice_id:
        logger.warning("ElevenLabs key or voice id missing: the browser voice reads questions")
        return None
    return CachedTextToSpeech(
        ElevenLabsTextToSpeech(
            api_key=settings.elevenlabs_api_key.get_secret_value(),
            voice_id=settings.elevenlabs_voice_id,
            model=settings.elevenlabs_model,
            timeout_seconds=settings.tts_timeout_seconds,
        )
    )


def build_preparer(
    settings: Settings, library: PlaybookLibrary, llm: StructuredLLM | None
) -> Preparer:
    return Preparer(
        library,
        llm,
        allow_draft=settings.allow_draft_playbooks,
        context_budget=settings.planner_context_chars,
    )
