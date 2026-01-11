"""Protocol definitions for dependency injection and testing."""

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from honeysuckle.sam.client import SamEvent
from honeysuckle.foyle.client import FoyleEvent


@runtime_checkable
class SamClientProtocol(Protocol):
    """Protocol for Sam (OpenAI Realtime) client."""

    async def connect(self) -> None:
        """Connect to the OpenAI Realtime API."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the API."""
        ...

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio data to Sam."""
        ...

    async def cancel_response(self) -> None:
        """Cancel current response (for barge-in)."""
        ...

    async def speak(self, text: str) -> None:
        """Have Sam speak the given text."""
        ...

    async def send_function_result(self, call_id: str, result: str) -> None:
        """Send function call result back to Sam."""
        ...

    def events(self) -> AsyncIterator[SamEvent]:
        """Iterate over events from Sam."""
        ...


@runtime_checkable
class FoyleClientProtocol(Protocol):
    """Protocol for Foyle (Claude Agent SDK) client."""

    def run(self, query_text: str) -> AsyncIterator[FoyleEvent]:
        """Run a query through Foyle, yielding events."""
        ...

    async def cancel(self) -> None:
        """Cancel the current Foyle task."""
        ...
