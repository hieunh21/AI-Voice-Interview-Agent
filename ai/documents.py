"""Text extraction for optional CV/JD uploads (PDF with a text layer, or plain text)."""

import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_PAGES = 10
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BLANK_LINES = re.compile(r"\n{3,}")


class DocumentError(ValueError):
    """User-facing problem with an uploaded document (message is shown as-is, in Vietnamese)."""


def normalise_text(text: str) -> str:
    text = _CONTROL_CHARS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.strip() for line in text.split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def extract_text(data: bytes, *, filename: str, content_type: str | None) -> tuple[str, str]:
    """Return (normalised text, source) where source is "pdf" or "txt"."""
    name = filename.lower()
    is_pdf = name.endswith(".pdf") or content_type == "application/pdf" or data[:5] == b"%PDF-"
    if is_pdf:
        return _extract_pdf(data), "pdf"
    if name.endswith(".txt") or (content_type or "").startswith("text/"):
        return _decode_text(data), "txt"
    raise DocumentError("Chỉ hỗ trợ file PDF (có lớp text) hoặc TXT.")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise DocumentError("PDF đang được đặt mật khẩu, không đọc được.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentError(f"PDF quá dài (tối đa {MAX_PDF_PAGES} trang).")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except DocumentError:
        raise
    except (PdfReadError, ValueError, KeyError) as exc:
        raise DocumentError("Không đọc được file PDF.") from exc
    text = normalise_text(text)
    if len(text) < 30:
        raise DocumentError(
            "PDF không có lớp text (có thể là ảnh scan). Hãy dán nội dung dưới dạng văn bản."
        )
    return text


def _decode_text(data: bytes) -> str:
    encoding = "utf-16" if data[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise DocumentError("File TXT phải được lưu ở mã UTF-8.") from exc
    text = normalise_text(text)
    if not text:
        raise DocumentError("File không có nội dung.")
    return text
