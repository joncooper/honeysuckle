"""Session state and conversation context."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SessionPhase(Enum):
    """Current phase of the session."""

    IDLE = "idle"
    LISTENING = "listening"
    RECEPTIONIST_SPEAKING = "receptionist_speaking"
    PROFESSOR_THINKING = "professor_thinking"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class QueuedTask:
    """A task queued for a high-bandwidth context."""

    id: str
    description: str
    action: str
    context: dict[str, Any]
    created_at: float


@dataclass
class ApprovalRequest:
    """Pending approval request."""

    tool_name: str
    tool_input: dict[str, Any]
    description: str


@dataclass
class SessionState:
    """
    Tracks the current state of a voice session.

    Includes conversation context, queued tasks, and pending approvals.
    """

    phase: SessionPhase = SessionPhase.IDLE
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    task_queue: list[QueuedTask] = field(default_factory=list)
    pending_approval: ApprovalRequest | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for WebSocket transmission."""
        return {
            "phase": self.phase.value,
            "pending_approval": (
                {
                    "tool_name": self.pending_approval.tool_name,
                    "description": self.pending_approval.description,
                }
                if self.pending_approval
                else None
            ),
            "queued_tasks_count": len(self.task_queue),
        }
