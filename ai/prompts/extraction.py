"""CV/JD structured extraction prompt (one call for both documents)."""

from typing import Literal

from pydantic import BaseModel, Field

from ai.prompts.untrusted import UNTRUSTED_DATA_RULE, wrap

EXTRACTION_PROMPT_VERSION = "1.1.0"


class ProjectOut(BaseModel):
    name: str
    summary: str = Field(description="1–2 câu tóm tắt bài toán và vai trò của ứng viên.")
    technologies: list[str]
    evidence: str = Field(description="Trích NGUYÊN VĂN một câu/cụm từ trong CV chứng minh dự án.")


class CandidateOut(BaseModel):
    skills: list[str] = Field(
        description="Kỹ năng/công nghệ được nêu rõ trong CV, viết như trong CV."
    )
    projects: list[ProjectOut] = Field(description="Tối đa 4 dự án nổi bật có trong CV.")
    years_of_experience: float = Field(description="Số năm kinh nghiệm làm việc; -1 nếu không rõ.")


class JobOut(BaseModel):
    title: str
    role_guess: Literal["ai_engineer", "backend_developer", "data_engineer", "other"]
    levels: list[Literal["intern", "fresher", "junior"]] = Field(
        description=(
            "Mọi cấp độ JD chấp nhận (ví dụ 'Fresher/Junior' → [fresher, junior]); "
            "[] nếu không nêu."
        )
    )
    required_skills: list[str]
    nice_to_have: list[str]


class ExtractionOutput(BaseModel):
    has_cv: bool
    candidate: CandidateOut
    has_jd: bool
    job: JobOut


SYSTEM = f"""Bạn trích xuất thông tin có cấu trúc từ CV và mô tả công việc (JD) cho một ứng dụng
luyện phỏng vấn kỹ thuật IT.

Quy tắc:
- {UNTRUSTED_DATA_RULE}
- Chỉ trích những gì được nêu rõ trong tài liệu. Không suy đoán, không bịa dự án, kỹ năng
  hay kinh nghiệm.
- Trường `evidence` của mỗi dự án phải là đoạn trích NGUYÊN VĂN từ CV; nếu không trích được
  thì bỏ dự án đó.
- Nếu không có CV: has_cv=false và để candidate rỗng. Nếu không có JD: has_jd=false, job.title="",
  role_guess="other", levels=[] và các danh sách rỗng.
- role_guess: ai_engineer (ML/LLM/RAG/AI), backend_developer (API/server/database), data_engineer
  (pipeline/ETL/SQL/big data), hoặc other.
- Giữ nguyên tên công nghệ như trong tài liệu (ví dụ "PostgreSQL", "LangGraph")."""


def build_prompt(cv_text: str | None, jd_text: str | None) -> str:
    return "\n\n".join(
        [
            "Trích xuất thông tin từ các tài liệu sau.",
            wrap("candidate_cv", cv_text),
            wrap("job_description", jd_text),
        ]
    )
