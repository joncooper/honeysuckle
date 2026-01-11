"""Mock implementations of Sam and Foyle clients for testing."""

import asyncio
from typing import AsyncIterator

from honeysuckle.sam.client import (
    SamEvent,
    AudioDelta,
    TranscriptDelta,
    FunctionCall,
    SpeechStarted,
    SpeechStopped,
    ResponseStarted,
    ResponseDone,
)
from honeysuckle.foyle.client import (
    FoyleEvent,
    ToolStart,
    ToolEnd,
    TextDelta,
    Result,
)


class MockSamClient:
    """
    Mock implementation of SamClient for testing.

    Allows tests to:
    - Inject events via inject_event()
    - Verify calls to speak(), send_function_result(), etc.
    - Control the event stream
    """

    def __init__(self):
        self.events_queue: asyncio.Queue[SamEvent | None] = asyncio.Queue()
        self.spoken: list[str] = []
        self.function_results: list[tuple[str, str]] = []
        self.audio_sent: list[bytes] = []
        self.connected: bool = False
        self.response_cancelled: bool = False
        self._running: bool = False

    async def connect(self) -> None:
        """Mock connect - just sets connected flag."""
        self.connected = True
        self._running = True

    async def disconnect(self) -> None:
        """Mock disconnect - clears connected flag and stops event loop."""
        self.connected = False
        self._running = False
        # Send sentinel to unblock events() if waiting
        await self.events_queue.put(None)

    async def send_audio(self, audio_data: bytes) -> None:
        """Record audio sent to Sam."""
        self.audio_sent.append(audio_data)

    async def cancel_response(self) -> None:
        """Record that response was cancelled."""
        self.response_cancelled = True

    async def speak(self, text: str) -> None:
        """Record text that Sam was asked to speak."""
        self.spoken.append(text)

    async def send_function_result(self, call_id: str, result: str) -> None:
        """Record function results sent back to Sam."""
        self.function_results.append((call_id, result))

    async def inject_event(self, event: SamEvent) -> None:
        """
        Inject an event into the event stream.

        Use this from tests to simulate Sam sending events.
        """
        await self.events_queue.put(event)

    async def stop(self) -> None:
        """Stop the event stream by sending sentinel."""
        await self.events_queue.put(None)

    async def events(self) -> AsyncIterator[SamEvent]:
        """Yield events from the queue until sentinel (None) received."""
        while self._running:
            event = await self.events_queue.get()
            if event is None:
                break
            yield event


class MockFoyleClient:
    """
    Mock implementation of FoyleClient for testing.

    Allows tests to:
    - Set canned responses via set_response()
    - Verify queries received
    - Simulate cancellation
    """

    def __init__(self):
        self.queries: list[str] = []
        self.responses: list[list[FoyleEvent]] = []
        self.cancelled: bool = False
        self._cancel_event: asyncio.Event = asyncio.Event()

    def set_response(self, events: list[FoyleEvent]) -> None:
        """
        Set the events to yield for the next run() call.

        Events are consumed in FIFO order - call multiple times
        to set up responses for multiple queries.
        """
        self.responses.append(events)

    async def run(self, query_text: str) -> AsyncIterator[FoyleEvent]:
        """
        Yield pre-configured events for the query.

        Records the query for later verification.
        """
        self.queries.append(query_text)
        self._cancel_event.clear()
        self.cancelled = False

        # Get events for this query, or default to a simple result
        if self.responses:
            events = self.responses.pop(0)
        else:
            events = [Result(text="Mock response")]

        for event in events:
            # Check for cancellation before each event
            if self._cancel_event.is_set():
                self.cancelled = True
                return
            yield event
            # Small yield to allow cancellation to be processed
            await asyncio.sleep(0)

    async def cancel(self) -> None:
        """Signal cancellation of the current query."""
        self._cancel_event.set()
        self.cancelled = True
