"""Closed vocabularies shared by the AI layer, the API and the database."""

from enum import StrEnum


class Role(StrEnum):
    AI_ENGINEER = "ai_engineer"
    BACKEND_DEVELOPER = "backend_developer"
    DATA_ENGINEER = "data_engineer"


class Level(StrEnum):
    INTERN = "intern"
    FRESHER = "fresher"
    JUNIOR = "junior"


class InterviewMode(StrEnum):
    DEMO = "demo"
    STANDARD = "standard"


class SessionStatus(StrEnum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EndReason(StrEnum):
    PLAN_COMPLETED = "plan_completed"
    USER_ENDED = "user_ended"
    MAX_TURNS = "max_turns"
    TIME_BUDGET = "time_budget"


class TurnKind(StrEnum):
    """A question thread = one MAIN turn plus its FOLLOW_UP / CLARIFY turns."""

    MAIN = "main"
    FOLLOW_UP = "follow_up"
    CLARIFY = "clarify"


class NextAction(StrEnum):
    """What the LLM may propose after an answer. Finishing is decided by the backend only."""

    FOLLOW_UP = "follow_up"
    CLARIFY = "clarify"
    MOVE_ON = "move_on"


class AnswerQuality(StrEnum):
    STRONG = "strong"
    PARTIAL = "partial"
    WEAK = "weak"
    OFF_TOPIC = "off_topic"
    NO_ANSWER = "no_answer"


class AnswerMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class DocumentKind(StrEnum):
    CV = "cv"
    JD = "jd"


class DocumentSource(StrEnum):
    PASTE = "paste"
    PDF = "pdf"
    TXT = "txt"


class ReportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationStatus(StrEnum):
    SCORED = "scored"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PlaybookStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    DEPRECATED = "deprecated"


class Assessment(StrEnum):
    """QUESTION skills get dedicated questions; CROSS_CUTTING skills are scored over all answers."""

    QUESTION = "question"
    CROSS_CUTTING = "cross_cutting"


class InputSource(StrEnum):
    ROLE_CONFIG = "role_config"
    ROLE_PLAYBOOK = "role_playbook"
    COMPETENCY_SKILLS = "competency_skills"
    CV = "cv"
    JD = "jd"


class QuestionOrigin(StrEnum):
    SEED = "seed"
    SEED_ADAPTED = "seed_adapted"
    CV = "cv"
    JD = "jd"
