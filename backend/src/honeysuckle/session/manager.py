"""SessionManager - Orchestrates the Split-Brain architecture."""

import asyncio
import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any

from fastapi import WebSocket
from openinference.instrumentation import using_session
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import set_span_in_context

logger = logging.getLogger(__name__)

from honeysuckle.foyle.client import FoyleClient, Result, TextDelta, ToolStart
from honeysuckle.protocols import FoyleClientProtocol, SamClientProtocol
from honeysuckle.sam.client import (
    AudioDelta,
    FunctionCall,
    SamClient,
    ResponseDone,
    ResponseStarted,
    SpeechStarted,
    SpeechStopped,
    TranscriptDelta,
)
from honeysuckle.session.state import SessionPhase, SessionState

# Minimum seconds between spoken status updates to avoid queue buildup
STATUS_SPEAK_DEBOUNCE_SECONDS = 4.0


def get_tracer():
    """Get tracer lazily to ensure Phoenix is initialized first."""
    return trace.get_tracer("honeysuckle.session")


class SessionManager:
    """
    Orchestrates the Split-Brain architecture.

    Manages handoff between Sam (OpenAI Realtime) and
    Foyle (Claude Agent SDK), handles ambient audio, approval
    flows, and barge-in cancellation.
    """

    def __init__(
        self,
        websocket: WebSocket,
        sam_client: SamClientProtocol | None = None,
        foyle_client: FoyleClientProtocol | None = None,
    ):
        self.websocket = websocket
        self.state = SessionState()
        self.sam: SamClientProtocol = sam_client if sam_client is not None else SamClient()
        self.foyle: FoyleClientProtocol = foyle_client if foyle_client is not None else FoyleClient()
        self.foyle_task: asyncio.Task | None = None
        self._running = False
        self._sam_task: asyncio.Task | None = None
        self._last_status_speak_time: float = 0  # For debouncing status updates
        self._session_id = str(uuid.uuid4())  # Unique ID for Phoenix session tracking

        # Span tracking hierarchy:
        # session (root) → conversation_turn → user_utterance/routing/foyle
        self._session_span = None            # Root span for entire session
        self._session_context: Context | None = None  # Context for session-level children
        self._session_start_time: float = 0
        self._turn_number: int = 0           # Counter for turn numbering

        self._current_turn_span = None       # Current turn span (child of session)
        self._current_turn_context: Context | None = None  # Context for turn-level children
        self._turn_start_time: float = 0

        logger.info(f"Session created with ID: {self._session_id}")

    async def run(self):
        """Main session loop."""
        self._running = True
        await self._emit_state()
        logger.info("Session started, connecting to OpenAI Realtime...")

        # Start the session-level root span
        self._start_session()

        # Connect to OpenAI Realtime
        try:
            await self.sam.connect()
            logger.info("Connected to OpenAI Realtime API")
            self.state.phase = SessionPhase.IDLE
            await self._emit_state()
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime: {e}")
            await self._emit_event("error", {"message": f"Failed to connect: {e}"})
            self._end_session(error=str(e))
            return

        # Start Sam event loop
        self._sam_task = asyncio.create_task(self._sam_loop())

        # Greet the user (as a session-level child span)
        with self._session_child_span("greeting") as span:
            await self.sam.speak("Hi! I'm Honeysuckle, your email and calendar assistant. How can I help you?")

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

        # Close any open turn span
        if self._current_turn_span:
            self._current_turn_span.set_attribute("session_ended", True)
            self._current_turn_span.end()
            self._current_turn_span = None
            self._current_turn_context = None

        if self._sam_task and not self._sam_task.done():
            self._sam_task.cancel()
            try:
                await self._sam_task
            except asyncio.CancelledError:
                pass

        if self.foyle_task and not self.foyle_task.done():
            self.foyle_task.cancel()
            try:
                await self.foyle_task
            except asyncio.CancelledError:
                pass

        await self.sam.disconnect()

        # End the session span
        self._end_session()
        logger.info(f"Session {self._session_id} cleaned up")

    def _start_session(self) -> None:
        """Start the root session span."""
        self._session_start_time = time.time()
        tracer = get_tracer()

        self._session_span = tracer.start_span(
            "session",
            attributes={
                SpanAttributes.SESSION_ID: self._session_id,
            }
        )
        self._session_context = set_span_in_context(self._session_span)
        logger.info(f"Started session span (id={self._session_id})")

    def _end_session(self, error: str | None = None) -> None:
        """End the root session span."""
        if self._session_span:
            duration = time.time() - self._session_start_time
            self._session_span.set_attribute("duration_seconds", duration)
            self._session_span.set_attribute("turn_count", self._turn_number)
            if error:
                self._session_span.set_attribute("error", error)
            self._session_span.end()
            self._session_span = None
            self._session_context = None
            logger.info(f"Ended session span (duration={duration:.2f}s, turns={self._turn_number})")

    @contextmanager
    def _session_child_span(self, name: str, **attributes):
        """Create a child span under the session (not under a turn)."""
        tracer = get_tracer()
        if self._session_context:
            span = tracer.start_span(name, context=self._session_context)
        else:
            span = tracer.start_span(name)

        span.set_attribute(SpanAttributes.SESSION_ID, self._session_id)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            yield span
        finally:
            span.end()

    def _start_turn(self, trigger: str) -> None:
        """Start a new conversation turn span (as child of session)."""
        # End any existing turn first
        self._end_turn(interrupted=True)

        self._turn_number += 1
        self._turn_start_time = time.time()
        tracer = get_tracer()

        # Create turn span as child of session
        self._current_turn_span = tracer.start_span(
            "conversation_turn",
            context=self._session_context,  # Child of session
            attributes={
                SpanAttributes.SESSION_ID: self._session_id,
                "trigger": trigger,
                "turn_number": self._turn_number,
            }
        )
        # Store context so child spans can be created under this turn
        self._current_turn_context = set_span_in_context(self._current_turn_span)
        logger.info(f"Started conversation turn #{self._turn_number} (trigger={trigger})")

    def _end_turn(self, interrupted: bool = False) -> None:
        """End the current conversation turn span."""
        if self._current_turn_span:
            duration = time.time() - self._turn_start_time
            self._current_turn_span.set_attribute("duration_seconds", duration)
            self._current_turn_span.set_attribute("interrupted", interrupted)
            self._current_turn_span.end()
            self._current_turn_span = None
            self._current_turn_context = None
            logger.info(f"Ended conversation turn (duration={duration:.2f}s, interrupted={interrupted})")

    @contextmanager
    def _child_span(self, name: str, **attributes):
        """Create a child span under current turn, or session if no turn active."""
        tracer = get_tracer()
        if self._current_turn_context:
            # Create as child of the current turn
            span = tracer.start_span(name, context=self._current_turn_context)
        elif self._session_context:
            # No turn active, create as child of session
            span = tracer.start_span(name, context=self._session_context)
        else:
            # No session either, create standalone span
            span = tracer.start_span(name)

        span.set_attribute(SpanAttributes.SESSION_ID, self._session_id)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            yield span
        finally:
            span.end()

    async def _sam_loop(self):
        """Handle events from Sam."""
        try:
            async for event in self.sam.events():
                if isinstance(event, AudioDelta):
                    # Forward audio to client
                    await self.websocket.send_bytes(event.data)

                elif isinstance(event, SpeechStarted):
                    # User started speaking - this begins a new turn
                    logger.info("VAD: user started speaking")

                    # Handle barge-in (cancel ongoing activity)
                    await self._handle_barge_in()

                    # Start new conversation turn
                    self._start_turn(trigger="user_speech")

                    self.state.phase = SessionPhase.LISTENING
                    await self._emit_state()

                elif isinstance(event, SpeechStopped):
                    # User stopped speaking
                    logger.info("VAD: user stopped speaking")

                elif isinstance(event, TranscriptDelta):
                    # Send transcript to client
                    await self._emit_event(
                        "transcript",
                        {"text": event.text, "role": event.role},
                    )
                    if event.role == "user":
                        # Record user utterance as child span
                        with self._child_span("user_utterance", **{SpanAttributes.INPUT_VALUE: event.text[:500]}) as span:
                            pass  # Span auto-ends

                elif isinstance(event, FunctionCall):
                    # Record routing decision as child span
                    with self._child_span("sam_routing", routing_decision="foyle", function_name=event.name) as span:
                        pass

                    if event.name == "ask_foyle":
                        # Hand off to Foyle (non-blocking!)
                        query = event.args.get("query", "")
                        logger.info(f"Function call: ask_foyle({query[:50]}...) - spawning background task")
                        # Pass turn context to Foyle so its spans are children of this turn
                        turn_context = self._current_turn_context
                        self.foyle_task = asyncio.create_task(
                            self._invoke_foyle(query, event.call_id, turn_context)
                        )

                elif isinstance(event, ResponseStarted):
                    # Sam started responding
                    self.state.phase = SessionPhase.SAM_SPEAKING
                    await self._emit_state()
                    logger.info(f"Response started: {event.response_id}")

                elif isinstance(event, ResponseDone):
                    # Sam finished responding - turn is complete
                    self._end_turn(interrupted=False)
                    self.state.phase = SessionPhase.IDLE
                    await self._emit_state()
                    logger.info(f"Response done: {event.response_id}")

        except asyncio.CancelledError:
            pass

    async def _invoke_foyle(self, query: str, call_id: str, turn_context: Context | None):
        """Hand off to Foyle for deep reasoning. Runs as background task."""
        import datetime

        tracer = get_tracer()

        # Create foyle_invocation as child of the turn
        span = tracer.start_span(
            "foyle_invocation",
            context=turn_context,
            attributes={
                SpanAttributes.SESSION_ID: self._session_id,
                SpanAttributes.INPUT_VALUE: query[:500],
                "call_id": call_id,
            }
        )
        # Create context for tool spans to be children of foyle_invocation
        foyle_context = set_span_in_context(span)

        logger.info(f"Foyle starting for query: {query[:50]}...")
        self.state.phase = SessionPhase.FOYLE_THINKING
        await self._emit_state()

        # Reset debounce so first status update gets spoken
        self._last_status_speak_time = 0

        result_text = ""
        tool_count = 0

        try:
            async for event in self.foyle.run(query):
                if isinstance(event, ToolStart):
                    tool_count += 1
                    logger.info(f"Foyle tool start: {event.name}")
                    # Create child span for tool execution under foyle_invocation
                    tool_span = tracer.start_span(
                        "tool_execution",
                        context=foyle_context,
                        attributes={
                            SpanAttributes.SESSION_ID: self._session_id,
                            "tool.name": event.name,
                            "tool.input": str(event.input)[:500],
                        }
                    )
                    tool_span.end()  # Tool events don't have duration info, end immediately

                    await self._emit_event(
                        "tool_start",
                        {"tool": event.name, "input": event.input},
                    )

                elif isinstance(event, TextDelta):
                    await self._emit_event("text", {"content": event.text})
                    # Speak intermediate status updates so user knows what's happening
                    # Debounce to avoid queuing too many speaks (causes overlap issues)
                    now = time.time()
                    time_since_last = now - self._last_status_speak_time
                    if event.text and len(event.text) > 20 and time_since_last >= STATUS_SPEAK_DEBOUNCE_SECONDS:
                        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        logger.info(f"[{ts}] SPEAK status: {event.text[:80]}...")
                        self._last_status_speak_time = now
                        await self.sam.speak(event.text)

                elif isinstance(event, Result):
                    result_text = event.text
                    logger.info(f"Foyle result: {result_text[:100]}...")

            span.set_attribute("tool_count", tool_count)
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, result_text[:500])

        except asyncio.CancelledError:
            logger.info("Foyle cancelled (barge-in)")
            result_text = "The request was cancelled."
            span.set_attribute("cancelled", True)
        except Exception as e:
            logger.error(f"Foyle error: {e}", exc_info=True)
            result_text = "Sorry, I encountered an error processing that request."
            span.record_exception(e)
        finally:
            span.end()
            self.state.phase = SessionPhase.IDLE
            await self._emit_state()

        # Send result back to Sam to speak
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"[{ts}] SPEAK result: {result_text[:80]}...")
        await self.sam.send_function_result(call_id, result_text)
        logger.info(f"[{ts}] Foyle handoff complete")

    async def _handle_audio(self, audio_data: bytes):
        """Handle incoming audio from client."""
        await self.sam.send_audio(audio_data)

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

    async def _handle_barge_in(self):
        """Handle barge-in when user starts speaking during output."""
        logger.info("Barge-in: user interrupted, clearing audio")

        # Tell frontend to clear its audio buffer immediately
        await self._emit_event("barge_in", {})

        # Cancel the OpenAI response to stop audio output
        await self.sam.cancel_response()

        # Also cancel Foyle if thinking
        if self.state.phase == SessionPhase.FOYLE_THINKING:
            logger.info("Barge-in: cancelling Foyle task")
            await self.foyle.cancel()
            if self.foyle_task and not self.foyle_task.done():
                self.foyle_task.cancel()

        self.state.phase = SessionPhase.LISTENING
        await self._emit_state()

    async def _handle_vad_start(self):
        """User started speaking - handle barge-in (legacy, from frontend control message)."""
        await self._handle_barge_in()

    async def _handle_vad_end(self):
        """User stopped speaking."""
        # Sam will process the utterance
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
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Log events that appear in the Thoughts UI
        if event_type == "transcript":
            logger.info(f"[{ts}] THOUGHT transcript [{data.get('role')}]: {data.get('text', '')[:100]}")
        elif event_type == "tool_start":
            logger.info(f"[{ts}] THOUGHT tool_start: {data.get('tool')} - {str(data.get('input', ''))[:100]}")
        elif event_type == "text":
            logger.info(f"[{ts}] THOUGHT text: {data.get('content', '')[:100]}")

        await self.websocket.send_json({
            "type": event_type,
            **data,
        })
