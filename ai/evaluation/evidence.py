"""Evidence checker: a quote counts only if it appears verbatim in the cited answer."""

import re

_WS = re.compile(r"\s+")
_TYPOGRAPHIC = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."})
_EDGE = " .,;:!?\"'()[]-"
MIN_QUOTE_CHARS = 3


def _normalise(text: str) -> str:
    return _WS.sub(" ", text.translate(_TYPOGRAPHIC)).strip().casefold()


def quote_is_verbatim(quote: str, answer: str) -> bool:
    """Case/whitespace/typographic-quote insensitive substring check; edge punctuation ignored."""
    needle = _normalise(quote).strip(_EDGE)
    return len(needle) >= MIN_QUOTE_CHARS and needle in _normalise(answer)
