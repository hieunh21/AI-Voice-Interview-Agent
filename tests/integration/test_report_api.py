"""Report jobs end to end: interview ends → background evaluation → GET report (PostgreSQL)."""

import time
import uuid

from fastapi.testclient import TestClient
from helpers import create_session, fake_llm, guest_headers, requires_db, run_sql

from ai.evaluation.evaluator import Evaluator
from ai.llm.base import LLMTimeout
from ai.schemas.evaluation import InterviewReport
from app.core.config import Settings
from app.main import create_app

pytestmark = requires_db

LONG = "Câu trả lời đầy đủ: " + "nêu khái niệm, ví dụ cụ thể và trade-off khi áp dụng. " * 3


def _running(client: TestClient) -> tuple[dict[str, str], str]:
    headers = guest_headers(client)
    sid = create_session(client, headers)["id"]
    client.post(f"/api/interviews/{sid}/prepare", headers=headers)
    client.post(f"/api/interviews/{sid}/start", headers=headers)
    return headers, sid


def _answer(client, headers, sid, answer):
    turn_no = client.get(f"/api/interviews/{sid}", headers=headers).json()["turns"][-1]["turn_no"]
    return client.post(
        f"/api/interviews/{sid}/answer",
        headers=headers,
        json={"request_id": uuid.uuid4().hex, "turn_no": turn_no, "answer_text": answer},
    ).json()


def _wait_report(client, headers, sid, until=("completed", "failed"), timeout=20.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/interviews/{sid}/report", headers=headers).json()
        if body["status"] in until:
            return body
        time.sleep(0.1)
    raise AssertionError(f"report still {body['status']}")


def test_finished_interview_gets_an_evidence_backed_report(
    client: TestClient, settings: Settings
) -> None:
    headers, sid = _running(client)
    view = {"status": "in_progress"}
    answers = iter(["Dùng vector database.", LONG, "Em không biết ạ.", LONG, LONG, LONG])
    while view["status"] == "in_progress":
        view = _answer(client, headers, sid, next(answers))
    assert view["report_status"] in ("pending", "processing", "completed")

    body = _wait_report(client, headers, sid)
    assert body["status"] == "completed"
    report = InterviewReport.model_validate(body["report"])
    assert [q.question_id for q in report.questions] == ["q_001", "q_002", "q_003"]
    turns = {t["turn_no"]: t["answer_text"] for t in view["turns"]}
    for result in report.questions:
        for criterion in result.criteria:
            for evidence in criterion.evidence:
                assert evidence.quote.split()[0] in turns[evidence.turn_no]
    assert report.overall_score is not None
    assert report.disclaimer

    rows = run_sql(
        settings.database_url,
        "SELECT count(*) FROM answer_evaluations WHERE session_id = :id",
        id=uuid.UUID(sid),
    )
    assert rows[0][0] == 3
    summary = client.get("/api/interviews", headers=headers).json()[0]
    assert summary["report_status"] == "completed"
    assert summary["overall_score"] == report.overall_score


def test_ending_early_evaluates_only_answered_questions(client: TestClient) -> None:
    headers, sid = _running(client)
    _answer(client, headers, sid, LONG)
    client.post(f"/api/interviews/{sid}/finish", headers=headers)
    report = _wait_report(client, headers, sid)["report"]
    assert [q["question_id"] for q in report["questions"]] == ["q_001"]


def test_no_answers_means_no_report(client: TestClient) -> None:
    headers, sid = _running(client)
    view = client.post(f"/api/interviews/{sid}/finish", headers=headers).json()
    assert view["report_status"] is None
    assert client.get(f"/api/interviews/{sid}/report", headers=headers).status_code == 404


def test_failed_evaluation_can_be_retried_without_duplicates(
    settings: Settings, migrated: None
) -> None:
    run_sql(settings.database_url, "TRUNCATE users CASCADE")
    app = create_app(settings, llm=fake_llm(evaluation_error=LLMTimeout("slow")))
    with TestClient(app) as client:
        headers, sid = _running(client)
        _answer(client, headers, sid, LONG)
        client.post(f"/api/interviews/{sid}/finish", headers=headers)
        failed = _wait_report(client, headers, sid)
        assert failed == {"status": "failed", "report": None}

        app.state.reports._evaluator = Evaluator(fake_llm())  # provider is back
        client.post(f"/api/interviews/{sid}/report/retry", headers=headers)
        assert _wait_report(client, headers, sid)["status"] == "completed"
        again = client.post(f"/api/interviews/{sid}/report/retry", headers=headers).json()
        assert again["status"] == "completed"  # retrying a completed report is a no-op
        rows = run_sql(
            settings.database_url,
            "SELECT attempts FROM interview_reports WHERE session_id = :id",
            id=uuid.UUID(sid),
        )
        assert rows[0][0] == 2


def test_pending_reports_resume_after_a_restart(settings: Settings, migrated: None) -> None:
    run_sql(settings.database_url, "TRUNCATE users CASCADE")
    with TestClient(create_app(settings, llm=fake_llm())) as client:
        headers, sid = _running(client)
        _answer(client, headers, sid, LONG)
        client.post(f"/api/interviews/{sid}/finish", headers=headers)
        _wait_report(client, headers, sid)
    # Simulate a crash mid-job: the row is left "processing" with an old start time.
    run_sql(
        settings.database_url,
        "UPDATE interview_reports SET status = 'processing', report_json = NULL, "
        "started_at = now() - interval '1 hour' WHERE session_id = :id",
        id=uuid.UUID(sid),
    )
    with TestClient(create_app(settings, llm=fake_llm())) as restarted:
        assert _wait_report(restarted, headers, sid)["status"] == "completed"


def test_reports_are_private(client: TestClient) -> None:
    headers, sid = _running(client)
    _answer(client, headers, sid, LONG)
    client.post(f"/api/interviews/{sid}/finish", headers=headers)
    stranger = guest_headers(client)
    assert client.get(f"/api/interviews/{sid}/report", headers=stranger).status_code == 404
    assert client.post(f"/api/interviews/{sid}/report/retry", headers=stranger).status_code == 404
