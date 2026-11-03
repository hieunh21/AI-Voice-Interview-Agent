import pytest

from ai.markdown import (
    FrontmatterError,
    parse_bullets,
    parse_fields,
    split_frontmatter,
    split_sections,
)


def test_split_frontmatter_returns_mapping_and_body() -> None:
    data, body = split_frontmatter("---\nid: x\nversion: 1.0.0\n---\n# Title\n")
    assert data == {"id": "x", "version": "1.0.0"}
    assert body.strip() == "# Title"


def test_split_frontmatter_strips_bom() -> None:
    data, _ = split_frontmatter("﻿---\nid: x\n---\nbody")
    assert data == {"id": "x"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("# No frontmatter", "must start"),
        ("---\nid: x\n# never closed", "not closed"),
        ("---\n- a\n- b\n---\n", "mapping"),
        ("---\nid: [unclosed\n---\n", "invalid YAML"),
    ],
)
def test_split_frontmatter_rejects_bad_input(text: str, message: str) -> None:
    with pytest.raises(FrontmatterError, match=message):
        split_frontmatter(text)


def test_split_sections_ignores_headings_inside_code_fences() -> None:
    text = "intro\n## A\nalpha\n```md\n## Not a heading\n```\n## B\nbeta"
    preamble, sections = split_sections(text, 2)
    assert preamble == "intro"
    assert [s.title for s in sections] == ["A", "B"]
    assert "## Not a heading" in sections[0].body


def test_split_sections_only_splits_requested_level() -> None:
    _, sections = split_sections("## A\n### A1\nx\n## B", 2)
    assert [s.title for s in sections] == ["A", "B"]
    assert sections[0].body.startswith("### A1")


def test_parse_bullets_joins_continuations_and_nested_items() -> None:
    text = "- first\n  continued\n- second\n  - nested\n\n* third"
    assert parse_bullets(text) == ["first continued", "second - nested", "third"]


def test_parse_fields_collects_multiline_values_and_duplicates() -> None:
    text = "**Levels:** intern, fresher\n**Expected points:**\n- a\n- b\n**Levels**: junior"
    fields, duplicates = parse_fields(text)
    assert fields["expected points"] == "- a\n- b"
    assert fields["levels"] == "junior"
    assert duplicates == ["levels"]
