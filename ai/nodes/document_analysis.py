"""Optional CV/JD analysis: one LLM extraction call, then evidence checks against the source text.

Anything the model claims that cannot be found in the document is dropped, so the planner can
never attribute an invented project to the candidate. Without an LLM (or on failure) the analysis
degrades to "keywords": the selector still matches skill keywords against the raw text.
"""

import logging
import re

from ai.llm.base import LLMError, StructuredLLM
from ai.prompts import extraction
from ai.schemas.documents import CandidateProfile, CandidateProject, DocumentAnalysis, JobSpec
from ai.schemas.enums import Level, Role

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    Role.AI_ENGINEER: "AI Engineer",
    Role.BACKEND_DEVELOPER: "Backend Developer",
    Role.DATA_ENGINEER: "Data Engineer",
}
_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().casefold()


def appears_in(fragment: str, source: str) -> bool:
    fragment = _norm(fragment)
    return bool(fragment) and fragment in _norm(source)


def _candidate(out: extraction.CandidateOut, cv_text: str) -> CandidateProfile:
    projects = []
    for project in out.projects[:6]:
        if not appears_in(project.evidence, cv_text):
            logger.info("Dropping CV project without verbatim evidence")
            continue
        projects.append(
            CandidateProject(
                name=project.name.strip() or "Dự án",
                summary=project.summary.strip()[:400],
                technologies=[t for t in project.technologies if appears_in(t, cv_text)][:15],
                evidence=project.evidence.strip()[:300],
            )
        )
    years = out.years_of_experience if 0 <= out.years_of_experience <= 50 else None
    return CandidateProfile(
        skills=list(dict.fromkeys(s for s in out.skills if appears_in(s, cv_text)))[:40],
        projects=projects,
        years_of_experience=years,
    )


def _job(out: extraction.JobOut, jd_text: str) -> JobSpec:
    def keep(items: list[str]) -> list[str]:
        return list(dict.fromkeys(i.strip() for i in items if i.strip()))[:40]

    return JobSpec(
        title=out.title.strip() or None,
        role_guess=None if out.role_guess == "other" else Role(out.role_guess),
        levels=list(dict.fromkeys(Level(level) for level in out.levels)),
        required_skills=keep(out.required_skills),
        nice_to_have=keep(out.nice_to_have),
    )


def mismatch_warnings(job: JobSpec | None, role: Role, level: Level) -> list[str]:
    warnings = []
    if job is not None and job.role_guess is not None and job.role_guess is not role:
        warnings.append(
            f"JD có vẻ dành cho vị trí {ROLE_LABELS[job.role_guess]}, khác vị trí bạn chọn "
            f"({ROLE_LABELS[role]}). Kế hoạch vẫn theo vị trí bạn đã chọn."
        )
    if job is not None and job.levels and level not in job.levels:
        accepted = "/".join(lv.value.capitalize() for lv in job.levels)
        warnings.append(
            f"JD tuyển cấp độ {accepted}, khác cấp độ bạn chọn ({level.value.capitalize()}). "
            "Kế hoạch vẫn theo cấp độ bạn đã chọn."
        )
    return warnings


async def analyze_documents(
    llm: StructuredLLM | None,
    *,
    cv_text: str | None,
    jd_text: str | None,
    role: Role,
    level: Level,
) -> DocumentAnalysis:
    if not cv_text and not jd_text:
        return DocumentAnalysis(source="none")
    if llm is None:
        return DocumentAnalysis(source="keywords")
    try:
        out = await llm.generate(
            system=extraction.SYSTEM,
            prompt=extraction.build_prompt(cv_text, jd_text),
            schema=extraction.ExtractionOutput,
            temperature=0.0,
        )
    except LLMError as exc:
        logger.warning("Document extraction failed, using keyword matching only: %s", exc)
        return DocumentAnalysis(source="keywords")

    candidate = _candidate(out.candidate, cv_text) if cv_text and out.has_cv else None
    job = _job(out.job, jd_text) if jd_text and out.has_jd else None
    return DocumentAnalysis(
        candidate=candidate,
        job=job,
        source="llm",
        warnings=mismatch_warnings(job, role, level),
    )
