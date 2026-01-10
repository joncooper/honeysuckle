"""OpenAI Realtime WebSocket client."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

import websockets
from websockets.client import WebSocketClientProtocol

from honeysuckle.config import settings
from honeysuckle.receptionist.functions import RECEPTIONIST_FUNCTIONS, RECEPTIONIST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class ReceptionistEvent:
    """Base class for Receptionist events."""

    pass


@dataclass
class AudioDelta(ReceptionistEvent):
    """Audio output from Receptionist."""

    data: bytes


@dataclass
class TranscriptDelta(ReceptionistEvent):
    """Transcript of user or assistant speech."""

    text: str
    role: str  # "user" or "assistant"


@dataclass
class FunctionCall(ReceptionistEvent):
    """Function call from Receptionist."""

    name: str
    args: dict[str, Any]
    call_id: str


class ReceptionistClient:
    """
    OpenAI Realtime API client.

    Provides bidirectional audio streaming with function calling support.
    The Receptionist handles low-latency conversational flow, VAD, and barge-in.
    """

    REALTIME_URL = "wss://api.openai.com/v1/realtime"

    def __init__(self):
        self._ws: WebSocketClientProtocol | None = None
        self._running = False

    async def connect(self):
        """Connect to OpenAI Realtime API."""
        url = f"{self.REALTIME_URL}?model={settings.openai_realtime_model}"
        logger.info(f"Connecting to OpenAI Realtime: {url}")

        self._ws = await websockets.connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
        )
        logger.info("WebSocket connected to OpenAI")
        self._running = True

        # Configure session
        logger.info("Configuring session...")
        await self._send({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": RECEPTIONIST_SYSTEM_PROMPT,
                "voice": settings.openai_realtime_voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "tools": RECEPTIONIST_FUNCTIONS,
            },
        })

    async def disconnect(self):
        """Disconnect from OpenAI Realtime API."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Receptionist."""
        if self._ws:
            import base64

            await self._send({
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(audio_data).decode(),
            })

    async def cancel_response(self):
        """Cancel current response (for barge-in)."""
        if self._ws:
            await self._send({"type": "response.cancel"})

    async def speak(self, text: str):
        """
        Have Receptionist speak the given text.

        Uses the pattern: create a user message with instruction, then trigger response.
        See: https://community.openai.com/t/make-agent-speak-first-when-using-realtimesession/1328354
        """
        if self._ws:
            # Create a user message instructing the assistant what to say
            await self._send({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": f"Say exactly this to the user: \"{text}\""
                    }],
                },
            })
            # Trigger the response
            await self._send({"type": "response.create"})

    async def send_function_result(self, call_id: str, result: str):
        """Send function call result back to Receptionist."""
        logger.info(f"Sending function result for {call_id}: {result[:100]}...")
        if self._ws:
            await self._send({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result,
                },
            })
            await self._send({"type": "response.create"})
            logger.info("Triggered response.create after function result")

    async def events(self) -> AsyncIterator[ReceptionistEvent]:
        """Iterate over events from Receptionist."""
        if not self._ws:
            return

        while self._running:
            try:
                raw = await self._ws.recv()
                event = json.loads(raw)
                parsed = self._parse_event(event)
                if parsed:
                    yield parsed
            except websockets.ConnectionClosed:
                break
            except asyncio.CancelledError:
                break

    def _parse_event(self, event: dict[str, Any]) -> ReceptionistEvent | None:
        """Parse raw event into typed event."""
        event_type = event.get("type", "")

        # Log significant events for debugging (skip high-frequency audio events)
        if event_type not in (
            "input_audio_buffer.speech_started",
            "input_audio_buffer.speech_stopped",
            "input_audio_buffer.committed",
            "response.audio.delta",
            "response.audio_transcript.delta",
        ):
            logger.info(f"OpenAI event: {event_type}")

        if event_type == "response.audio.delta":
            import base64

            audio = base64.b64decode(event.get("delta", ""))
            logger.info(f"Received {len(audio)} bytes of audio from OpenAI")
            return AudioDelta(data=audio)

        elif event_type == "response.audio_transcript.done":
            # Complete assistant transcript (not deltas)
            return TranscriptDelta(text=event.get("transcript", ""), role="assistant")

        elif event_type == "conversation.item.input_audio_transcription.completed":
            return TranscriptDelta(text=event.get("transcript", ""), role="user")

        elif event_type == "response.function_call_arguments.done":
            return FunctionCall(
                name=event.get("name", ""),
                args=json.loads(event.get("arguments", "{}")),
                call_id=event.get("call_id", ""),
            )

        return None

    async def _send(self, message: dict[str, Any]):
        """Send JSON message to WebSocket."""
        if self._ws:
            await self._ws.send(json.dumps(message))
