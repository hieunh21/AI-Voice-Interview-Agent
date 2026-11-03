"""Upload validation for recorded answers. Audio is processed in memory and never stored."""

import struct

from speech.interfaces import SpeechError

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
}
MIN_AUDIO_BYTES = 2_000
MAX_AUDIO_SECONDS = 185  # the recorder stops at 180 s


def base_mime_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def wav_duration_seconds(data: bytes) -> float | None:
    """Duration of a PCM WAV file from its header, or None if the header is not a simple WAV."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    offset = 12
    byte_rate = None
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        (size,) = struct.unpack("<I", data[offset + 4 : offset + 8])
        if chunk_id == b"fmt " and size >= 16:
            (byte_rate,) = struct.unpack("<I", data[offset + 16 : offset + 20])
        elif chunk_id == b"data":
            if not byte_rate:
                return None
            return min(size, len(data) - offset - 8) / byte_rate
        offset += 8 + size + (size % 2)
    return None


def validate_audio(data: bytes, content_type: str | None, max_bytes: int) -> str:
    """Return the normalised MIME type or raise SpeechError with a user-facing message."""
    mime = base_mime_type(content_type)
    if mime not in ALLOWED_AUDIO_TYPES:
        raise SpeechError("Định dạng ghi âm không được hỗ trợ.")
    if len(data) > max_bytes:
        raise SpeechError(f"Bản ghi quá lớn (tối đa {max_bytes // (1024 * 1024)} MB).")
    if len(data) < MIN_AUDIO_BYTES:
        raise SpeechError("Bản ghi quá ngắn. Hãy giữ nút ghi âm lâu hơn một chút.")
    duration = (
        wav_duration_seconds(data) if mime in {"audio/wav", "audio/x-wav", "audio/wave"} else None
    )
    if duration is not None and duration > MAX_AUDIO_SECONDS:
        raise SpeechError("Bản ghi dài quá 3 phút. Hãy trả lời ngắn gọn hơn.")
    if mime in {"audio/x-wav", "audio/wave"}:
        mime = "audio/wav"
    return mime
