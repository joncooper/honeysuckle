"""Voice-based approval flow."""

import asyncio
from dataclasses import dataclass
from typing import Callable


@dataclass
class ApprovalResult:
    """Result of an approval request."""

    approved: bool
    reason: str | None = None


SpeakCallback = Callable[[str], None]
ListenCallback = Callable[[], str]


class ApprovalFlow:
    """
    Manages voice-based approval for risky operations.

    Uses the Receptionist to speak the approval request and
    listens for the user's yes/no response.
    """

    # Phrases that indicate approval
    APPROVAL_PHRASES = [
        "yes",
        "yeah",
        "yep",
        "sure",
        "okay",
        "ok",
        "go ahead",
        "do it",
        "proceed",
        "approved",
        "that's fine",
        "sounds good",
    ]

    # Phrases that indicate denial
    DENIAL_PHRASES = [
        "no",
        "nope",
        "don't",
        "stop",
        "cancel",
        "wait",
        "hold on",
        "never mind",
        "nevermind",
        "not now",
        "denied",
    ]

    def __init__(self, timeout: float = 30.0):
        """
        Initialize approval flow.

        Args:
            timeout: Seconds to wait for user response
        """
        self.timeout = timeout
        self._pending_future: asyncio.Future | None = None

    async def request_approval(
        self,
        description: str,
        speak: SpeakCallback,
    ) -> ApprovalResult:
        """
        Request user approval via voice.

        Args:
            description: What action needs approval
            speak: Callback to speak the approval request

        Returns:
            ApprovalResult with approved status
        """
        # Create future for the response
        self._pending_future = asyncio.get_event_loop().create_future()

        # Speak the request
        await speak(f"I need to {description}. Is that okay?")

        try:
            # Wait for response
            result = await asyncio.wait_for(
                self._pending_future,
                timeout=self.timeout,
            )
            return result
        except asyncio.TimeoutError:
            return ApprovalResult(
                approved=False,
                reason="Timed out waiting for response",
            )
        finally:
            self._pending_future = None

    def handle_response(self, transcript: str) -> bool:
        """
        Handle user's voice response to approval request.

        Args:
            transcript: User's transcribed speech

        Returns:
            True if response was handled, False if no pending request
        """
        if not self._pending_future or self._pending_future.done():
            return False

        # Normalize transcript
        text = transcript.lower().strip()

        # Check for approval
        for phrase in self.APPROVAL_PHRASES:
            if phrase in text:
                self._pending_future.set_result(
                    ApprovalResult(approved=True)
                )
                return True

        # Check for denial
        for phrase in self.DENIAL_PHRASES:
            if phrase in text:
                self._pending_future.set_result(
                    ApprovalResult(approved=False, reason="User said no")
                )
                return True

        # Ambiguous response - ask again or default to no
        self._pending_future.set_result(
            ApprovalResult(
                approved=False,
                reason=f"Unclear response: {transcript}",
            )
        )
        return True

    def cancel(self):
        """Cancel pending approval request."""
        if self._pending_future and not self._pending_future.done():
            self._pending_future.set_result(
                ApprovalResult(approved=False, reason="Cancelled")
            )
