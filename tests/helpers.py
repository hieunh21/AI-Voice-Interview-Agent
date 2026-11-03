"""Test helpers: a fake planner/extractor LLM that reads the real prompt, and a tiny PDF writer."""

import asyncio
import os
import re

import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.llm.base import LLMInvalidOutput
from ai.llm.fake import FakeLLM
from ai.prompts.evaluator import (
    CriterionOut,
    CrossCuttingOut,
    CrossSkillOut,
    EvidenceOut,
    ReportSummaryOut,
    SkillSummaryOut,
    ThreadEvaluationOut,
)
from ai.prompts.extraction import CandidateOut, ExtractionOutput, JobOut, ProjectOut
from ai.prompts.interviewer import LiveDecisionOut
from ai.prompts.planner import PlannedQuestionOut, PlannerOutput

CV_TEXT = (
    "Nguyễn Văn A — AI Engineer Fresher.\n"
    "Dự án: Chatbot hỏi đáp nội quy công ty dùng LangGraph và Qdrant, hybrid search BM25 + "
    "embedding, đánh giá bằng Recall@5.\n"
    "Kỹ năng: Python, PyTorch, FastAPI, Docker."
)
JD_TEXT = (
    "Tuyển AI Engineer (Fresher). Yêu cầu: kinh nghiệm RAG, LLM agents với LangGraph, "
    "đánh giá mô hình, Kubernetes."
)

_SKILL_HEADER = re.compile(r"^## Skill (\w+) — .*\(target_questions: (\d+)\)", re.MULTILINE)
_SEED_ID = re.compile(r"^- seed_id: (\w+)", re.MULTILINE)


def parse_planner_prompt(prompt: str) -> dict[str, tuple[int, list[str]]]:
    """{skill_id: (target_questions, [seed ids in context])} from the real planner prompt."""
    result: dict[str, tuple[int, list[str]]] = {}
    headers = list(_SKILL_HEADER.finditer(prompt))
    for i, header in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(prompt)
        seeds = _SEED_ID.findall(prompt[header.end() : end])
        result[header.group(1)] = (int(header.group(2)), seeds)
    return result


def default_planner_output(prompt: str, *, with_cv_question: bool = True) -> PlannerOutput:
    questions = []
    has_cv = "<candidate_cv>\n" in prompt
    for skill_id, (target, seeds) in parse_planner_prompt(prompt).items():
        slots = list(seeds[:target])
        if has_cv and with_cv_question and skill_id == "rag_systems" and slots:
            slots.pop()
            questions.append(
                PlannedQuestionOut(
                    skill_id=skill_id,
                    origin="cv",
                    source_seed_id="",
                    question_text="Trong dự án chatbot dùng Qdrant, bạn gộp kết quả BM25 và "
                    "embedding thế nào?",
                    objective="Kiểm tra hiểu biết thực tế về hybrid retrieval",
                    personalization_note="CV: chatbot nội quy dùng Qdrant và hybrid search",
                    expected_points=["Reciprocal Rank Fusion", "đo Recall@5 trước và sau"],
                    followup_hints=["Vì sao không cộng trực tiếp điểm?"],
                )
            )
        for seed_id in slots:
            questions.append(
                PlannedQuestionOut(
                    skill_id=skill_id,
                    origin="seed_adapted",
                    source_seed_id=seed_id,
                    question_text=f"(diễn đạt lại) Câu hỏi cho {seed_id}?",
                    objective="",
                    personalization_note="",
                    expected_points=[],
                    followup_hints=[],
                )
            )
    return PlannerOutput(questions=questions)


def default_extraction(prompt: str) -> ExtractionOutput:
    has_cv = "<candidate_cv>(không có)" not in prompt
    has_jd = "<job_description>(không có)" not in prompt
    return ExtractionOutput(
        has_cv=has_cv,
        candidate=CandidateOut(
            skills=["Python", "LangGraph", "Qdrant", "Kotlin"],  # Kotlin is not in the CV
            projects=[
                ProjectOut(
                    name="Chatbot nội quy",
                    summary="Chatbot RAG hỏi đáp nội quy",
                    technologies=["LangGraph", "Qdrant"],
                    evidence="Chatbot hỏi đáp nội quy công ty dùng LangGraph và Qdrant",
                ),
                ProjectOut(  # invented: no verbatim evidence in the CV
                    name="Hệ thống gợi ý phim",
                    summary="",
                    technologies=["Spark"],
                    evidence="Xây dựng hệ thống gợi ý phim cho 1 triệu người dùng",
                ),
            ]
            if has_cv
            else [],
            years_of_experience=0.5 if has_cv else -1,
        ),
        has_jd=has_jd,
        job=JobOut(
            title="AI Engineer" if has_jd else "",
            role_guess="ai_engineer" if has_jd else "other",
            levels=["fresher", "junior"] if has_jd else [],
            required_skills=["RAG", "LangGraph", "Kubernetes"] if has_jd else [],
            nice_to_have=[],
        ),
    )


_ANSWER = re.compile(r"<candidate_answer>(.*?)</candidate_answer>", re.DOTALL)


def latest_answer(prompt: str) -> str:
    answers = _ANSWER.findall(prompt)
    return answers[-1] if answers else ""


def default_live_decision(prompt: str) -> LiveDecisionOut:
    """Short answer → follow-up quoting it; "không biết" → move on; otherwise → move on."""
    answer = latest_answer(prompt)
    allowed_follow_up = "follow_up" in prompt.split("Hành động được phép:")[-1].split(".")[0]
    if "không biết" in answer.lower():
        return LiveDecisionOut(
            answer_quality="no_answer",
            covered_points=[],
            missing_points=["mọi ý"],
            next_action="move_on",
            question_text="",
            brief_note="ứng viên không biết",
        )
    if len(answer) < 60 and allowed_follow_up:
        return LiveDecisionOut(
            answer_quality="partial",
            covered_points=[],
            missing_points=["ý chính"],
            next_action="follow_up",
            question_text=f"Bạn vừa nói “{answer[:30]}”. Bạn giải thích rõ hơn vì sao không?",
            brief_note="thiếu ý",
        )
    return LiveDecisionOut(
        answer_quality="strong",
        covered_points=["ý chính"],
        missing_points=[],
        next_action="move_on",
        question_text="",
        brief_note="đủ ý",
    )


_CRITERION = re.compile(r"^- criterion_id: (\w+) \(", re.MULTILINE)
_TURN_ANSWER = re.compile(r'<candidate_answer turn="(\d+)">(.*?)</candidate_answer>', re.DOTALL)


def _criteria_out(prompt: str, *, invent: bool) -> list[CriterionOut]:
    answers = [(int(n), text) for n, text in _TURN_ANSWER.findall(prompt)]
    turn_no, text = answers[0]
    quote = "Tôi bịa ra câu này" if invent else " ".join(text.split()[:6])
    score = 1 if "không biết" in text.lower() else (4 if len(text) > 60 else 2)
    return [
        CriterionOut(
            criterion_id=cid,
            score=score,
            rationale="Nhận xét giả lập.",
            evidence=[EvidenceOut(turn_no=turn_no, quote=quote)],
        )
        for cid in _CRITERION.findall(prompt)
    ]


def default_thread_evaluation(prompt: str, mode: str) -> ThreadEvaluationOut:
    invent = mode == "invented" or (mode == "invented_once" and "Lần chấm trước" not in prompt)
    return ThreadEvaluationOut(
        insufficient_evidence=mode == "insufficient",
        criteria=[] if mode == "insufficient" else _criteria_out(prompt, invent=invent),
        covered_points=["ý đã nêu"],
        missed_points=["ý còn thiếu"],
        strengths=["Điểm mạnh giả lập"],
        gaps=["Điểm cần cải thiện giả lập"],
        improvement_suggestion="Nêu thêm ví dụ và cách đo.",
    )


def default_cross_cutting(prompt: str) -> CrossCuttingOut:
    skills = []
    for section in prompt.split("## skill_id: ")[1:]:
        skill_id = section.split(" ", 1)[0]
        transcript = prompt[prompt.index("Toàn bộ transcript:") :]
        skills.append(
            CrossSkillOut(
                skill_id=skill_id,
                criteria=_criteria_out(section.split("\n\n")[0] + "\n" + transcript, invent=False),
                summary=f"Tóm tắt {skill_id}",
            )
        )
    return CrossCuttingOut(skills=skills)


def fake_llm(
    *,
    planner_failures: int = 0,
    extraction_error: Exception | None = None,
    live_error: Exception | None = None,
    evaluation_mode: str = "valid",
    evaluation_error: Exception | None = None,
) -> FakeLLM:
    """evaluation_mode: valid | invented | invented_once | insufficient."""
    state = {"planner_failures": planner_failures}

    def responder(system: str, prompt: str, schema: type[BaseModel]) -> BaseModel | Exception:
        if schema is ExtractionOutput:
            return extraction_error or default_extraction(prompt)
        if schema is PlannerOutput:
            if state["planner_failures"] > 0:
                state["planner_failures"] -= 1
                return LLMInvalidOutput("bad json")
            return default_planner_output(prompt)
        if schema is LiveDecisionOut:
            return live_error or default_live_decision(prompt)
        if schema is ThreadEvaluationOut:
            return evaluation_error or default_thread_evaluation(prompt, evaluation_mode)
        if schema is CrossCuttingOut:
            return evaluation_error or default_cross_cutting(prompt)
        if schema is ReportSummaryOut:
            return evaluation_error or ReportSummaryOut(
                skill_summaries=[SkillSummaryOut(skill_id="rag_systems", summary="Tóm tắt RAG")],
                top_strengths=["Giải thích rõ ràng"],
                priority_improvements=["Bổ sung số liệu"],
                study_topics=["Recall@K"],
            )
        raise AssertionError(f"unexpected schema {schema}")

    return FakeLLM(responder=responder)


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MAX_UPLOAD = 50_000
requires_db = [
    pytest.mark.db,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to run DB tests"),
]


def run_sql(database_url: str, statement: str, **params):
    """Run one SQL statement on a fresh async engine; returns rows for SELECTs."""

    async def run():
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text(statement), params)
                return result.all() if result.returns_rows else None
        finally:
            await engine.dispose()

    return asyncio.run(run())


def guest_headers(client) -> dict[str, str]:
    response = client.post("/api/auth/guest")
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def create_session(client, headers: dict[str, str], **payload) -> dict:
    body = {"role": "ai_engineer", "level": "fresher", "mode": "demo", **payload}
    response = client.post("/api/interviews", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


class FakeSpeechToText:
    provider_id = "fake-stt"

    def __init__(
        self, transcript: str = "Em sẽ dùng RAG với hybrid search và đo Recall@K."
    ) -> None:
        self.transcript = transcript
        self.calls: list[tuple[int, str, list[str]]] = []
        self.error: Exception | None = None

    async def transcribe(self, audio: bytes, *, mime_type: str, hints: list[str]) -> str:
        self.calls.append((len(audio), mime_type, hints))
        if self.error:
            raise self.error
        return self.transcript


class FakeTextToSpeech:
    provider_id = "fake-tts"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    async def synthesize(self, text: str):
        from speech.interfaces import SynthesizedAudio

        self.calls.append(text)
        if self.error:
            raise self.error
        return SynthesizedAudio(data=b"ID3fake-mp3:" + text.encode(), mime_type="audio/mpeg")


def make_wav(seconds: float, rate: int = 16_000) -> bytes:
    """Mono 16-bit PCM WAV of silence."""
    import struct

    samples = int(seconds * rate)
    data = b"\x00\x00" * samples
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        rate,
        rate * 2,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data


def make_pdf(text: str) -> bytes:
    """Minimal single-page PDF with a Helvetica text layer (ASCII text only)."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)
