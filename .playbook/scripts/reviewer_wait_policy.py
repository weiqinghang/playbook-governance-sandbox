"""Formal Reviewer wait policy: windows are observations, never premature failure."""
DEFAULT = {"wait_window_seconds": 600, "max_failed_reviewer_attempts": 2}


def resolve(override=None):
    policy = dict(DEFAULT)
    if override:
        policy.update(override)
    if not isinstance(policy["wait_window_seconds"], int) or policy["wait_window_seconds"] < 600:
        raise ValueError("formal reviewer wait_window_seconds must be at least 600")
    return policy


def next_action(instance_status: str, policy=None) -> str:
    resolve(policy)
    if instance_status == "pending":
        return "continue_same_reviewer"
    if instance_status in {"incomplete", "launch_failed"}:
        return "retry_reviewer"
    if instance_status == "blocked":
        return "review_blocked"
    if instance_status == "completed":
        return "consume_result"
    raise ValueError(f"unknown reviewer instance status: {instance_status}")
