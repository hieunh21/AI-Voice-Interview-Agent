import os
import shutil
from pathlib import Path

import pytest

# Settings require DATABASE_URL; unit tests never connect, so a placeholder is enough.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://intervai:intervai@localhost:5432/intervai"
)
os.environ.setdefault("APP_ENV", "test")

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_DIR = REPO_ROOT / "ai"


@pytest.fixture
def library_copy(tmp_path: Path) -> tuple[Path, Path]:
    """A writable copy of the real playbooks + config, for tests that break files on purpose."""
    playbooks = tmp_path / "playbooks"
    config = tmp_path / "config"
    shutil.copytree(
        AI_DIR / "playbooks", playbooks, ignore=shutil.ignore_patterns("*.py", "__pycache__")
    )
    shutil.copytree(AI_DIR / "config", config)
    return playbooks, config
