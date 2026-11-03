from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/speech", tags=["speech"])


class SpeechCapabilities(BaseModel):
    stt: bool
    tts: bool
    tts_provider: str | None


@router.get("/capabilities", response_model=SpeechCapabilities)
async def capabilities(request: Request) -> SpeechCapabilities:
    """What voice features this deployment offers; the UI falls back to text/browser voice."""
    tts = request.app.state.tts
    return SpeechCapabilities(
        stt=request.app.state.stt is not None,
        tts=tts is not None,
        tts_provider=tts.provider_id if tts else None,
    )
