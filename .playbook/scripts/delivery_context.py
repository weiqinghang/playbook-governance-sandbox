#!/usr/bin/env python3
"""Native Issue precheck for ordinary v0.13 single-owner delivery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = ("## Goal Contract", "## 范围", "## 验收")
ORDINARY_ACTIONS = {"file_mutation", "gitlab_mutation", "commit", "push", "comment"}


def native_issue_precheck(issue: dict[str, Any], action: str) -> dict[str, Any]:
    """Check Issue-native facts only; never parse a lifecycle projection."""
    if action not in ORDINARY_ACTIONS:
        return {"result": "deny_side_effect", "action": action, "reason": "high-risk action needs its dedicated guard"}
    description = str(issue.get("description") or "")
    missing = [section for section in REQUIRED_SECTIONS if section not in description]
    assignees = issue.get("assignees") or []
    labels = issue.get("labels") or []
    workflow = [label for label in labels if isinstance(label, str) and label.startswith("workflow::")]
    if missing:
        return {"result": "deny_side_effect", "action": action, "reason": f"missing Issue sections: {', '.join(missing)}"}
    if len(assignees) != 1:
        return {"result": "deny_side_effect", "action": action, "reason": "Issue must have exactly one assignee"}
    if len(workflow) != 1:
        return {"result": "deny_side_effect", "action": action, "reason": "Issue must have exactly one workflow label"}
    return {"result": "side_effect_candidate", "action": action, "legacy_state_read": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.13 native Issue ordinary-action precheck")
    parser.add_argument("--issue-json", type=Path, required=True)
    parser.add_argument("--action", required=True)
    args = parser.parse_args()
    issue = json.loads(args.issue_json.read_text(encoding="utf-8"))
    result = native_issue_precheck(issue, args.action)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["result"] == "side_effect_candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
