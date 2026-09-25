#!/usr/bin/env python3
"""Lean Core primitives for v0.13.0.

This module deliberately has no GitLab mutation, lock acquisition, profile, receipt,
claim, lease, or runtime-log dependency.  It provides only a read-only legacy import
and evidence validation for actions which remain intrinsically high risk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LEGACY_VERSION = "0.12.3"
HIGH_RISK_ACTIONS = {
    "protected_merge",
    "annotated_tag_release",
    "permission_security_credential",
    "data_schema_migration",
    "cross_repo_write",
}
ORDINARY_ACTIONS = {"file", "comment", "commit", "push"}


class LeanCoreError(ValueError):
    """A deliberately narrow, human-readable fail-closed error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_file(path: Path, *, required: bool = False) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            raise LeanCoreError(f"required legacy metadata is missing: {path.name}")
        return None
    if not path.is_file() or path.is_symlink():
        raise LeanCoreError(f"legacy metadata must be a regular file: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LeanCoreError(f"invalid JSON in legacy metadata: {path.name}") from exc
    if not isinstance(value, dict):
        raise LeanCoreError(f"legacy metadata must be an object: {path.name}")
    return value


def import_v0123_metadata(target_root: Path, *, write: bool = False) -> dict[str, Any]:
    """Return diagnostic input from an existing v0.12.3 installation.

    The importer intentionally never materializes, refreshes, converts, or writes
    state.  ``write`` exists only so callers can be rejected explicitly rather than
    accidentally treating this utility as an upgrade command.
    """
    if write:
        raise LeanCoreError("legacy importer is read-only; write is not supported")
    root = target_root.resolve()
    lock_path = root / ".seed-lock.json"
    lock = _json_file(lock_path, required=True)
    version = lock.get("seed_version") or lock.get("version")
    if version != LEGACY_VERSION:
        raise LeanCoreError(f"unsupported legacy version: {version!r}; expected {LEGACY_VERSION}")
    source_commit = lock.get("source_commit") or lock.get("commit")
    if not isinstance(source_commit, str) or len(source_commit) < 7:
        raise LeanCoreError("legacy lock has no usable source_commit")

    activation_path = root / ".playbook" / "config" / "delivery-governance-activation.json"
    overlay_path = root / ".seed-overrides.json"
    activation = _json_file(activation_path)
    overlay = _json_file(overlay_path)
    diagnostics: list[str] = []
    if activation is None:
        diagnostics.append("activation_record_absent")
    if overlay is None:
        diagnostics.append("overlay_absent")

    return {
        "recognized_version": LEGACY_VERSION,
        "source_commit": source_commit,
        "lock_sha256": sha256_file(lock_path),
        "activation_state": "present" if activation is not None else "absent",
        "activation_sha256": sha256_file(activation_path) if activation is not None else None,
        "rollback_ref": lock.get("source_tag") or lock.get("tag") or None,
        "overlay_classification": "present" if overlay is not None else "absent",
        "overlay_sha256": sha256_file(overlay_path) if overlay is not None else None,
        "diagnostics": diagnostics,
        "read_only": True,
    }


def ordinary_mutation_candidate(action: str) -> dict[str, Any]:
    if action not in ORDINARY_ACTIONS:
        raise LeanCoreError(f"not an ordinary action: {action}")
    return {"action": action, "decision": "candidate", "legacy_state_read": False}


def evaluate_high_risk_action(action: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Deny high-risk actions until an action-specific native verifier runs.

    Caller-provided strings are deliberately not evidence: treating a timestamp,
    a permission prefix, or a rollback label as proof would let an implementer
    forge a release/merge/migration approval.  The retained protected-merge
    verifier lives in ``git_traceability.py``; the remaining four categories have
    no generic verifier because their target systems differ, and therefore fail
    closed rather than inventing a second lifecycle controller.
    """
    if action not in HIGH_RISK_ACTIONS:
        return {"action": action, "decision": "deny", "reason": "unknown_high_risk_action"}
    verifier = {
        "protected_merge": "git_traceability.merge_decision",
        "annotated_tag_release": "native annotated-tag and Release readback",
        "permission_security_credential": "target-system permission/security verifier",
        "data_schema_migration": "schema target and rollback verifier",
        "cross_repo_write": "source/target identity and rollback verifier",
    }[action]
    return {
        "action": action,
        "decision": "deny",
        "reason": "action_specific_verifier_required",
        "required_verifier": verifier,
        "legacy_state_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.13 Lean Core helpers")
    subcommands = parser.add_subparsers(dest="command", required=True)
    importer = subcommands.add_parser("import-legacy")
    importer.add_argument("--target", type=Path, required=True)
    importer.add_argument("--write", action="store_true")
    guard = subcommands.add_parser("guard")
    guard.add_argument("--action", required=True)
    guard.add_argument("--evidence-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "import-legacy":
            result = import_v0123_metadata(args.target, write=args.write)
        else:
            payload = json.loads(args.evidence_json.read_text(encoding="utf-8"))
            result = evaluate_high_risk_action(args.action, payload)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("decision", "allow") != "deny" else 2
    except (LeanCoreError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "deny", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
