"""Small, private settings file; never written into the selected vault."""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def settings_path() -> Path:
    return Path(os.environ.get("BLUEBELL_SETTINGS_DIR", PROJECT_ROOT / ".local")) / "settings.json"


def load_settings() -> dict:
    try:
        result = json.loads(settings_path().read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(values: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, indent=2), encoding="utf-8")
    temporary.replace(path)
