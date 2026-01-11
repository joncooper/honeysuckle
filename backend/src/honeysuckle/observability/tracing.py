"""OpenTelemetry tracing for Honeysuckle."""

from opentelemetry import trace

# Main tracer for Honeysuckle
tracer = trace.get_tracer("honeysuckle")


# Span names for key operations
class SpanNames:
    """Standard span names for Honeysuckle operations."""

    # Voice turns
    VOICE_TURN = "voice_turn"  # VAD start → VAD end

    # Sam operations
    SAM_RESPONSE = "sam_response"  # Query → audio complete
    SAM_CONNECT = "sam_connect"  # WebSocket connection

    # Foyle operations
    FOYLE_INVOCATION = "foyle_invocation"  # Start → result
    TOOL_EXECUTION = "tool_execution"  # Tool start → tool end

    # Approval flow
    APPROVAL_FLOW = "approval_flow"  # Request → user response
    APPROVAL_LATENCY = "approval_latency"  # Time waiting for user

    # Session operations
    SESSION_HANDOFF = "session_handoff"  # Sam → Foyle handoff
    SESSION_CLEANUP = "session_cleanup"  # Session teardown


def create_voice_turn_span(user_id: str | None = None):
    """Create a span for a voice turn (user speaking)."""
    span = tracer.start_span(SpanNames.VOICE_TURN)
    if user_id:
        span.set_attribute("user.id", user_id)
    return span


def create_foyle_span(query: str):
    """Create a span for a Foyle invocation."""
    span = tracer.start_span(SpanNames.FOYLE_INVOCATION)
    span.set_attribute("foyle.query", query[:500])  # Truncate for safety
    return span


def create_tool_span(tool_name: str, tool_input: dict):
    """Create a span for tool execution."""
    span = tracer.start_span(SpanNames.TOOL_EXECUTION)
    span.set_attribute("tool.name", tool_name)
    span.set_attribute("tool.input_keys", list(tool_input.keys()))
    return span


def create_approval_span(action_description: str):
    """Create a span for an approval flow."""
    span = tracer.start_span(SpanNames.APPROVAL_FLOW)
    span.set_attribute("approval.action", action_description)
    return span
