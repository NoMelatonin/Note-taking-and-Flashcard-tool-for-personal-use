"""Small, private settings file; never written into the selected vault."""

import json
import os
from pathlib import Path
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def settings_path() -> Path:
    return Path(os.environ.get("BLUEBELL_SETTINGS_DIR", PROJECT_ROOT / ".local")) / "settings.json"


def load_settings() -> dict:
    try:
        if settings_path().is_symlink():
            return {}
        result = json.loads(settings_path().read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(values: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.resolve() != path.parent.absolute():
        raise OSError("Refusing a symbolic link in the private settings path.")
    temporary = path.parent / (".settings-" + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(values, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
