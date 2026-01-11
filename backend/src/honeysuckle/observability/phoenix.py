"""Arize Phoenix integration for development observability.

Phoenix provides a local UI for viewing LLM traces and debugging.
It instruments OpenAI and Anthropic SDK calls automatically.

Usage:
    1. Start the backend with PHOENIX_ENABLED=true (default)
    2. Open http://localhost:6006 to view traces
    3. Make voice requests - traces appear in real-time
"""

import logging
import os

from honeysuckle.config import settings

logger = logging.getLogger(__name__)


def setup_phoenix():
    """
    Set up Arize Phoenix for local development.

    This function:
    1. Launches the Phoenix server (web UI)
    2. Configures OpenTelemetry to export traces to Phoenix
    3. Instruments OpenAI SDK for automatic tracing
    """
    try:
        import phoenix as px
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from phoenix.otel import register

        # Set Phoenix port via environment variable (avoids deprecation warning)
        os.environ["PHOENIX_PORT"] = str(settings.phoenix_port)

        # Launch Phoenix server in the background
        # use_temp_dir=False persists traces to ~/.phoenix/ (SQLite)
        logger.info(f"Launching Phoenix on port {settings.phoenix_port}...")
        px.launch_app(use_temp_dir=False)

        # Use phoenix.otel.register() for proper project name handling
        # batch=True uses BatchSpanProcessor which queues and flushes reliably
        tracer_provider = register(
            project_name="honeysuckle",
            endpoint=f"http://127.0.0.1:{settings.phoenix_port}/v1/traces",
            batch=True,  # Reliable persistence via BatchSpanProcessor
        )

        # Verify the global tracer provider was set
        from opentelemetry import trace as otel_trace
        global_provider = otel_trace.get_tracer_provider()
        logger.info(f"Global TracerProvider type: {type(global_provider).__name__}")
        logger.info(f"Returned TracerProvider type: {type(tracer_provider).__name__}")
        logger.info(f"Are they the same? {global_provider is tracer_provider}")

        # Instrument OpenAI SDK (traces all openai.* calls)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("OpenAI SDK instrumented for tracing")

        # Create a test span to verify export works
        test_tracer = otel_trace.get_tracer("honeysuckle.test")
        with test_tracer.start_as_current_span("startup_test_span") as span:
            span.set_attribute("test", "phoenix_connectivity")
            logger.info(f"Created test span: {span.get_span_context().trace_id}")

        # Note: Anthropic instrumentation skipped - Claude Agent SDK bundles
        # anthropic differently and the instrumentor has version conflicts.
        # Claude API calls will still be visible via our custom spans.

        logger.info(f"Phoenix UI available at http://localhost:{settings.phoenix_port}")
        logger.info("Traces will appear in project: honeysuckle")

    except ImportError as e:
        logger.warning(f"Phoenix dependencies not available: {e}")
        logger.warning("Install with: uv add arize-phoenix openinference-instrumentation-openai")
    except Exception as e:
        logger.error(f"Failed to start Phoenix: {e}", exc_info=True)
