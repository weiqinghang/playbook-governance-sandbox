"""Resolve the user-confirmed language for human-facing Playbook collaboration."""
import json
from pathlib import Path


def resolve(path: Path) -> dict:
    if not path.exists():
        return {"status": "needs_user_confirmation", "reason": "configuration_missing"}
    value = json.loads(path.read_text(encoding="utf-8")).get("primary_language")
    if not isinstance(value, str) or not value.strip():
        return {"status": "needs_user_confirmation", "reason": "primary_language_missing"}
    return {"status": "configured", "primary_language": value}


def record_confirmation(path: Path, primary_language: str) -> None:
    if not isinstance(primary_language, str) or not primary_language.strip():
        raise ValueError("primary_language must be a non-empty language tag")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "primary_language": primary_language}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
