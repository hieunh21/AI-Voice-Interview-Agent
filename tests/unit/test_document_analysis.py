from ai.nodes.document_analysis import appears_in, mismatch_warnings
from ai.schemas.documents import JobSpec
from ai.schemas.enums import Level, Role


def test_no_level_warning_when_jd_accepts_the_chosen_level() -> None:
    job = JobSpec(role_guess=Role.AI_ENGINEER, levels=[Level.FRESHER, Level.JUNIOR])
    assert mismatch_warnings(job, Role.AI_ENGINEER, Level.FRESHER) == []


def test_level_and_role_mismatches_are_reported() -> None:
    job = JobSpec(role_guess=Role.DATA_ENGINEER, levels=[Level.JUNIOR])
    warnings = mismatch_warnings(job, Role.BACKEND_DEVELOPER, Level.INTERN)
    assert len(warnings) == 2
    assert "Data Engineer" in warnings[0]
    assert "Junior" in warnings[1]


def test_unknown_level_or_role_raises_no_warning() -> None:
    assert mismatch_warnings(JobSpec(), Role.AI_ENGINEER, Level.INTERN) == []


def test_evidence_matching_ignores_case_and_whitespace() -> None:
    source = "Dự án: Chatbot hỏi đáp\nquy chế   đào tạo"
    assert appears_in("chatbot hỏi đáp quy chế đào tạo", source)
    assert not appears_in("hệ thống gợi ý phim", source)
    assert not appears_in("   ", source)
