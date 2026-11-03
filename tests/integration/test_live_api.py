"""LIVE interview API: start → answer (follow-ups, limits, idempotency, locking) → finish."""

import asyncio
import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from helpers import create_session, guest_headers, requires_db, run_sql
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings

pytestmark = requires_db

LONG = "Câu trả lời đầy đủ: " + "nêu khái niệm, ví dụ cụ thể và trade-off khi áp dụng. " * 3


def _ready(client: TestClient, headers: dict[str, str], **payload) -> str:
    session = create_session(client, headers, **payload)
    prepared = client.post(f"/api/interviews/{session['id']}/prepare", headers=headers)
    assert prepared.json()["status"] == "ready"
    return session["id"]


def _start(client: TestClient, headers: dict[str, str], sid: str) -> dict:
    response = client.post(f"/api/interviews/{sid}/start", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _answer(client, headers, sid, turn_no, answer, request_id=None):
    return client.post(
        f"/api/interviews/{sid}/answer",
        headers=headers,
        json={
            "request_id": request_id or uuid.uuid4().hex,
            "turn_no": turn_no,
            "answer_text": answer,
        },
    )


def test_full_demo_interview_with_follow_up_and_coverage(
    client: TestClient, settings: Settings
) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    view = _start(client, headers, sid)
    assert view["status"] == "in_progress"
    assert [(t["question_id"], t["answer_text"]) for t in view["turns"]] == [("q_001", None)]

    view = _answer(client, headers, sid, 1, "Dùng vector database.").json()
    follow_up = view["turns"][-1]
    assert (follow_up["question_id"], follow_up["kind"]) == ("q_001.f1", "follow_up")
    assert "Dùng vector database" in follow_up["question_text"]  # reacts to the actual answer

    view = _answer(client, headers, sid, 2, LONG).json()
    assert view["turns"][-1]["question_id"] == "q_002"
    view = _answer(client, headers, sid, 3, "Em không biết ạ.").json()
    assert view["turns"][-1]["question_id"] == "q_003"  # no pressing after "không biết"
    view = _answer(client, headers, sid, 4, LONG).json()

    assert view["status"] == "completed"
    assert view["end_reason"] == "plan_completed"
    assert all(t["answer_text"] for t in view["turns"])
    assert [t["question_id"] for t in view["turns"] if t["kind"] == "main"] == [
        "q_001",
        "q_002",
        "q_003",
    ]

    rows = run_sql(
        settings.database_url,
        "SELECT decision_json FROM interview_turns WHERE session_id = :id ORDER BY turn_no",
        id=uuid.UUID(sid),
    )
    decisions = [row[0] for row in rows]
    assert [d["action"] for d in decisions] == ["follow_up", "next_main", "next_main", "finish"]
    assert {d["source"] for d in decisions} == {"llm"}
    assert all("latency_ms" in d and "prompt_version" in d for d in decisions)


def test_retrying_the_same_request_is_a_no_op(client: TestClient) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    _start(client, headers, sid)
    first = _answer(client, headers, sid, 1, LONG, request_id="retry-key-123")
    again = _answer(client, headers, sid, 1, LONG, request_id="retry-key-123")
    assert first.status_code == again.status_code == 200
    assert first.json()["turns"] == again.json()["turns"]
    assert len(again.json()["turns"]) == 2


def test_stale_turn_number_is_rejected(client: TestClient) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    _start(client, headers, sid)
    _answer(client, headers, sid, 1, LONG)
    response = _answer(client, headers, sid, 1, "trả lời lại câu cũ")
    assert response.status_code == 409


def test_answers_require_a_running_interview(client: TestClient) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    assert _answer(client, headers, sid, 1, LONG).status_code == 409  # not started
    _start(client, headers, sid)
    finished = client.post(f"/api/interviews/{sid}/finish", headers=headers).json()
    assert (finished["status"], finished["end_reason"]) == ("completed", "user_ended")
    assert finished["turns"][0]["answer_text"] is None
    assert _answer(client, headers, sid, 1, LONG).status_code == 409  # already finished
    assert client.post(f"/api/interviews/{sid}/finish", headers=headers).status_code == 200
    assert client.post(f"/api/interviews/{sid}/start", headers=headers).status_code == 409


def test_start_is_idempotent_and_needs_a_plan(client: TestClient) -> None:
    headers = guest_headers(client)
    unprepared = create_session(client, headers)
    response = client.post(f"/api/interviews/{unprepared['id']}/start", headers=headers)
    assert response.status_code == 409
    sid = _ready(client, headers)
    assert _start(client, headers, sid)["turns"] == _start(client, headers, sid)["turns"]


def test_progress_survives_a_reload(client: TestClient) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    _start(client, headers, sid)
    _answer(client, headers, sid, 1, LONG)
    view = client.get(f"/api/interviews/{sid}", headers=headers).json()
    assert view["status"] == "in_progress"
    assert view["turns"][-1]["answer_text"] is None
    assert view["turns"][-1]["question_id"] == "q_002"


def test_concurrent_submission_is_rejected_while_one_is_processing(
    client: TestClient, settings: Settings
) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    _start(client, headers, sid)
    locked, release = threading.Event(), threading.Event()

    def hold_lock() -> None:
        async def run() -> None:
            engine = create_async_engine(settings.database_url)
            async with engine.begin() as conn:
                await conn.execute(
                    text("SELECT id FROM interview_sessions WHERE id = :id FOR UPDATE"),
                    {"id": uuid.UUID(sid)},
                )
                locked.set()
                while not release.is_set():
                    await asyncio.sleep(0.02)
            await engine.dispose()

        asyncio.run(run())

    holder = threading.Thread(target=hold_lock)
    holder.start()
    try:
        assert locked.wait(10)
        response = _answer(client, headers, sid, 1, LONG)
        assert response.status_code == 409
        assert "đang được xử lý" in response.json()["detail"]
    finally:
        release.set()
        holder.join(10)
    assert _answer(client, headers, sid, 1, LONG).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"request_id": "valid-id-1", "turn_no": 1, "answer_text": "   "},
        {"request_id": "bad id!", "turn_no": 1, "answer_text": "ok"},
        {"request_id": "valid-id-2", "turn_no": 0, "answer_text": "ok"},
        {"request_id": "valid-id-3", "turn_no": 1, "answer_text": "x" * 4001},
    ],
)
def test_invalid_answers_are_rejected(client: TestClient, body: dict) -> None:
    headers = guest_headers(client)
    sid = _ready(client, headers)
    _start(client, headers, sid)
    response = client.post(f"/api/interviews/{sid}/answer", headers=headers, json=body)
    assert response.status_code == 422


def test_strangers_cannot_drive_someone_elses_interview(client: TestClient) -> None:
    owner, stranger = guest_headers(client), guest_headers(client)
    sid = _ready(client, owner)
    assert client.post(f"/api/interviews/{sid}/start", headers=stranger).status_code == 404
    _start(client, owner, sid)
    assert _answer(client, stranger, sid, 1, LONG).status_code == 404
    assert client.post(f"/api/interviews/{sid}/finish", headers=stranger).status_code == 404
