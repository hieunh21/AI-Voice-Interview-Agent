"""Structured views of the optional CV / JD. Candidate claims need a verbatim quote."""

from pydantic import Field

from ai.schemas.common import ContractModel, NonEmptyStr
from ai.schemas.enums import Level, Role


class CandidateProject(ContractModel):
    name: NonEmptyStr
    summary: str = Field(default="", max_length=400)
    technologies: list[str] = Field(default_factory=list, max_length=15)
    # Verbatim excerpt of the CV proving this project exists (checked after extraction).
    evidence: NonEmptyStr


class CandidateProfile(ContractModel):
    skills: list[str] = Field(default_factory=list, max_length=40)
    projects: list[CandidateProject] = Field(default_factory=list, max_length=6)
    years_of_experience: float | None = Field(default=None, ge=0, le=50)


class JobSpec(ContractModel):
    title: str | None = None
    role_guess: Role | None = None
    # Every level the JD accepts (e.g. "Fresher/Junior"); empty when not stated.
    levels: list[Level] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list, max_length=40)
    nice_to_have: list[str] = Field(default_factory=list, max_length=40)


class DocumentAnalysis(ContractModel):
    candidate: CandidateProfile | None = None
    job: JobSpec | None = None
    source: str = "none"  # "llm" | "keywords" | "none"
    warnings: list[str] = Field(default_factory=list)
