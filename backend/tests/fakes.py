"""Fake implementations for testing."""

import asyncio
import json
from typing import Any


class FakeWebSocket:
    """
    Fake WebSocket implementation for testing SessionManager.

    Captures messages sent by SessionManager and allows tests
    to inject incoming messages.
    """

    def __init__(self):
        self.sent_json: list[dict[str, Any]] = []
        self.sent_bytes: list[bytes] = []
        self.incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.closed: bool = False

    async def send_json(self, data: dict[str, Any]) -> None:
        """Capture JSON messages sent to the client."""
        self.sent_json.append(data)

    async def send_bytes(self, data: bytes) -> None:
        """Capture binary data sent to the client."""
        self.sent_bytes.append(data)

    async def receive(self) -> dict[str, Any]:
        """
        Return next message from the incoming queue.

        Blocks until a message is available.
        """
        return await self.incoming.get()

    async def inject_text(self, text: str) -> None:
        """
        Inject a text message as if received from the client.

        The message will be wrapped in WebSocket receive format.
        """
        await self.incoming.put({
            "type": "websocket.receive",
            "text": text,
        })

    async def inject_json(self, data: dict[str, Any]) -> None:
        """
        Inject a JSON message as if received from the client.

        Convenience wrapper around inject_text.
        """
        await self.inject_text(json.dumps(data))

    async def inject_bytes(self, data: bytes) -> None:
        """
        Inject binary data as if received from the client.

        Used to simulate audio input.
        """
        await self.incoming.put({
            "type": "websocket.receive",
            "bytes": data,
        })

    async def inject_disconnect(self) -> None:
        """
        Inject a disconnect event.

        This will cause SessionManager.run() to exit.
        """
        self.closed = True
        await self.incoming.put({
            "type": "websocket.disconnect",
        })

    def get_state_updates(self) -> list[dict[str, Any]]:
        """
        Get all state update messages sent to the client.

        Filters sent_json for messages with type="state".
        """
        return [msg for msg in self.sent_json if msg.get("type") == "state"]

    def get_events(self, event_type: str) -> list[dict[str, Any]]:
        """
        Get all messages of a specific type sent to the client.

        Args:
            event_type: The type of events to filter for (e.g., "transcript", "tool_start")
        """
        return [msg for msg in self.sent_json if msg.get("type") == event_type]

    def clear(self) -> None:
        """Clear all captured messages."""
        self.sent_json.clear()
        self.sent_bytes.clear()
