"""Action risk assessment for approval flow."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionRisk(Enum):
    """Risk level of an action."""

    LOW = "low"  # Safe to execute without approval
    MEDIUM = "medium"  # Requires implicit or explicit consent
    HIGH = "high"  # Always requires explicit approval


@dataclass
class RiskAssessment:
    """Result of risk assessment."""

    level: ActionRisk
    description: str
    reason: str


def assess_risk(tool_name: str, tool_input: dict[str, Any]) -> RiskAssessment:
    """
    Assess the risk level of a tool operation.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Input arguments to the tool

    Returns:
        RiskAssessment with level, description, and reason
    """
    if tool_name != "Bash":
        # Unknown tools are high risk
        return RiskAssessment(
            level=ActionRisk.HIGH,
            description=f"execute unknown tool {tool_name}",
            reason="Unknown tool type",
        )

    command = tool_input.get("command", "")

    # High risk: sending emails
    if re.search(r"gday\s+mail\s+send", command):
        recipient = _extract_flag(command, "--to")
        return RiskAssessment(
            level=ActionRisk.HIGH,
            description=f"send an email to {recipient}" if recipient else "send an email",
            reason="Sending email is irreversible",
        )

    if re.search(r"gday\s+mail\s+reply", command):
        return RiskAssessment(
            level=ActionRisk.HIGH,
            description="send a reply",
            reason="Sending email is irreversible",
        )

    # Medium risk: modifying data
    if re.search(r"gday\s+mail\s+archive", command):
        return RiskAssessment(
            level=ActionRisk.MEDIUM,
            description="archive an email",
            reason="Archives email (can be undone)",
        )

    if re.search(r"gday\s+mail\s+star", command):
        return RiskAssessment(
            level=ActionRisk.LOW,
            description="star an email",
            reason="Starring is easily reversible",
        )

    if re.search(r"gday\s+cal\s+create", command):
        return RiskAssessment(
            level=ActionRisk.MEDIUM,
            description="create a calendar event",
            reason="Creates event (can be deleted)",
        )

    # Low risk: read-only operations
    if re.search(r"gday\s+mail\s+(list|read|search)", command):
        return RiskAssessment(
            level=ActionRisk.LOW,
            description="read email",
            reason="Read-only operation",
        )

    if re.search(r"gday\s+cal\s+(today|tomorrow|week|show)", command):
        return RiskAssessment(
            level=ActionRisk.LOW,
            description="check calendar",
            reason="Read-only operation",
        )

    # Unknown gday commands are medium risk
    if "gday" in command:
        return RiskAssessment(
            level=ActionRisk.MEDIUM,
            description="execute a gday command",
            reason="Unknown gday operation",
        )

    # Non-gday commands are high risk
    return RiskAssessment(
        level=ActionRisk.HIGH,
        description="execute a system command",
        reason="Non-gday command",
    )


def _extract_flag(command: str, flag: str) -> str | None:
    """Extract the value of a flag from a command string."""
    pattern = rf"{flag}\s+(\S+)"
    match = re.search(pattern, command)
    return match.group(1) if match else None
