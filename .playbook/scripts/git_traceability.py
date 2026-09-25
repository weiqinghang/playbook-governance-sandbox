#!/usr/bin/env python3
"""Traceable protected merge helper without a delivery lifecycle manifest."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote


def run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=check)


def project_path(repo_root: Path) -> str:
    remote = run(["git", "remote", "get-url", "origin"], repo_root).stdout.strip()
    if remote.startswith("git@") and ":" in remote:
        return remote.split(":", 1)[1].removesuffix(".git")
    if remote.startswith(("http://", "https://")):
        return remote.split("//", 1)[1].split("/", 1)[1].removesuffix(".git")
    raise ValueError("cannot resolve GitLab project from origin")


def api(repo_root: Path, endpoint: str) -> object:
    return json.loads(run(["glab", "api", endpoint], repo_root).stdout)


def reviewer_pass(notes: list[dict], head_sha: str) -> bool:
    """Recognize the exact-head Reviewer audit comment, not merge authority."""
    for note in notes:
        body = str(note.get("body") or "")
        author = note.get("author") or {}
        if (
            isinstance(author.get("username"), str)
            and author["username"]
            and re.search(r"review_result\s*[:|]\s*review pass", body, re.I)
            and re.search(r"(?im)^Agent:\s*reviewer\s*$", body)
            and re.search(r"(?im)^Instance:\s*reviewer:[^\s]+\s*$", body)
            and re.search(r"(?im)^Via:\s*Codex\s*$", body)
            and head_sha in body
        ):
            return True
    return False


def has_distinct_native_approval(approvals: dict, mr_author: str) -> bool:
    """Return true only for a GitLab-native approval from a different principal."""
    approved_by = approvals.get("approved_by") if isinstance(approvals, dict) else None
    if not isinstance(approved_by, list):
        return False
    for approval in approved_by:
        user = approval.get("user") if isinstance(approval, dict) else None
        username = user.get("username") if isinstance(user, dict) else None
        if isinstance(username, str) and username and username != mr_author:
            return True
    return False


def merge_decision(
    repo_root: Path,
    mr_iid: int,
    governing_issue: int,
    *,
    expected_target: str = "develop",
    require_distinct_native_approval: bool = False,
) -> dict:
    project = project_path(repo_root)
    encoded = quote(project, safe="")
    mr = api(repo_root, f"projects/{encoded}/merge_requests/{mr_iid}")
    if not isinstance(mr, dict):
        raise ValueError("MR readback is not an object")
    if mr.get("state") != "opened" or not mr.get("sha"):
        raise ValueError("MR must be opened with an exact head")
    if mr.get("target_branch") != expected_target or mr.get("source_branch") == mr.get("target_branch"):
        raise ValueError("MR branch identity is invalid")
    if mr.get("merge_status") != "can_be_merged" or mr.get("has_conflicts") is not False:
        raise ValueError("MR mergeability readback is not clean")
    if mr.get("blocking_discussions_resolved") is not True:
        raise ValueError("MR blocking discussions are not resolved")
    description = str(mr.get("description") or "")
    if not re.search(rf"(?<!\w)#{governing_issue}(?!\w)", description):
        raise ValueError("MR must name its governing Issue")
    if re.search(r"(?im)^\s*close\s+scope\s*:\s*none\s*$", description) and mr.get("closes_issues"):
        raise ValueError("Close scope none conflicts with GitLab closes_issues readback")
    author = mr.get("author") or {}
    mr_author = author.get("username") if isinstance(author.get("username"), str) else ""
    if not mr_author:
        raise ValueError("MR author identity is required for reviewer independence")
    notes = api(repo_root, f"projects/{encoded}/merge_requests/{mr_iid}/notes?per_page=100")
    if not isinstance(notes, list) or not reviewer_pass(notes, str(mr["sha"])):
        raise ValueError("missing independent reviewer audit bound to current MR head")
    if require_distinct_native_approval:
        approvals = api(repo_root, f"projects/{encoded}/merge_requests/{mr_iid}/approvals")
        if not has_distinct_native_approval(approvals, mr_author):
            return {
                "decision": "deny",
                "reason": "distinct_native_approval_required",
                "project": project,
                "mr": mr_iid,
                "governing_issue": governing_issue,
                "head_sha": mr["sha"],
                "reviewer_audit": "present",
                "expected_target": expected_target,
            }
    title = " ".join(str(mr.get("title") or "").split())
    return {
        "decision": "allow",
        "project": project,
        "mr": mr_iid,
        "governing_issue": governing_issue,
        "head_sha": mr["sha"],
        "expected_target": expected_target,
        "merge_message": f"merge MR !{mr_iid}: {title} (#{governing_issue})",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.13 protected merge traceability guard")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge-mr")
    merge.add_argument("--mr", type=int, required=True)
    merge.add_argument("--governing-issue", type=int, required=True)
    merge.add_argument("--expected-target", default="develop")
    merge.add_argument(
        "--require-distinct-native-approval",
        action="store_true",
        help="require a GitLab approval from a principal other than the MR author; use only when the action policy requires it",
    )
    merge.add_argument("--dry-run", action="store_true")
    log = sub.add_parser("log-local")
    log.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    root = Path(".").resolve()
    if args.command == "log-local":
        completed = subprocess.run(["git", "log", "--graph", f"--max-count={args.count}", "--date=iso-strict", "--pretty=format:%h %ad %s"], cwd=root)
        return completed.returncode
    try:
        decision = merge_decision(
            root,
            args.mr,
            args.governing_issue,
            expected_target=args.expected_target,
            require_distinct_native_approval=args.require_distinct_native_approval,
        )
        print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
        if decision["decision"] != "allow":
            return 2
        # This helper is preflight-only.  A Supervisor's explicit high-risk
        # authorization must invoke GitLab native merge separately.
        return 0
    except (ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "deny", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
