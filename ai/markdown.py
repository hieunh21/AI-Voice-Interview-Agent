"""Minimal, dependency-free Markdown helpers for playbook files.

Only what the playbook contract needs: YAML frontmatter, ATX headings (ignoring fenced code),
bullet lists and `**Label:**` fields. Anything richer stays as raw Markdown for the planner.
"""

import re
from dataclasses import dataclass

import yaml

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_BULLET_RE = re.compile(r"^([ \t]*)[-*+][ \t]+(.*)$")
_FIELD_RE = re.compile(r"^\*\*(?P<label>[^*:]+?)(?::\*\*|\*\*:)[ \t]*(?P<rest>.*)$")


class FrontmatterError(ValueError):
    """The file does not start with a valid `---` YAML mapping block."""


@dataclass(frozen=True)
class Section:
    title: str
    body: str


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Return (frontmatter mapping, Markdown body)."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file must start with a '---' YAML frontmatter block")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            raw = "\n".join(lines[1:index])
            try:
                data = yaml.safe_load(raw)
            except yaml.YAMLError as exc:
                raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise FrontmatterError("frontmatter must be a YAML mapping")
            return data, "\n".join(lines[index + 1 :])
    raise FrontmatterError("frontmatter is not closed with '---'")


def split_sections(text: str, level: int) -> tuple[str, list[Section]]:
    """Split `text` at headings of exactly `level` (# count). Headings inside code fences are text.

    Returns (preamble before the first heading, sections in document order).
    """
    preamble: list[str] = []
    sections: list[Section] = []
    title: str | None = None
    body: list[str] = []
    fence: str | None = None

    def flush() -> None:
        if title is not None:
            sections.append(Section(title=title, body="\n".join(body).strip()))

    for line in text.splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0] * 3
            elif marker.startswith(fence):
                fence = None
        elif fence is None:
            heading = _HEADING_RE.match(line)
            if heading and len(heading.group(1)) == level:
                flush()
                title = heading.group(2).strip()
                body = []
                continue
        (body if title is not None else preamble).append(line)
    flush()
    return "\n".join(preamble).strip(), sections


def parse_bullets(text: str) -> list[str]:
    """Top-level bullet items; indented continuation lines and nested bullets join their parent."""
    items: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _BULLET_RE.match(line)
        if match and len(match.group(1).expandtabs(4)) < 2:
            items.append(match.group(2).strip())
        elif items and (line.startswith((" ", "\t"))):
            items[-1] = f"{items[-1]} {line.strip()}"
    return [item for item in items if item]


def parse_fields(text: str) -> tuple[dict[str, str], list[str]]:
    """Parse `**Label:** value` blocks. A field's value runs until the next field.

    Returns ({lowercased label: raw value}, duplicate labels).
    """
    fields: dict[str, list[str]] = {}
    duplicates: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        match = _FIELD_RE.match(line.strip())
        if match:
            current = match.group("label").strip().lower()
            if current in fields:
                duplicates.append(current)
            fields[current] = [match.group("rest")]
        elif current is not None:
            fields[current].append(line)
    return {k: "\n".join(v).strip() for k, v in fields.items()}, duplicates
