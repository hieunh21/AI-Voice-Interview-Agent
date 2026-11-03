import pytest
from helpers import make_pdf

from ai.documents import DocumentError, extract_text


def test_pdf_text_layer_is_extracted() -> None:
    text, source = extract_text(
        make_pdf("Built a RAG chatbot with FastAPI and PostgreSQL for internal docs"),
        filename="cv.pdf",
        content_type="application/pdf",
    )
    assert source == "pdf"
    assert "RAG chatbot with FastAPI" in text


def test_pdf_without_text_is_rejected() -> None:
    with pytest.raises(DocumentError, match="lớp text"):
        extract_text(make_pdf(""), filename="scan.pdf", content_type="application/pdf")


def test_broken_pdf_is_rejected() -> None:
    with pytest.raises(DocumentError):
        extract_text(b"%PDF-1.4 not really", filename="x.pdf", content_type=None)


def test_utf8_text_is_normalised() -> None:
    data = "﻿Kỹ năng:\r\n\r\n\r\n\r\nPython\x00, SQL  ".encode()
    text, source = extract_text(data, filename="cv.txt", content_type="text/plain")
    assert source == "txt"
    assert text == "Kỹ năng:\n\nPython, SQL"


def test_utf16_with_bom_is_supported() -> None:
    text, _ = extract_text("Yêu cầu SQL".encode("utf-16"), filename="jd.txt", content_type=None)
    assert text == "Yêu cầu SQL"


@pytest.mark.parametrize(
    ("data", "filename"),
    [(b"\xff\xd8\xff", "photo.jpg"), ("Xin chào".encode("cp1258"), "cv.txt")],
)
def test_unsupported_or_undecodable_files(data: bytes, filename: str) -> None:
    with pytest.raises(DocumentError):
        extract_text(data, filename=filename, content_type=None)
