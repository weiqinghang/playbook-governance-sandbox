#!/usr/bin/env python3
"""Read-only audit of files recorded by a downstream .seed-lock.json."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

START = b"<!-- PLAYBOOK-MANAGED:START -->"
END = b"<!-- PLAYBOOK-MANAGED:END -->"
STRATEGIES = {"copy", "managed_block", "copy_if_absent", "manual"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def managed_block(data: bytes) -> bytes | None:
    if data.count(START) != 1 or data.count(END) != 1:
        return None
    start, end = data.index(START), data.index(END)
    if end < start or (start and data[start - 1:start] != b"\n"):
        return None
    if end and data[end - 1:end] != b"\n":
        return None
    for position, marker in ((start, START), (end, END)):
        tail = data[position + len(marker):]
        if tail and not tail.startswith((b"\n", b"\r\n")):
            return None
    end += len(END)
    if data[end:end + 2] == b"\r\n":
        end += 2
    elif data[end:end + 1] == b"\n":
        end += 1
    return data[start:end]


def safe_target(root: Path, name: object) -> Path | None:
    if not isinstance(name, str) or not name or "\\" in name or any(ord(c) < 32 for c in name):
        return None
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(part in {".", "..", ".git"} for part in path.parts):
        return None
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            return None
    if not target.is_relative_to(root):
        return None
    return target


def audit(root: Path) -> dict:
    root = root.resolve()
    result = {"ok": False, "version": None, "checked": 0, "protected": 0,
              "preserved": [], "errors": []}
    lock_path = root / ".seed-lock.json"
    try:
        if lock_path.is_symlink():
            raise OSError("unsafe lock")
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        result["errors"].append({"path": ".seed-lock.json", "reason": "unreadable_lock"})
        return result
    if not isinstance(lock, dict) or not isinstance(lock.get("installed_files"), list) or not lock["installed_files"]:
        result["errors"].append({"path": ".seed-lock.json", "reason": "invalid_inventory"})
        return result
    result["version"] = lock.get("seed_version")
    seen = set()
    for record in lock["installed_files"]:
        if not isinstance(record, dict):
            result["errors"].append({"path": ".seed-lock.json", "reason": "invalid_record"})
            continue
        name, strategy, expected = (record.get(key) for key in ("target_name", "strategy", "target_sha256"))
        source_hash = record.get("source_sha256")
        executable = record.get("executable")
        target = safe_target(root, name)
        if target is None or name == ".seed-lock.json" or name in seen or strategy not in STRATEGIES or not (
            isinstance(expected, str) and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected)
        ) or not (
            isinstance(source_hash, str) and len(source_hash) == 64
            and all(c in "0123456789abcdef" for c in source_hash)
        ) or (strategy in {"copy", "managed_block"} and expected != source_hash) or (
            strategy == "managed_block" and name != "AGENTS.md"
        ) or (strategy in {"copy", "managed_block"} and not isinstance(executable, bool)) or (
            executable is not None and not isinstance(executable, bool)
        ):
            result["errors"].append({"path": str(name), "reason": "invalid_record"})
            continue
        seen.add(name)
        if not target.is_file():
            result["errors"].append({"path": name, "reason": "missing_or_unsafe_file"})
            continue
        try:
            data = target.read_bytes()
        except OSError:
            result["errors"].append({"path": name, "reason": "unreadable_file"})
            continue
        owned = managed_block(data) if strategy == "managed_block" else data
        if owned is None:
            result["errors"].append({"path": name, "reason": "invalid_managed_block"})
            continue
        actual = sha256(owned)
        result["checked"] += 1
        if strategy in {"copy", "managed_block"}:
            result["protected"] += 1
            if actual != expected:
                result["errors"].append({"path": name, "reason": "managed_drift"})
            if isinstance(executable, bool) and bool(target.stat().st_mode & 0o111) != executable:
                result["errors"].append({"path": name, "reason": "executable_drift"})
        elif actual != expected:
            result["preserved"].append({"path": name, "reason": "project_content_differs_from_lock"})
    result["ok"] = not result["errors"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="downstream repository root")
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
