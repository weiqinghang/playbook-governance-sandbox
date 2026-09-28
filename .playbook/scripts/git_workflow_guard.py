#!/usr/bin/env python3
"""Branch and Issue traceability guard for ordinary commit and push actions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


PROTECTED = {"develop", "main", "master"}


def branch(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo_root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def evaluate(action: str, current_branch: str, allow_protected: bool, issue: str | None = None, message: str | None = None, branch_only: bool = False) -> dict:
    if action not in {"commit", "push"}:
        return {"decision": "deny", "reason": "unsupported ordinary action"}
    if current_branch in PROTECTED and not allow_protected:
        return {"decision": "deny", "reason": "protected branch requires explicit --allow-protected"}
    if not current_branch:
        return {"decision": "deny", "reason": "detached HEAD cannot receive ordinary mutation"}
    if branch_only:
        return {"decision": "allow", "action": action, "branch": current_branch, "legacy_state_read": False}
    if not issue or not re.fullmatch(r"[1-9][0-9]*", issue):
        return {"decision": "deny", "reason": "positive governing Issue IID is required"}
    if action == "commit":
        if not message:
            return {"decision": "deny", "reason": "commit message is required"}
        subject = message.splitlines()[0].strip()
        match = re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*(?:\([^()]+\))?: .+ \((?P<refs>#[1-9][0-9]*(?:, #[1-9][0-9]*)*)\)", subject)
        if not match:
            return {"decision": "deny", "reason": "commit subject must be type(scope): summary (#issue...)"}
        refs = re.findall(r"#([1-9][0-9]*)", match.group("refs"))
        if issue not in refs:
            return {"decision": "deny", "reason": "commit subject does not reference governing Issue"}
    return {"decision": "allow", "action": action, "branch": current_branch, "legacy_state_read": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="ordinary Git branch and Issue traceability guard")
    parser.add_argument("--action", choices=("commit", "push"))
    parser.add_argument("--issue", help="Required governing Issue IID; not an authorization projection.")
    parser.add_argument("--message-file", type=Path, help="Exact proposed commit message file; required for commit.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--allow-protected", action="store_true")
    parser.add_argument("--branch-only", action="store_true")
    args = parser.parse_args()
    message = args.message_file.read_text(encoding="utf-8") if args.message_file else None
    result = evaluate(args.action or "commit", branch(args.repo_root), args.allow_protected, args.issue, message, args.branch_only)
    result["issue"] = args.issue
    result["mode"] = "branch_only" if args.branch_only else "ordinary"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["decision"] == "allow" else 2


if __name__ == "__main__":
    raise SystemExit(main())
