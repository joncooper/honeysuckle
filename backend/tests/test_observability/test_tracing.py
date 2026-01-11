"""Tests for OpenTelemetry tracing instrumentation.

Note: OpenTelemetry's global TracerProvider can only be set once,
so we run these tests with a single shared provider setup.
"""

import asyncio
import pytest

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from honeysuckle.session.manager import SessionManager
from honeysuckle.sam.client import (
    FunctionCall,
    ResponseDone,
    ResponseStarted,
    SpeechStarted,
)
from honeysuckle.foyle.client import Result, TextDelta

from mocks import MockSamClient, MockFoyleClient
from fakes import FakeWebSocket


# Module-level setup for tracing - done once
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))

# Only set if not already set
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    trace.set_tracer_provider(_provider)


@pytest.fixture
def trace_exporter():
    """Provide the shared exporter, clearing it before each test."""
    _exporter.clear()
    yield _exporter
    _exporter.clear()


@pytest.fixture
def mock_sam_for_tracing() -> MockSamClient:
    return MockSamClient()


@pytest.fixture
def mock_foyle_for_tracing() -> MockFoyleClient:
    return MockFoyleClient()


@pytest.fixture
def fake_websocket_for_tracing() -> FakeWebSocket:
    return FakeWebSocket()


@pytest.fixture
def traced_session_manager(
    fake_websocket_for_tracing: FakeWebSocket,
    mock_sam_for_tracing: MockSamClient,
    mock_foyle_for_tracing: MockFoyleClient,
) -> SessionManager:
    """Create a SessionManager for tracing tests."""
    return SessionManager(
        websocket=fake_websocket_for_tracing,
        sam_client=mock_sam_for_tracing,
        foyle_client=mock_foyle_for_tracing,
    )


class TestSessionTracing:
    """Test that session creates proper trace hierarchy."""

    async def test_session_creates_root_span(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """SessionManager creates a root 'session' span."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        # End the session
        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        # Check for session span
        spans = trace_exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "session" in span_names

    async def test_session_span_has_session_id(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Session span has session_id attribute."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        session_span = next((s for s in spans if s.name == "session"), None)

        assert session_span is not None
        attrs = dict(session_span.attributes)
        assert "session.id" in attrs

    async def test_greeting_creates_span(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Greeting creates a child span under session."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "greeting" in span_names


class TestConversationTurnTracing:
    """Test conversation turn span hierarchy."""

    async def test_speech_started_creates_turn_span(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """SpeechStarted creates a conversation_turn span."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        # Trigger a turn
        await mock_sam_for_tracing.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseStarted(response_id="r1"))
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseDone(response_id="r1"))
        await asyncio.sleep(0.05)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "conversation_turn" in span_names

    async def test_turn_span_has_turn_number(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Conversation turn span has turn_number attribute."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        # Trigger a turn
        await mock_sam_for_tracing.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseStarted(response_id="r1"))
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseDone(response_id="r1"))
        await asyncio.sleep(0.05)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        turn_span = next((s for s in spans if s.name == "conversation_turn"), None)

        assert turn_span is not None
        attrs = dict(turn_span.attributes)
        assert "turn_number" in attrs
        assert attrs["turn_number"] == 1


class TestSpanHierarchy:
    """Test parent/child span relationships."""

    async def test_greeting_is_child_of_session(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Greeting span has session span as parent."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        session_span = next((s for s in spans if s.name == "session"), None)
        greeting_span = next((s for s in spans if s.name == "greeting"), None)

        assert session_span is not None
        assert greeting_span is not None
        # Greeting's parent should be session's span context
        assert greeting_span.parent.span_id == session_span.context.span_id

    async def test_turn_is_child_of_session(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Conversation turn span has session span as parent."""
        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        # Trigger a turn
        await mock_sam_for_tracing.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseStarted(response_id="r1"))
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(ResponseDone(response_id="r1"))
        await asyncio.sleep(0.05)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        session_span = next((s for s in spans if s.name == "session"), None)
        turn_span = next((s for s in spans if s.name == "conversation_turn"), None)

        assert session_span is not None
        assert turn_span is not None
        assert turn_span.parent.span_id == session_span.context.span_id

    async def test_foyle_invocation_is_child_of_turn(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Foyle invocation span has turn span as parent."""
        mock_foyle_for_tracing.set_response([Result(text="Done")])

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        # Start a turn then call Foyle
        await mock_sam_for_tracing.inject_event(SpeechStarted())
        await asyncio.sleep(0.05)
        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        turn_span = next((s for s in spans if s.name == "conversation_turn"), None)
        foyle_span = next((s for s in spans if s.name == "foyle_invocation"), None)

        assert turn_span is not None
        assert foyle_span is not None
        assert foyle_span.parent.span_id == turn_span.context.span_id


class TestFoyleInvocationTracing:
    """Test Foyle invocation creates proper spans."""

    async def test_foyle_invocation_creates_span(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """ask_foyle creates a foyle_invocation span."""
        mock_foyle_for_tracing.set_response([Result(text="Done")])

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test query"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "foyle_invocation" in span_names

    async def test_foyle_span_has_query_input(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Foyle invocation span has input value attribute."""
        mock_foyle_for_tracing.set_response([Result(text="Done")])

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "What emails do I have?"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        foyle_span = next((s for s in spans if s.name == "foyle_invocation"), None)

        assert foyle_span is not None
        attrs = dict(foyle_span.attributes)
        assert "input.value" in attrs
        assert "emails" in attrs["input.value"]

    async def test_foyle_span_has_output_value(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Foyle invocation span has output value attribute."""
        mock_foyle_for_tracing.set_response([Result(text="You have 5 emails")])

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        foyle_span = next((s for s in spans if s.name == "foyle_invocation"), None)

        assert foyle_span is not None
        attrs = dict(foyle_span.attributes)
        assert "output.value" in attrs
        assert "5 emails" in attrs["output.value"]

    async def test_foyle_error_records_exception(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Foyle errors are recorded in the span."""
        async def failing_foyle(query):
            raise RuntimeError("Test error")
            yield

        mock_foyle_for_tracing.run = failing_foyle

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Test"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        foyle_span = next((s for s in spans if s.name == "foyle_invocation"), None)

        assert foyle_span is not None
        # Span should have recorded an exception event
        assert len(foyle_span.events) >= 1
        exception_event = next(
            (e for e in foyle_span.events if e.name == "exception"),
            None
        )
        assert exception_event is not None

    async def test_foyle_cancellation_records_cancelled_attribute(
        self,
        traced_session_manager: SessionManager,
        mock_sam_for_tracing: MockSamClient,
        mock_foyle_for_tracing: MockFoyleClient,
        fake_websocket_for_tracing: FakeWebSocket,
        trace_exporter: InMemorySpanExporter,
    ):
        """Cancelled Foyle invocation records cancelled attribute."""
        async def slow_foyle(query):
            mock_foyle_for_tracing.queries.append(query)
            for i in range(20):
                if mock_foyle_for_tracing._cancel_event.is_set():
                    return
                await asyncio.sleep(0.05)
                yield TextDelta(text=f"Working {i}...")
            yield Result(text="Done")

        mock_foyle_for_tracing.run = slow_foyle

        session_task = asyncio.create_task(traced_session_manager.run())
        await asyncio.sleep(0.1)

        await mock_sam_for_tracing.inject_event(FunctionCall(
            name="ask_foyle",
            args={"query": "Long query"},
            call_id="call-1",
        ))
        await asyncio.sleep(0.15)

        # Barge in to cancel
        await mock_sam_for_tracing.inject_event(SpeechStarted())
        await asyncio.sleep(0.2)

        await mock_sam_for_tracing.stop()
        await fake_websocket_for_tracing.inject_disconnect()
        await asyncio.wait_for(session_task, timeout=1.0)

        spans = trace_exporter.get_finished_spans()
        foyle_span = next((s for s in spans if s.name == "foyle_invocation"), None)

        assert foyle_span is not None
        attrs = dict(foyle_span.attributes)
        assert attrs.get("cancelled") is True
