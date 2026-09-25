#!/usr/bin/env python3
"""Pure Supervisor/Executor route decisions plus guarded user-local persistence.

The caller supplies fresh host capabilities and task-adequacy evidence. Selection
does not launch a task; verify_readback must match the launched task before its
side effects. A process-local capability verifies resolver handoff, not user
consent or host dispatch. Repository defaults are never written by this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any


ROLES = ("supervisor", "executor")
LEGACY_KEYS = {"supervisor": "supervision", "executor": "ordinary_implementation"}
ROUTE_KEYS = frozenset(("primary", "after_primary_max", "availability_fallback"))
_DISPATCH_KEY = secrets.token_bytes(32)
_CONFIRMATION_SCOPES = frozenset(("repository_default", "confirmed_user_local", "this_task"))


def _validate_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"unsupported role: {role}")


def _validate_route(route: Any) -> None:
    if not isinstance(route, dict) or set(route) - ROUTE_KEYS:
        raise ValueError("route must contain only primary, after_primary_max and availability_fallback")
    if not isinstance(route.get("primary"), list) or not route["primary"]:
        raise ValueError("route.primary must be a nonempty list")
    for key in ROUTE_KEYS:
        steps = route.get(key, [])
        if not isinstance(steps, list):
            raise ValueError(f"route.{key} must be a list")
        for step in steps:
            if (not isinstance(step, dict) or set(step) != {"model", "effort"}
                    or not all(isinstance(step[k], str) and step[k] for k in ("model", "effort"))):
                raise ValueError(f"route.{key} has an invalid model/effort step")
    all_steps = [json.dumps(step, sort_keys=True) for key in ROUTE_KEYS for step in route.get(key, [])]
    if len(all_steps) != len(set(all_steps)):
        raise ValueError("route has duplicate model/effort steps")


def _legacy_candidate(role: str, local: dict[str, Any]) -> dict[str, Any] | None:
    preferences = local.get("starting_preferences", {})
    if not isinstance(preferences, dict):
        raise ValueError("local starting_preferences must be an object")
    preference = preferences.get(LEGACY_KEYS[role])
    if preference is None:
        return None
    if not isinstance(preference, dict):
        raise ValueError("legacy local role preference must be an object")
    candidate = {"primary": [{"model": preference.get("model"), "effort": preference.get("effort")}]}
    _validate_route(candidate)
    return candidate


def route_digest(route: dict[str, Any]) -> str:
    """Stable snapshot identifier for an exact route; safe against later mutation."""
    _validate_route(route)
    encoded = json.dumps(route, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dispatch_capability(scope: str, role: str, task_ref: str | None,
                         source: str, digest: str) -> str:
    binding = {"scope": scope, "role": role, "task_ref": task_ref,
               "source": source, "route_digest": digest}
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(_DISPATCH_KEY, encoded, hashlib.sha256).hexdigest()


def _ready_resolution(scope: str, role: str, task_ref: str | None,
                      source: str, route: dict[str, Any]) -> dict[str, Any]:
    digest = route_digest(route)
    return {"status": "ready", "role": role, "task_ref": task_ref,
            "source": source, "confirmation_scope": scope, "route": route,
            "route_digest": digest,
            "dispatch_capability": _dispatch_capability(scope, role, task_ref, source, digest)}


def _confirmation_matches(
    scope: str, role: str, task_ref: str | None, candidate: dict[str, Any],
    confirmation: dict[str, Any] | None,
) -> bool:
    """Require an actual user choice tied to this role, task and exact route."""
    if confirmation is None:
        return False
    if not isinstance(confirmation, dict):
        raise ValueError("confirmation must bind scope, role, task_ref and exact candidate digest")
    return (
        isinstance(task_ref, str) and bool(task_ref.strip())
        and set(confirmation) == {"scope", "role", "task_ref", "candidate_digest", "evidence_ref"}
        and confirmation["scope"] == scope
        and confirmation["role"] == role
        and confirmation["task_ref"] == task_ref
        and confirmation["candidate_digest"] == route_digest(candidate)
        and isinstance(confirmation["evidence_ref"], str)
        and bool(confirmation["evidence_ref"].strip())
    )


def resolve_role(
    role: str,
    defaults: dict[str, Any],
    local: dict[str, Any] | None = None,
    *,
    task_choice: dict[str, Any] | None = None,
    task_ref: str | None = None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a role route or a confirmation request before affected dispatch.

    An explicit ``this_task`` confirmation binds role, task_ref and exact route.
    A future choice uses ``persist_user_role`` with a similarly bound record.
    Existing generic v2 preferences are unconfirmed candidates for S/E roles.
    """
    _validate_role(role)
    if confirmation is not None and not isinstance(confirmation, dict):
        raise ValueError("confirmation must bind scope, role, task_ref and exact candidate digest")
    base = defaults["supervisor_executor_roles"][role]
    _validate_route(base)
    if local is None:
        local = {}
    if not isinstance(local, dict):
        raise ValueError("local config must be an object")
    if local.get("ownership", "user_managed") != "user_managed":
        raise ValueError("local model routing config is not user-managed")
    role_routes = local.get("supervisor_executor_roles", {})
    if not isinstance(role_routes, dict):
        raise ValueError("local supervisor_executor_roles must be an object")
    confirmations = local.get("supervisor_executor_confirmed", {})
    if not isinstance(confirmations, dict):
        raise ValueError("local supervisor_executor_confirmed must be an object")

    if role in role_routes:
        local_candidate = role_routes[role]
        local_source = "local_role"
        _validate_route(local_candidate)
    else:
        local_candidate = _legacy_candidate(role, local)
        local_source = "legacy_local" if local_candidate is not None else None
    local_confirmed = (local_source == "local_role"
                       and confirmations.get(role) == local_candidate)

    candidate = None
    source = None
    if task_choice is not None:
        candidate, source = task_choice, "task_choice"
    else:
        candidate, source = local_candidate, local_source

    if candidate is None:
        return _ready_resolution("repository_default", role, task_ref, "repository_default", base)
    _validate_route(candidate)
    # An explicit base choice overrides a conflicting local route; that is a
    # real choice and must be confirmed rather than silently bypassing it.
    bypasses_local = (task_choice is not None and local_candidate is not None
                      and local_candidate != candidate)
    already_confirmed = (candidate == base and not bypasses_local)
    if source == "local_role" and local_confirmed:
        already_confirmed = True
    if source == "task_choice" and local_confirmed and candidate == local_candidate:
        already_confirmed = True
    this_task_confirmed = _confirmation_matches("this_task", role, task_ref, candidate, confirmation)
    if already_confirmed or this_task_confirmed:
        scope = ("this_task" if this_task_confirmed else
                 "confirmed_user_local" if local_confirmed else "repository_default")
        return _ready_resolution(scope, role, task_ref, source, candidate)
    return {
        "status": "needs_confirmation",
        "source": f"{source}_candidate",
        "candidate": candidate,
        "confirmation_binding": {"role": role, "task_ref": task_ref,
                                 "candidate_digest": route_digest(candidate)},
        "confirmation_choices": ["this_task", "future"],
        "question": "这次按你的模型路线执行，还是后续 Playbook 任务都按这条路线执行？",
    }


def user_config_path(codex_home: Path | None = None) -> Path:
    if codex_home is None:
        codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return Path(codex_home) / "model-routing.json"


def load_user_config(codex_home: Path | None = None) -> dict[str, Any]:
    path = user_config_path(codex_home)
    if path.is_symlink():
        raise ValueError("refusing to replace symlinked user model-routing.json")
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("user model-routing.json must contain an object")
    return data


def persist_user_role(
    role: str,
    route: dict[str, Any],
    codex_home: Path,
    *,
    task_ref: str,
    confirmation: dict[str, Any],
) -> Path:
    """Persist only an explicitly future-scoped choice in user local config."""
    _validate_role(role)
    _validate_route(route)
    if not _confirmation_matches("future", role, task_ref, route, confirmation):
        raise ValueError("writing user-local model routing requires exact future confirmation")
    path = user_config_path(codex_home)
    local = load_user_config(codex_home)
    if local.get("ownership", "user_managed") != "user_managed":
        raise ValueError("model-routing.json is not user-managed")
    local.setdefault("schema_version", 2)
    local["ownership"] = "user_managed"
    local.setdefault("supervisor_executor_roles", {})[role] = route
    local.setdefault("supervisor_executor_confirmed", {})[role] = route
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".model-routing-", suffix=".json", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(local, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def _available(step: dict[str, str], host_capabilities: dict[str, list[str]]) -> bool:
    return step["effort"] in host_capabilities.get(step["model"], ())


def _assessment_index(
    route: dict[str, Any], task_ref: str, task_assessments: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    if not isinstance(task_ref, str) or not task_ref.strip():
        raise ValueError("task_ref is required for task adequacy assessment")
    if not isinstance(task_assessments, list):
        raise ValueError("task assessments must be a list of exact model/effort evidence")
    allowed = {(step["model"], step["effort"])
               for key in ROUTE_KEYS for step in route.get(key, [])}
    indexed = {}
    for assessment in task_assessments:
        if (not isinstance(assessment, dict)
                or set(assessment) != {"task_ref", "model", "effort", "status", "evidence_ref"}
                or not all(isinstance(assessment[key], str) and assessment[key].strip()
                           for key in ("task_ref", "model", "effort", "evidence_ref"))
                or assessment["status"] not in ("adequate", "insufficient")):
            raise ValueError("task assessment requires task_ref, exact model, effort, status and evidence_ref")
        if assessment["task_ref"] != task_ref:
            raise ValueError("task assessment task_ref does not match dispatch task_ref")
        key = (assessment["model"], assessment["effort"])
        if key not in allowed or key in indexed:
            raise ValueError("task assessment must name a unique step in the confirmed route")
        indexed[key] = assessment
    return indexed


def _assessed_step(step: dict[str, str], assessments: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    assessment = assessments.get((step["model"], step["effort"]))
    if assessment is None:
        raise ValueError(f"task adequacy unknown for {step['model']} {step['effort']}")
    return assessment


def select_step(
    role: str,
    resolution: dict[str, Any],
    host_capabilities: dict[str, list[str]],
    *,
    task_ref: str,
    task_assessments: list[dict[str, str]],
    current: dict[str, str] | None = None,
    failure_kind: str | None = None,
) -> dict[str, Any]:
    """Select the next available, adequate step from a ready role resolution.

    Host capabilities and per-step assessments must be fresh for this task.
    Missing assessment of an earlier available step blocks dispatch. A current
    step may be escalated only after exact-step model insufficiency diagnosis.
    """
    _validate_role(role)
    if (not isinstance(resolution, dict) or resolution.get("status") != "ready"
            or resolution.get("role") != role or resolution.get("task_ref") != task_ref):
        raise ValueError("ready resolution for this role and task_ref is required before selection")
    route = resolution.get("route")
    _validate_route(route)
    digest = route_digest(route)
    if resolution.get("route_digest") != digest:
        raise ValueError("ready resolution route changed after confirmation")
    scope = resolution.get("confirmation_scope")
    source = resolution.get("source")
    capability = resolution.get("dispatch_capability")
    if (not isinstance(scope, str) or scope not in _CONFIRMATION_SCOPES
            or not isinstance(source, str)
            or not isinstance(capability, str) or len(capability) != 64
            or any(character not in "0123456789abcdef" for character in capability)
            or not hmac.compare_digest(capability,
                                       _dispatch_capability(scope, role, task_ref, source, digest))):
        raise ValueError("valid resolver-issued dispatch capability is required")
    if not isinstance(host_capabilities, dict) or not host_capabilities:
        raise ValueError("fresh host model/effort capabilities are required")
    if any(not isinstance(model, str) or not isinstance(efforts, list)
           or not all(isinstance(effort, str) for effort in efforts)
           for model, efforts in host_capabilities.items()):
        raise ValueError("host capabilities must map models to effort lists")
    assessments = _assessment_index(route, task_ref, task_assessments)

    primary = route["primary"]
    secondary = route.get("after_primary_max", [])
    fallback = route.get("availability_fallback", [])
    def choose(steps: list[dict[str, str]], source: str, escalation_ref: str | None = None) -> dict[str, Any] | None:
        for step in steps:
            if not _available(step, host_capabilities):
                continue
            assessment = _assessed_step(step, assessments)
            if assessment["status"] == "adequate":
                result = {"source": source, "step": step,
                          "adequacy_evidence": assessment["evidence_ref"]}
                if escalation_ref is not None:
                    result["escalation_evidence"] = escalation_ref
                return result
        return None

    def require_fallback_gate() -> None:
        available_primary = [step for step in primary if _available(step, host_capabilities)]
        if role == "executor":
            if available_primary:
                raise ValueError("Executor Terra fallback requires every Luna step unavailable")
            return
        for step in available_primary:
            if _assessed_step(step, assessments)["status"] == "adequate":
                raise ValueError("Supervisor fallback requires no available and adequate 6 Sol step")

    if current is None:
        chosen = choose(primary, "primary")
        if chosen is not None:
            return chosen
        require_fallback_gate()
        chosen = choose(fallback, "availability_fallback")
        if chosen is not None:
            return chosen
        raise ValueError("no available and evidenced adequate role step")

    if failure_kind != "model_insufficient" or current not in primary + secondary + fallback:
        raise ValueError("escalation requires a diagnosed current route step")
    diagnosis = _assessed_step(current, assessments)
    if diagnosis["status"] != "insufficient":
        raise ValueError("escalation requires exact current model/effort insufficiency evidence")
    evidence_ref = diagnosis["evidence_ref"]
    if current in primary:
        remaining = primary[primary.index(current) + 1:]
        chosen = choose(remaining, "primary", evidence_ref)
        if chosen is not None:
            return chosen
        # The dedicated Sol series opens only after the primary Max was
        # actually tried and diagnosed as insufficient. Missing higher Luna
        # efforts are an availability problem, not proof of Max insufficiency.
        if current == primary[-1]:
            chosen = choose(secondary, "after_primary_max", evidence_ref)
            if chosen is not None:
                return chosen
        if role == "supervisor":
            require_fallback_gate()
            chosen = choose(fallback, "availability_fallback", evidence_ref)
            if chosen is not None:
                return chosen
        raise ValueError("primary route exhausted; no available adequate next series")
    if current in secondary:
        chosen = choose(secondary[secondary.index(current) + 1:], "after_primary_max", evidence_ref)
        if chosen is not None:
            return chosen
        raise ValueError("after-primary route exhausted or unavailable")
    if current in fallback:
        require_fallback_gate()
        chosen = choose(fallback[fallback.index(current) + 1:], "availability_fallback", evidence_ref)
        if chosen is not None:
            return chosen
        raise ValueError("availability fallback exhausted or unavailable")
    raise ValueError("current model/effort is not in the confirmed escalation route")


def verify_readback(step: dict[str, str], actual_model: str, actual_effort: str) -> bool:
    if step != {"model": actual_model, "effort": actual_effort}:
        raise ValueError("actual dispatched model/effort does not match selected route")
    return True
