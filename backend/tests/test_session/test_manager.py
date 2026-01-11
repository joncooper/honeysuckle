"""Tests for SessionManager orchestration."""

import asyncio
import pytest

from honeysuckle.session.manager import SessionManager
from honeysuckle.session.state import SessionPhase
from honeysuckle.sam.client import (
    AudioDelta,
    FunctionCall,
    ResponseDone,
    ResponseStarted,
    SpeechStarted,
    SpeechStopped,
    TranscriptDelta,
)
from honeysuckle.foyle.client import Result, TextDelta, ToolStart

from mocks import MockSamClient, MockFoyleClient
from fakes import FakeWebSocket


class TestStateTransitions:
    """Test session state machine transitions."""

    async def test_initial_state_is_idle(
        self,
        session_manager: SessionManager,
    ):
        """SessionManager starts in IDLE state."""
        assert session_manager.state.phase == SessionPhase.IDLE

    async def test_speech_started_transitions_to_listening(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SpeechStarted event transitions state to LISTENING."""
        # Start the session in a background task
        session_task = asyncio.create_task(session_manager.run())

        # Wait for session to initialize
        await asyncio.sleep(0.05)

        # Inject SpeechStarted event
        await mock_sam.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)

        assert session_manager.state.phase == SessionPhase.LISTENING

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_response_started_transitions_to_sam_speaking(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """ResponseStarted event transitions state to SAM_SPEAKING."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Inject ResponseStarted event
        await mock_sam.inject_event(ResponseStarted(response_id="test-response"))
        await asyncio.sleep(0.05)

        assert session_manager.state.phase == SessionPhase.SAM_SPEAKING

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_response_done_transitions_to_idle(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """ResponseDone event transitions state back to IDLE."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Go through the speaking state first
        await mock_sam.inject_event(ResponseStarted(response_id="test-response"))
        await asyncio.sleep(0.05)
        assert session_manager.state.phase == SessionPhase.SAM_SPEAKING

        # Then finish
        await mock_sam.inject_event(ResponseDone(response_id="test-response"))
        await asyncio.sleep(0.05)

        assert session_manager.state.phase == SessionPhase.IDLE

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestSamToFoyleHandoff:
    """Test handoff from Sam to Foyle when ask_foyle is called."""

    async def test_ask_foyle_triggers_foyle_run(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """FunctionCall with ask_foyle triggers Foyle.run()."""
        # Set up Foyle response
        mock_foyle.set_response([
            TextDelta(text="Looking up emails..."),
            Result(text="You have 3 unread emails."),
        ])

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Inject ask_foyle function call
        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "What emails do I have?"},
            call_id="call-123",
        ))

        # Wait for Foyle to process
        await asyncio.sleep(0.1)

        # Verify Foyle was called with the query
        assert len(mock_foyle.queries) == 1
        assert mock_foyle.queries[0] == "What emails do I have?"

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_foyle_result_sent_back_to_sam(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Foyle's result is sent back to Sam via send_function_result."""
        mock_foyle.set_response([
            Result(text="You have 3 unread emails."),
        ])

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "What emails do I have?"},
            call_id="call-123",
        ))

        # Wait for Foyle to process and result to be sent back
        await asyncio.sleep(0.1)

        # Verify result was sent back to Sam
        assert len(mock_sam.function_results) == 1
        call_id, result = mock_sam.function_results[0]
        assert call_id == "call-123"
        assert "3 unread emails" in result

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_foyle_thinking_state_during_processing(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """State transitions to FOYLE_THINKING while Foyle processes."""
        # Use a slower response to catch the state
        async def slow_foyle():
            mock_foyle.queries.append("slow query")
            await asyncio.sleep(0.2)
            yield Result(text="Done")

        # Replace run with slow version
        original_run = mock_foyle.run
        mock_foyle.run = lambda q: slow_foyle()

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Slow query"},
            call_id="call-123",
        ))

        # Check state during processing
        await asyncio.sleep(0.05)
        assert session_manager.state.phase == SessionPhase.FOYLE_THINKING

        # Wait for completion
        await asyncio.sleep(0.3)
        assert session_manager.state.phase == SessionPhase.IDLE

        # Restore and clean up
        mock_foyle.run = original_run
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestBargeIn:
    """Test barge-in handling (user interrupts during processing)."""

    async def test_barge_in_cancels_sam_response(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SpeechStarted during Sam response cancels the response."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Start a response
        await mock_sam.inject_event(ResponseStarted(response_id="test-response"))
        await asyncio.sleep(0.05)
        assert session_manager.state.phase == SessionPhase.SAM_SPEAKING

        # User barges in
        await mock_sam.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)

        # Verify cancel was called and state changed
        assert mock_sam.response_cancelled
        assert session_manager.state.phase == SessionPhase.LISTENING

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_barge_in_cancels_foyle_task(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """SpeechStarted during Foyle thinking cancels Foyle."""
        # Use a slow response that can be cancelled
        async def slow_foyle(query):
            mock_foyle.queries.append(query)
            for i in range(10):
                if mock_foyle._cancel_event.is_set():
                    return
                await asyncio.sleep(0.05)
                yield TextDelta(text=f"Working {i}...")
            yield Result(text="Done")

        mock_foyle.run = slow_foyle

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Start Foyle processing
        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Long query"},
            call_id="call-123",
        ))
        await asyncio.sleep(0.1)
        assert session_manager.state.phase == SessionPhase.FOYLE_THINKING

        # User barges in
        await mock_sam.inject_event(SpeechStarted())
        await asyncio.sleep(0.1)

        # Verify Foyle was cancelled
        assert mock_foyle.cancelled
        # State will be LISTENING momentarily, then IDLE when Foyle task cleanup finishes
        # The important thing is that it's no longer FOYLE_THINKING
        assert session_manager.state.phase != SessionPhase.FOYLE_THINKING

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestEventRouting:
    """Test that events are properly routed to the WebSocket."""

    async def test_audio_forwarded_to_websocket(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """AudioDelta events are forwarded as bytes to WebSocket."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Inject audio event
        audio_data = b"\x00\x01\x02\x03"
        await mock_sam.inject_event(AudioDelta(data=audio_data))
        await asyncio.sleep(0.05)

        # Verify audio was sent to websocket
        assert len(fake_websocket.sent_bytes) >= 1
        assert audio_data in fake_websocket.sent_bytes

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_transcript_sent_as_json(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """TranscriptDelta events are sent as JSON to WebSocket."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Inject transcript event
        await mock_sam.inject_event(TranscriptDelta(text="Hello there", role="user"))
        await asyncio.sleep(0.05)

        # Verify transcript was sent
        transcript_events = fake_websocket.get_events("transcript")
        assert len(transcript_events) >= 1
        assert any(
            e.get("text") == "Hello there" and e.get("role") == "user"
            for e in transcript_events
        )

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_tool_start_sent_to_websocket(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """ToolStart events from Foyle are sent to WebSocket."""
        mock_foyle.set_response([
            ToolStart(name="Bash", input={"command": "gday mail list"}),
            Result(text="Found 3 emails"),
        ])

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "List emails"},
            call_id="call-123",
        ))
        await asyncio.sleep(0.1)

        # Verify tool_start was sent
        tool_events = fake_websocket.get_events("tool_start")
        assert len(tool_events) >= 1
        assert any(e.get("tool") == "Bash" for e in tool_events)

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_state_updates_sent_to_websocket(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """State changes are sent to WebSocket."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Trigger some state changes
        await mock_sam.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)
        await mock_sam.inject_event(SpeechStopped())
        await asyncio.sleep(0.05)

        # Verify state updates were sent
        state_updates = fake_websocket.get_state_updates()
        assert len(state_updates) >= 1

        # Should have received at least one "listening" state
        phases = [u.get("state", {}).get("phase") for u in state_updates]
        assert "listening" in phases

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestErrorHandling:
    """Test error handling and recovery."""

    async def test_sam_connect_failure_emits_error(
        self,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Sam connection failure emits error event and ends session."""
        # Make connect raise an exception
        async def failing_connect():
            raise ConnectionError("Failed to connect to OpenAI")

        mock_sam.connect = failing_connect

        session_manager = SessionManager(
            websocket=fake_websocket,
            sam_client=mock_sam,
            foyle_client=mock_foyle,
        )

        # Run should complete (not hang) when connect fails
        await asyncio.wait_for(session_manager.run(), timeout=1.0)

        # Verify error event was emitted
        error_events = fake_websocket.get_events("error")
        assert len(error_events) >= 1
        assert "Failed to connect" in error_events[0].get("message", "")

    async def test_foyle_exception_returns_error_result(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Foyle exception returns error message to Sam."""
        # Make Foyle raise an exception
        async def failing_foyle(query):
            raise RuntimeError("Foyle API error")
            yield  # Make it a generator

        mock_foyle.run = failing_foyle

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Trigger Foyle call
        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test query"},
            call_id="call-error",
        ))
        await asyncio.sleep(0.2)

        # Verify error result was sent back to Sam
        assert len(mock_sam.function_results) >= 1
        call_id, result = mock_sam.function_results[0]
        assert call_id == "call-error"
        assert "error" in result.lower()

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_foyle_exception_returns_to_idle(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Foyle exception returns state to IDLE."""
        async def failing_foyle(query):
            raise RuntimeError("Foyle API error")
            yield

        mock_foyle.run = failing_foyle

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        # State should be back to IDLE
        assert session_manager.state.phase == SessionPhase.IDLE

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestBargeInEdgeCases:
    """Test barge-in edge cases."""

    async def test_multiple_rapid_barge_ins(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Multiple rapid barge-ins don't crash the system."""
        # Set up slow Foyle response
        async def slow_foyle(query):
            mock_foyle.queries.append(query)
            for i in range(20):
                if mock_foyle._cancel_event.is_set():
                    return
                await asyncio.sleep(0.05)
                yield TextDelta(text=f"Working {i}...")
            yield Result(text="Done")

        mock_foyle.run = slow_foyle

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Start Foyle processing
        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Long query"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.1)

        # Rapid-fire barge-ins
        for _ in range(3):
            await mock_sam.inject_event(SpeechStarted())
            await asyncio.sleep(0.02)

        # Should not crash, state should be LISTENING
        assert session_manager.state.phase == SessionPhase.LISTENING

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_barge_in_emits_barge_in_event(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """Barge-in emits barge_in event to frontend."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Start a response
        await mock_sam.inject_event(ResponseStarted(response_id="r1"))
        await asyncio.sleep(0.05)

        # Barge in
        await mock_sam.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)

        # Verify barge_in event was sent
        barge_in_events = fake_websocket.get_events("barge_in")
        assert len(barge_in_events) >= 1

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestEventOrdering:
    """Test handling of events in unexpected order."""

    async def test_speech_stopped_without_speech_started(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SpeechStopped without prior SpeechStarted doesn't crash."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Send SpeechStopped without SpeechStarted
        await mock_sam.inject_event(SpeechStopped())
        await asyncio.sleep(0.05)

        # Should not crash, state should still be IDLE
        assert session_manager.state.phase == SessionPhase.IDLE

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_response_done_without_response_started(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """ResponseDone without prior ResponseStarted doesn't crash."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Send ResponseDone without ResponseStarted
        await mock_sam.inject_event(ResponseDone(response_id="orphan"))
        await asyncio.sleep(0.05)

        # Should not crash
        assert session_task.done() is False

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_audio_delta_before_session_ready(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """AudioDelta events are forwarded even in IDLE state."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Send audio while IDLE
        audio_data = b"\x00\x01\x02\x03"
        await mock_sam.inject_event(AudioDelta(data=audio_data))
        await asyncio.sleep(0.05)

        # Audio should still be forwarded
        assert audio_data in fake_websocket.sent_bytes

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestDebouncing:
    """Test status speak debouncing."""

    async def test_status_speaks_are_debounced(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        mock_foyle: MockFoyleClient,
        fake_websocket: FakeWebSocket,
    ):
        """Rapid TextDelta events don't all trigger speaks."""
        # Set up response with many rapid text deltas
        mock_foyle.set_response([
            TextDelta(text="This is a long enough status update one"),
            TextDelta(text="This is a long enough status update two"),
            TextDelta(text="This is a long enough status update three"),
            Result(text="Done"),
        ])

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.1)  # Let greeting happen

        initial_speak_count = len(mock_sam.spoken)

        await mock_sam.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.3)

        # Should have spoken greeting + at most 1 status (due to debounce)
        # Not all 3 text deltas should trigger speaks
        speaks_after_foyle = len(mock_sam.spoken) - initial_speak_count
        # The debounce is 4 seconds, so in 0.3s only 1 should get through
        assert speaks_after_foyle <= 2  # Result + maybe 1 status

        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)


class TestSessionLifecycle:
    """Test session startup and shutdown."""

    async def test_session_connects_sam_on_run(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SessionManager connects Sam when run() is called."""
        assert not mock_sam.connected

        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        assert mock_sam.connected

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_session_speaks_greeting(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SessionManager speaks a greeting on startup."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.1)

        # Should have spoken a greeting
        assert len(mock_sam.spoken) >= 1
        assert any("Honeysuckle" in text for text in mock_sam.spoken)

        # Clean up
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

    async def test_session_cleanup_on_disconnect(
        self,
        session_manager: SessionManager,
        mock_sam: MockSamClient,
        fake_websocket: FakeWebSocket,
    ):
        """SessionManager cleans up when client disconnects."""
        session_task = asyncio.create_task(session_manager.run())
        await asyncio.sleep(0.05)

        # Disconnect
        await mock_sam.stop()
        await fake_websocket.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        # Session should have completed without error
        assert session_task.done()
        assert session_task.exception() is None
