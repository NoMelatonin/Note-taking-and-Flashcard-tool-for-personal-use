"""Every test vault and GUI setting stays in the repository's ignored work/."""

import shutil
import tempfile
from pathlib import Path

import pytest

from bluebell.qt_runtime import prepare_qt_plugins


def pytest_sessionstart(session):
    prepare_qt_plugins()


@pytest.fixture
def sandbox(monkeypatch):
    root = Path(__file__).resolve().parents[1] / "work" / "tests"
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="case-", dir=root))
    monkeypatch.setenv("BLUEBELL_SETTINGS_DIR", str(directory / "settings"))
    yield directory
    shutil.rmtree(directory)
