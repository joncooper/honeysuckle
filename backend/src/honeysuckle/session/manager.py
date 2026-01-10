"""SessionManager - Orchestrates the Split-Brain architecture."""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

from honeysuckle.professor.client import ProfessorClient, Result, TextDelta, ToolStart
from honeysuckle.receptionist.client import (
    AudioDelta,
    FunctionCall,
    ReceptionistClient,
    TranscriptDelta,
)
from honeysuckle.session.state import SessionPhase, SessionState


class SessionManager:
    """
    Orchestrates the Split-Brain architecture.

    Manages handoff between Receptionist (OpenAI Realtime) and
    Professor (Claude Agent SDK), handles ambient audio, approval
    flows, and barge-in cancellation.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.state = SessionState()
        self.receptionist = ReceptionistClient()
        self.professor = ProfessorClient()
        self.professor_task: asyncio.Task | None = None
        self._running = False
        self._receptionist_task: asyncio.Task | None = None

    async def run(self):
        """Main session loop."""
        self._running = True
        await self._emit_state()
        logger.info("Session started, connecting to OpenAI Realtime...")

        # Connect to OpenAI Realtime
        try:
            await self.receptionist.connect()
            logger.info("Connected to OpenAI Realtime API")
            self.state.phase = SessionPhase.IDLE
            await self._emit_state()
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime: {e}")
            await self._emit_event("error", {"message": f"Failed to connect: {e}"})
            return

        # Start receptionist event loop
        self._receptionist_task = asyncio.create_task(self._receptionist_loop())

        # Greet the user
        await self.receptionist.speak("Hi! I'm Honeysuckle, your email and calendar assistant. How can I help you?")

        # Handle client messages
        try:
            while self._running:
                message = await self.websocket.receive()

                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        await self._handle_audio(message["bytes"])
                    elif "text" in message:
                        await self._handle_control(json.loads(message["text"]))
                elif message["type"] == "websocket.disconnect":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources on session end."""
        self._running = False

        if self._receptionist_task and not self._receptionist_task.done():
            self._receptionist_task.cancel()
            try:
                await self._receptionist_task
            except asyncio.CancelledError:
                pass

        if self.professor_task and not self.professor_task.done():
            self.professor_task.cancel()
            try:
                await self.professor_task
            except asyncio.CancelledError:
                pass

        await self.receptionist.disconnect()

    async def _receptionist_loop(self):
        """Handle events from the Receptionist."""
        try:
            async for event in self.receptionist.events():
                if isinstance(event, AudioDelta):
                    # Forward audio to client
                    logger.info(f"Audio: {len(event.data)} bytes -> client")
                    await self.websocket.send_bytes(event.data)

                elif isinstance(event, TranscriptDelta):
                    # Send transcript to client
                    await self._emit_event(
                        "transcript",
                        {"text": event.text, "role": event.role},
                    )
                    if event.role == "user":
                        self.state.phase = SessionPhase.LISTENING
                        await self._emit_state()

                elif isinstance(event, FunctionCall):
                    if event.name == "ask_professor":
                        # Hand off to Professor (non-blocking!)
                        # Must not await - continue processing audio events while Professor runs
                        query = event.args.get("query", "")
                        logger.info(f"Function call: ask_professor({query[:50]}...) - spawning background task")
                        self.professor_task = asyncio.create_task(
                            self._invoke_professor(query, event.call_id)
                        )

        except asyncio.CancelledError:
            pass

    async def _invoke_professor(self, query: str, call_id: str):
        """Hand off to Professor for deep reasoning. Runs as background task."""
        logger.info(f"Professor starting for query: {query[:50]}...")
        self.state.phase = SessionPhase.PROFESSOR_THINKING
        await self._emit_state()

        result_text = ""

        try:
            async for event in self.professor.run(query):
                if isinstance(event, ToolStart):
                    logger.info(f"Professor tool start: {event.name}")
                    await self._emit_event(
                        "tool_start",
                        {"tool": event.name, "input": event.input},
                    )

                elif isinstance(event, TextDelta):
                    await self._emit_event("text", {"content": event.text})

                elif isinstance(event, Result):
                    result_text = event.text
                    logger.info(f"Professor result: {result_text[:100]}...")

        except asyncio.CancelledError:
            logger.info("Professor cancelled (barge-in)")
            result_text = "The request was cancelled."
        except Exception as e:
            logger.error(f"Professor error: {e}", exc_info=True)
            result_text = "Sorry, I encountered an error processing that request."
        finally:
            self.state.phase = SessionPhase.IDLE
            await self._emit_state()

        # Send result back to Receptionist to speak
        logger.info("Sending Professor result to Receptionist")
        await self.receptionist.send_function_result(call_id, result_text)
        logger.info("Professor handoff complete")

    async def _handle_audio(self, audio_data: bytes):
        """Handle incoming audio from client."""
        await self.receptionist.send_audio(audio_data)

    async def _handle_control(self, message: dict[str, Any]):
        """Handle control messages from client."""
        msg_type = message.get("type")

        match msg_type:
            case "vad_start":
                await self._handle_vad_start()
            case "vad_end":
                await self._handle_vad_end()
            case "approval_response":
                approved = message.get("approved", False)
                await self._handle_approval_response(approved)
            case _:
                pass

    async def _handle_vad_start(self):
        """User started speaking - handle barge-in."""
        if self.state.phase == SessionPhase.PROFESSOR_THINKING:
            # Cancel Professor task
            await self.professor.cancel()

        elif self.state.phase == SessionPhase.RECEPTIONIST_SPEAKING:
            # Cancel current response
            await self.receptionist.cancel_response()

        self.state.phase = SessionPhase.LISTENING
        await self._emit_state()

    async def _handle_vad_end(self):
        """User stopped speaking."""
        # Receptionist will process the utterance
        pass

    async def _handle_approval_response(self, approved: bool):
        """Handle approval response from user."""
        # TODO: Resolve pending approval future
        self.state.pending_approval = None
        await self._emit_state()

    async def _emit_state(self):
        """Send current state to client."""
        await self.websocket.send_json({
            "type": "state",
            "state": self.state.to_dict(),
        })

    async def _emit_event(self, event_type: str, data: dict[str, Any]):
        """Send an event to client."""
        await self.websocket.send_json({
            "type": event_type,
            **data,
        })
