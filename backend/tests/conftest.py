"""Pytest fixtures for honeysuckle tests."""

import sys
from pathlib import Path

# Add tests directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import pytest

from mocks import MockSamClient, MockFoyleClient
from fakes import FakeWebSocket
from honeysuckle.session.manager import SessionManager


@pytest.fixture
def mock_sam() -> MockSamClient:
    """Create a MockSamClient instance."""
    return MockSamClient()


@pytest.fixture
def mock_foyle() -> MockFoyleClient:
    """Create a MockFoyleClient instance."""
    return MockFoyleClient()


@pytest.fixture
def fake_websocket() -> FakeWebSocket:
    """Create a FakeWebSocket instance."""
    return FakeWebSocket()


@pytest.fixture
def session_manager(
    fake_websocket: FakeWebSocket,
    mock_sam: MockSamClient,
    mock_foyle: MockFoyleClient,
) -> SessionManager:
    """
    Create a SessionManager with mocked dependencies.

    This fixture provides a fully testable SessionManager that:
    - Uses a FakeWebSocket instead of a real WebSocket
    - Uses MockSamClient instead of connecting to OpenAI
    - Uses MockFoyleClient instead of connecting to Claude
    """
    return SessionManager(
        websocket=fake_websocket,
        sam_client=mock_sam,
        foyle_client=mock_foyle,
    )
