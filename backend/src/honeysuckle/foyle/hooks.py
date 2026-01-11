"""Approval hooks and tool interceptors for Foyle."""

from typing import Any

from honeysuckle.approval.risk import ActionRisk, assess_risk


async def voice_approval_hook(
    tool_name: str,
    tool_input: dict[str, Any],
    request_approval: Any,  # Callable to request voice approval
) -> dict[str, Any]:
    """
    Pre-tool-use hook that requests voice approval for risky operations.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Input arguments to the tool
        request_approval: Async callback to request user approval

    Returns:
        Hook response - empty dict to proceed, or permission denial
    """
    # Assess the risk of this operation
    risk = assess_risk(tool_name, tool_input)

    if risk.level == ActionRisk.HIGH:
        # Always require approval for high-risk actions
        description = risk.description
        approved = await request_approval(
            f"I need to {description}. Is that okay?"
        )

        if not approved:
            return {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "User denied via voice",
                }
            }

    elif risk.level == ActionRisk.MEDIUM:
        # Require approval unless we have recent implicit consent
        # TODO: Track implicit consent from conversation context
        description = risk.description
        approved = await request_approval(
            f"I'll {description}. Is that okay?"
        )

        if not approved:
            return {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "User denied via voice",
                }
            }

    # Low risk or approved - proceed
    return {}


def describe_action(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    Generate a human-readable description of a tool action.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input arguments

    Returns:
        Human-readable description of the action
    """
    if tool_name == "Bash":
        command = tool_input.get("command", "")

        if "gday mail send" in command:
            # Extract recipient from command
            return "send an email"
        elif "gday mail reply" in command:
            return "send a reply"
        elif "gday mail archive" in command:
            return "archive an email"
        elif "gday cal create" in command:
            return "create a calendar event"

    return f"execute {tool_name}"
