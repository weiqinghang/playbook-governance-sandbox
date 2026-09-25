#!/usr/bin/env python3
"""Branch and Issue traceability guard for ordinary commit and push actions."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from urllib.parse import quote, urlparse
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


MICRO_CONDITIONS = (
    "single_repo_local_reversible", "authorized_clear_scope_and_verification",
    "presentation_only", "no_business_or_contract_change", "no_shared_component_change",
)


def execution_decision(*, current_branch, default_branch, protected_branches, issue,
                       route="standard", action="file_mutation", micro=None):
    """Admission uses current native facts, not a cached conversation mode or receipt."""
    def deny(reason):
        return {"decision": "deny", "reason": reason}
    if action not in {"file_mutation", "commit", "push"}:
        return deny("unsupported execution action")
    if not default_branch or not isinstance(protected_branches, list):
        return deny("remote branch policy unavailable")
    if not current_branch or current_branch == default_branch or current_branch in PROTECTED:
        return deny("create a work branch before the first persistent edit")
    if any(fnmatch.fnmatchcase(current_branch, pattern) for pattern in protected_branches):
        return deny("current branch is protected")
    if route == "micro_direct":
        if not isinstance(micro, dict) or any(micro.get(key) is not True for key in MICRO_CONDITIONS):
            return deny("micro_direct requires all bounded admission conditions")
    elif route != "standard":
        return deny("unknown execution route")
    if route == "standard" or issue is not None:
        if not isinstance(issue, dict) or issue.get("state") not in {"open", "opened"}:
            return deny("open governing Issue required before implementation")
        if len(issue.get("assignees") or []) != 1:
            return deny("Issue must have exactly one assignee")
        labels = [v.get("name") if isinstance(v, dict) else v for v in issue.get("labels", [])]
        workflow = [v for v in labels if isinstance(v, str) and v.startswith("workflow::")]
        if len(workflow) != 1 or workflow[0] not in {
            "workflow::ready", "workflow::doing", "workflow::verify", "workflow::writeback"
        }:
            return deny("Issue is not in a single executable workflow state")
        maturity = [v for v in labels if isinstance(v, str) and v.startswith("backlog::")]
        if maturity != ["backlog::ready-for-dev"]:
            return deny("Issue must be ready-for-dev before implementation")
        body = issue.get("description") or issue.get("body") or ""
        for heading in ("Goal Contract", "范围", "验收"):
            match = re.search(r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
            if not match or not match.group(1).strip():
                return deny("Issue requires nonempty goal, scope and acceptance")
    return {"decision": "allow", "action": action, "branch": current_branch,
            "route": route, "legacy_state_read": False}


def _api(command, endpoint, repo_root):
    result = subprocess.run([command, "api", endpoint], cwd=repo_root, check=True,
                            capture_output=True, text=True)
    return json.loads(result.stdout)


def live_execution_check(repo_root, issue_number, route, action, micro=None):
    """Read origin, native project policy and Issue immediately before admission."""
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_root,
                            check=True, capture_output=True, text=True).stdout.strip()
    if "://" in remote:
        parsed = urlparse(remote)
        host, path = parsed.hostname, parsed.path.lstrip("/")
    else:
        match = re.fullmatch(r"(?:[^@]+@)?([^:]+):(.+)", remote)
        if not match:
            raise ValueError("unsupported origin URL")
        host, path = match.groups()
    path = path.removesuffix(".git")
    if not host or not path or (issue_number and not str(issue_number).isdigit()):
        raise ValueError("invalid repository or Issue identity")
    if host == "github.com":
        base = "repos/" + path
        project = _api("gh", base, repo_root)
        if project.get("full_name", "").lower() != path.lower():
            raise ValueError("repository identity mismatch")
        current = branch(repo_root)
        # New local work branches need not exist remotely. Read applicable rules
        # and classic protection patterns without fetching a nonexistent branch.
        rules = _api("gh", base + "/rules/branches/" + quote(current, safe=""), repo_root) if current else []
        if not isinstance(rules, list):
            raise ValueError("invalid branch rules")
        protected = [current] if rules else []
        owner, name = path.split("/", 1)
        cursor = None
        while True:
            query = """query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){
              branchProtectionRules(first:100,after:$cursor){nodes{pattern} pageInfo{hasNextPage endCursor}}}}"""
            r = subprocess.run(["gh", "api", "graphql", "--input", "-"], cwd=repo_root,
                input=json.dumps({"query": query, "variables": {"owner": owner, "name": name, "cursor": cursor}}),
                capture_output=True, text=True, check=True)
            payload = json.loads(r.stdout)
            if payload.get("errors"):
                raise ValueError("branch protection read failed")
            page = payload["data"]["repository"]["branchProtectionRules"]
            protected.extend(row["pattern"] for row in page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
        issue = _api("gh", base + "/issues/" + str(issue_number), repo_root) if issue_number else None
        if issue and "pull_request" in issue:
            raise ValueError("governing object must be an Issue, not a PR")
    else:
        base = "projects/" + quote(path, safe="")
        project = _api("glab", base, repo_root)
        if project.get("path_with_namespace") != path:
            raise ValueError("repository identity mismatch")
        current = branch(repo_root)
        protected = []
        page = 1
        while True:
            rows = _api("glab", base + f"/protected_branches?per_page=100&page={page}", repo_root)
            if not isinstance(rows, list):
                raise ValueError("invalid protected branches response")
            protected.extend(row["name"] for row in rows)
            if len(rows) < 100:
                break
            page += 1
        issue = _api("glab", base + "/issues/" + str(issue_number), repo_root) if issue_number else None
    return execution_decision(current_branch=current, default_branch=project.get("default_branch"),
                              protected_branches=protected, issue=issue, route=route,
                              action=action, micro=micro)


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue-native execution admission and Git branch guard")
    parser.add_argument("--action", choices=("file_mutation", "commit", "push"))
    parser.add_argument("--issue", help="Governing Issue number")
    parser.add_argument("--message-file", type=Path, help="Exact proposed commit message file; required for commit")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--allow-protected", action="store_true")
    parser.add_argument("--branch-only", action="store_true", help="Diagnostic only; not execution admission")
    parser.add_argument("--route", choices=("standard", "micro_direct"), default="standard")
    parser.add_argument("--micro-evidence", type=Path)
    args = parser.parse_args()
    try:
        current = branch(args.repo_root)
        if args.branch_only:
            result = evaluate(args.action or "commit", current, args.allow_protected,
                              args.issue, branch_only=True)
            result["mode"] = "diagnostic_only"
        elif args.action == "file_mutation":
            if args.allow_protected:
                result = {"decision": "deny", "reason": "protected override is not first-write admission"}
            else:
                micro = json.loads(args.micro_evidence.read_text()) if args.micro_evidence else None
                result = live_execution_check(args.repo_root, args.issue, args.route, "file_mutation", micro)
        else:
            message = args.message_file.read_text(encoding="utf-8") if args.message_file else None
            result = evaluate(args.action or "commit", current, args.allow_protected,
                              args.issue, message)
            if result["decision"] == "allow" and not args.allow_protected:
                micro = json.loads(args.micro_evidence.read_text()) if args.micro_evidence else None
                result = live_execution_check(args.repo_root, args.issue, args.route,
                                              args.action or "commit", micro)
        result["issue"] = args.issue
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError):
        result = {"decision": "deny", "reason": "fresh repository policy or Issue readback failed"}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["decision"] == "allow" else 2


if __name__ == "__main__":
    raise SystemExit(main())
