#!/usr/bin/env python3
"""Validate and render sparse delivery evidence without persisting task state."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


LAYER_ORDER = (
    "artifact_implementation",
    "automated_tests",
    "independent_reviewer",
    "commit_mr_exact_head",
    "merge_closeout",
    "migration_deploy",
    "health_smoke",
    "logs_runtime_observation",
    "acceptance",
)

STATUSES = {"proven", "not_proven", "failed", "blocked", "not_applicable"}
ACCEPTANCE_SUBTYPES = {"business_uat", "product_acceptance", "operational_acceptance"}

PROFILE_LAYERS = {
    "micro_local": LAYER_ORDER[:2],
    "reviewed_candidate": LAYER_ORDER[:4],
    "ordinary_repository": LAYER_ORDER[:5],
    "full_runtime": LAYER_ORDER,
}

EVIDENCE_KINDS = {
    "artifact_implementation": {"file", "diff", "artifact"},
    "automated_tests": {"test", "build"},
    "independent_reviewer": {"reviewer_comment"},
    "commit_mr_exact_head": {"commit", "mr"},
    "merge_closeout": {"merge_readback", "issue_closeout"},
    "migration_deploy": {"migration", "deployment"},
    "health_smoke": {"health_check", "smoke"},
    "logs_runtime_observation": {"elk_query", "runtime_observation"},
    "acceptance": ACCEPTANCE_SUBTYPES,
}

REQUIRED_BINDINGS = {
    "artifact_implementation": {"head"},
    "automated_tests": {"head"},
    "independent_reviewer": {"mr_exact_head"},
    "commit_mr_exact_head": {"head", "mr_exact_head"},
    "merge_closeout": {"mr_exact_head"},
    "migration_deploy": {"deployment_version", "environment"},
    "health_smoke": {"deployment_version", "environment"},
    "logs_runtime_observation": {"deployment_version", "environment"},
    "acceptance": {"deployment_version", "environment", "acceptance_object"},
}

FACT_CHANGE_IMPACT = {
    "head": {
        "artifact_implementation",
        "automated_tests",
        "independent_reviewer",
        "commit_mr_exact_head",
    },
    "mr_exact_head": {"independent_reviewer", "commit_mr_exact_head", "merge_closeout"},
    "deployment_version": {
        "migration_deploy",
        "health_smoke",
        "logs_runtime_observation",
        "acceptance",
    },
    "environment": {
        "migration_deploy",
        "health_smoke",
        "logs_runtime_observation",
        "acceptance",
    },
    "acceptance_object": {"acceptance"},
}


def _is_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _consumed_evidence_binding(
    evidence: Any,
    *,
    expected_result: str,
    binding_fields: tuple[str, ...],
) -> str | None:
    """Return the first applicable exact-head binding for consumed evidence."""

    if not isinstance(evidence, dict):
        return None
    if not _nonempty(evidence.get("ref")) or evidence.get("result") != expected_result:
        return None
    if not _is_timestamp(evidence.get("observed_at")):
        return None
    bindings = evidence.get("bindings")
    if not isinstance(bindings, dict):
        return None
    return next(
        (bindings[field] for field in binding_fields if _nonempty(bindings.get(field))),
        None,
    )


def validate_report(report: dict[str, Any]) -> list[str]:
    """Return deterministic semantic errors for one in-memory evidence report."""

    errors: list[str] = []
    profile = report.get("applicability_profile")
    if profile not in PROFILE_LAYERS:
        errors.append(f"applicability_profile must be one of {sorted(PROFILE_LAYERS)}")
        required_layers: set[str] = set()
    else:
        required_layers = set(PROFILE_LAYERS[profile])

    layers = report.get("layers")
    if not isinstance(layers, list):
        return errors + ["layers must be an array"]

    by_id: dict[str, dict[str, Any]] = {}
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"layers[{index}] must be an object")
            continue
        layer_id = layer.get("layer")
        if layer_id not in LAYER_ORDER:
            errors.append(f"layers[{index}].layer is not in the closed taxonomy")
            continue
        if layer_id in by_id:
            errors.append(f"duplicate layer: {layer_id}")
            continue
        by_id[layer_id] = layer

        status = layer.get("status")
        if status not in STATUSES:
            errors.append(f"{layer_id}.status must be one of {sorted(STATUSES)}")
            continue
        if layer_id in required_layers and status == "not_applicable":
            errors.append(f"required layer {layer_id} cannot be not_applicable")

        if layer_id == "acceptance" and status != "not_applicable":
            subtype = layer.get("acceptance_subtype")
            if subtype not in ACCEPTANCE_SUBTYPES:
                errors.append(f"acceptance.acceptance_subtype must be one of {sorted(ACCEPTANCE_SUBTYPES)}")

        if status == "proven":
            evidence = layer.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{layer_id}.proven requires locatable evidence")
                continue
            for evidence_index, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(f"{layer_id}.evidence[{evidence_index}] must be an object")
                    continue
                kind = item.get("kind")
                if kind not in EVIDENCE_KINDS[layer_id]:
                    errors.append(f"evidence kind {kind!r} cannot prove {layer_id}")
                if not _nonempty(item.get("ref")):
                    errors.append(f"{layer_id}.evidence[{evidence_index}].ref must be locatable")
                if not _is_timestamp(item.get("observed_at")):
                    errors.append(f"{layer_id}.evidence[{evidence_index}].observed_at must include timezone")
                bindings = item.get("bindings")
                if not isinstance(bindings, dict):
                    errors.append(f"{layer_id}.evidence[{evidence_index}].bindings must be an object")
                else:
                    missing_bindings = {
                        field for field in REQUIRED_BINDINGS[layer_id] if not _nonempty(bindings.get(field))
                    }
                    if missing_bindings:
                        errors.append(
                            f"{layer_id}.evidence[{evidence_index}] missing fact bindings: "
                            f"{sorted(missing_bindings)}"
                        )
            if layer_id == "acceptance" and any(
                item.get("kind") != layer.get("acceptance_subtype")
                for item in evidence
                if isinstance(item, dict)
            ):
                errors.append("acceptance evidence kind must match acceptance_subtype")
            if "owner" in layer or "next_action" in layer:
                errors.append(f"{layer_id}.proven must not retain owner or next_action")
        elif status in {"not_proven", "failed", "blocked"}:
            if not _nonempty(layer.get("owner")) or not _nonempty(layer.get("next_action")):
                errors.append(f"{layer_id}.{status} requires current owner and next_action")
        else:
            if not _nonempty(layer.get("reason")):
                errors.append(f"{layer_id}.not_applicable requires an auditable reason")
            if "owner" in layer or "next_action" in layer:
                errors.append(f"{layer_id}.not_applicable must not include owner or next_action")
            if "evidence" in layer:
                errors.append(f"{layer_id}.not_applicable must not carry proof evidence")

    missing_required = required_layers - set(by_id)
    for layer_id in sorted(missing_required, key=LAYER_ORDER.index):
        errors.append(f"profile {profile} requires layer {layer_id}")

    scope = report.get("profile_scope")
    scoped_out: set[str] = set()
    if scope is not None:
        if not isinstance(scope, dict):
            errors.append("profile_scope must be an object")
        else:
            raw_layers = scope.get("not_applicable_layers")
            if not isinstance(raw_layers, list) or not raw_layers:
                errors.append("profile_scope.not_applicable_layers must be a non-empty array")
            else:
                scoped_out = set(raw_layers)
                if len(scoped_out) != len(raw_layers):
                    errors.append("profile_scope.not_applicable_layers contains duplicates")
                unknown = scoped_out - set(LAYER_ORDER)
                if unknown:
                    errors.append(f"profile_scope contains unknown layers: {sorted(unknown)}")
                overlap = scoped_out & set(by_id)
                if overlap:
                    errors.append(f"profile_scope duplicates rendered layers: {sorted(overlap)}")
                applicable_overlap = scoped_out & required_layers
                if applicable_overlap:
                    errors.append(f"profile_scope cannot hide applicable layers: {sorted(applicable_overlap)}")
            if not _nonempty(scope.get("reason")):
                errors.append("profile_scope requires an auditable reason")
            if "owner" in scope or "next_action" in scope:
                errors.append("profile_scope must not invent owner or next_action")

    uncovered = set(LAYER_ORDER) - set(by_id) - scoped_out
    if uncovered:
        errors.append(f"layers must be rendered or covered once by profile_scope: {sorted(uncovered)}")

    claim = report.get("completion_claim")
    if not isinstance(claim, dict):
        errors.append("completion_claim must be an object")
        return errors
    claim_status = claim.get("status")
    if claim_status not in {"complete", "incomplete", "blocked"}:
        errors.append("completion_claim.status must be complete, incomplete, or blocked")
    readback = claim.get("fresh_readback")
    if not isinstance(readback, dict) or not _nonempty(readback.get("source")) or not _is_timestamp(readback.get("observed_at")):
        errors.append("completion_claim requires locatable fresh_readback source and observed_at")

    for field in ("unfinished_items", "blockers", "residual_risks"):
        if not isinstance(claim.get(field), list):
            errors.append(f"completion_claim.{field} must be an array")

    unresolved = [
        layer_id
        for layer_id, layer in by_id.items()
        if layer.get("status") not in {"proven", "not_applicable"}
    ]
    required_not_proven = [
        layer_id for layer_id in required_layers if by_id.get(layer_id, {}).get("status") != "proven"
    ]
    if claim_status == "complete":
        if required_not_proven or unresolved:
            errors.append("completion_claim.complete requires every applicable rendered layer proven")
        if claim.get("unfinished_items") or claim.get("blockers"):
            errors.append("completion_claim.complete cannot retain unfinished_items or blockers")
    elif unresolved and not claim.get("unfinished_items"):
        errors.append("incomplete or blocked claim must list unfinished_items")
    if claim_status == "blocked" and not claim.get("blockers"):
        errors.append("completion_claim.blocked requires blockers")

    return errors


def render_report(report: dict[str, Any]) -> str:
    """Render only selected layers plus one compact profile scope summary."""

    errors = validate_report(report)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = {item["layer"]: item for item in report["layers"]}
    lines = [f"profile: {report['applicability_profile']}"]
    for layer_id in LAYER_ORDER:
        if layer_id in by_id:
            layer = by_id[layer_id]
            lines.append(f"{layer_id}: {layer['status']}")
    scope = report.get("profile_scope")
    if scope:
        lines.append(f"scope_out: {len(scope['not_applicable_layers'])} upper layers — {scope['reason']}")
    lines.append(f"claim: {report['completion_claim']['status']}")
    return "\n".join(lines)


def invalidate_for_fact_changes(
    report: dict[str, Any],
    changes: set[str],
    *,
    owner: str,
    next_action: str,
    blocked: bool = False,
) -> dict[str, Any]:
    """Return a copy with only fact-affected proofs downgraded; no TTL is used."""

    unknown = set(changes) - set(FACT_CHANGE_IMPACT)
    if unknown:
        raise ValueError(f"unknown fact changes: {sorted(unknown)}")
    affected: set[str] = set()
    for change in changes:
        affected.update(FACT_CHANGE_IMPACT[change])

    result = copy.deepcopy(report)
    invalidated: list[str] = []
    for layer in result.get("layers", []):
        if layer.get("layer") not in affected or layer.get("status") != "proven":
            continue
        invalidated.append(layer["layer"])
        layer["stale_evidence"] = layer.pop("evidence", [])
        layer["status"] = "blocked" if blocked else "not_proven"
        layer["owner"] = owner
        layer["next_action"] = next_action

    if invalidated:
        claim = result.setdefault("completion_claim", {})
        claim["status"] = "blocked" if blocked else "incomplete"
        claim["unfinished_items"] = sorted(
            set(claim.get("unfinished_items", [])) | set(invalidated), key=LAYER_ORDER.index,
        )
        if blocked:
            claim["blockers"] = list(claim.get("blockers", [])) or [next_action]
    return result


def aggregate_group(group: dict[str, Any]) -> dict[str, Any]:
    """Aggregate required branches without allowing one success to cover another."""

    raw_required = group.get("required_branch_ids")
    invalid_required = (
        not isinstance(raw_required, list)
        or not raw_required
        or any(not _nonempty(branch_id) for branch_id in raw_required)
        or len(raw_required) != len(set(raw_required))
    )
    required = [
        branch_id for branch_id in raw_required or [] if _nonempty(branch_id)
    ] if isinstance(raw_required, list) else []
    raw_branches = group.get("branches", [])
    duplicate_required = len(required) != len(set(required))
    branch_ids = [
        branch.get("id") for branch in raw_branches if isinstance(branch, dict) and isinstance(branch.get("id"), str)
    ] if isinstance(raw_branches, list) else []
    duplicate_branches = sorted({branch_id for branch_id in branch_ids if branch_ids.count(branch_id) > 1})
    branches = {
        branch.get("id"): branch
        for branch in raw_branches
        if isinstance(branch, dict) and isinstance(branch.get("id"), str)
    } if isinstance(raw_branches, list) else {}
    missing = [branch_id for branch_id in required if branch_id not in branches]
    unconsumed_returns: list[str] = []
    unconsumed_reviewers: list[str] = []
    invalid_return_evidence: list[str] = []
    invalid_reviewer_evidence: list[str] = []
    mismatched_evidence_bindings: list[str] = []
    incomplete_evidence: list[str] = []
    invalid_evidence: dict[str, list[str]] = {}

    for branch_id in required:
        branch = branches.get(branch_id)
        if branch is None:
            continue
        if branch.get("return_consumed") is not True:
            unconsumed_returns.append(branch_id)
            return_head = None
        else:
            return_head = _consumed_evidence_binding(
                branch.get("return_evidence"),
                expected_result="accepted",
                binding_fields=("head",),
            )
            if return_head is None:
                invalid_return_evidence.append(branch_id)
        if branch.get("reviewer_consumed") is not True:
            unconsumed_reviewers.append(branch_id)
            reviewer_head = None
        else:
            reviewer_head = _consumed_evidence_binding(
                branch.get("reviewer_evidence"),
                expected_result="pass",
                binding_fields=("mr_exact_head", "head"),
            )
            if reviewer_head is None:
                invalid_reviewer_evidence.append(branch_id)
        if return_head is not None and reviewer_head is not None and return_head != reviewer_head:
            mismatched_evidence_bindings.append(branch_id)
        report = branch.get("evidence_report")
        if not isinstance(report, dict):
            invalid_evidence[branch_id] = ["evidence_report must be an object"]
            continue
        report_errors = validate_report(report)
        if report_errors:
            invalid_evidence[branch_id] = report_errors
        elif report.get("completion_claim", {}).get("status") != "complete":
            incomplete_evidence.append(branch_id)

    complete = not any(
        (
            duplicate_required,
            invalid_required,
            duplicate_branches,
            missing,
            unconsumed_returns,
            unconsumed_reviewers,
            invalid_return_evidence,
            invalid_reviewer_evidence,
            mismatched_evidence_bindings,
            incomplete_evidence,
            invalid_evidence,
        )
    )
    return {
        "complete": complete,
        "status": "completed" if complete else "blocked",
        "invalid_required_branch_ids": invalid_required,
        "duplicate_required_branch_ids": duplicate_required,
        "duplicate_branch_ids": duplicate_branches,
        "missing_branches": missing,
        "unconsumed_returns": unconsumed_returns,
        "unconsumed_reviewers": unconsumed_reviewers,
        "invalid_return_evidence": invalid_return_evidence,
        "invalid_reviewer_evidence": invalid_reviewer_evidence,
        "mismatched_evidence_bindings": mismatched_evidence_bindings,
        "incomplete_evidence": incomplete_evidence,
        "invalid_evidence": invalid_evidence,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render", "aggregate"):
        child = subparsers.add_parser(command)
        child.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.path.read_text(encoding="utf-8"))

    if args.command == "validate":
        errors = validate_report(payload)
        print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if args.command == "render":
        try:
            print(render_report(payload))
        except ValueError as exc:
            print(str(exc))
            return 1
        return 0
    result = aggregate_group(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
