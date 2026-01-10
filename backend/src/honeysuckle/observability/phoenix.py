"""Arize Phoenix integration for development observability."""

from honeysuckle.config import settings


def setup_phoenix():
    """
    Set up Arize Phoenix for local development.

    Phoenix provides a UI for viewing traces and debugging
    LLM applications during development.
    """
    try:
        import phoenix as px
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Launch Phoenix server
        px.launch_app(port=settings.phoenix_port)

        # Set up OTLP exporter to Phoenix
        endpoint = f"http://localhost:{settings.phoenix_port}/v1/traces"
        exporter = OTLPSpanExporter(endpoint=endpoint)

        # Configure tracer provider
        provider = TracerProvider()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        print(f"Phoenix UI available at http://localhost:{settings.phoenix_port}")

    except ImportError:
        print("Phoenix not available. Install with: pip install arize-phoenix")
    except Exception as e:
        print(f"Failed to start Phoenix: {e}")
